"""
quota_manager.py — Gestione dei piani abbonamento, limiti, cooldown e bonus voto.

Questo modulo si occupa di:
- Definire i piani utente (Free, Starter, Pro) e le relative quote per gruppo di comandi.
- Gestire il conteggio atomico dell'utilizzo su base giornaliera (chat, immagini, musica) o mensile (genserver, modello Pro).
- Verificare i cooldown temporali tra un comando e l'altro per prevenire lo spam.
- Assegnare e tracciare i bonus sbloccati tramite il voto giornaliero su top.gg.
"""

import os
from datetime import datetime, timezone, timedelta
from bot_managers.db import get_conn

# ── Piani abbonamento ─────────────────────────────────────────────────────────

PLANS = {
    "free": {
        "chat_model":        "gemini-3.8-flash",
        "chat_daily":         20,
        "image_daily":         1,
        "compose_daily":       1,
        "genserver_monthly":   1,
        "chat_pro_monthly":    0,     # Modello Pro non disponibile nel piano free
    },
    "starter": {
        "chat_model":        "gemini-3.8-flash",
        "chat_daily":        150,
        "image_daily":         8,
        "compose_daily":       3,
        "genserver_monthly":   1,
        "chat_pro_monthly":    0,     # Pro model only on pro plan
    },
    "pro": {
        "chat_model":        "gemini-3.8-flash",
        "chat_model_pro":    "gemini-3.1-pro-preview",  # solo piano pro
        "chat_daily":         -1,     # illimitato
        "image_daily":        20,
        "compose_daily":      10,
        "genserver_monthly":  -1,     # illimitato
        "chat_pro_monthly":   50,     # 50 messaggi/mese con modello Pro
    },
}

# Stripe Payment Links — checkout abbonamento (configurabili tramite variabili d'ambiente)
PAYMENT_LINKS = {
    "starter": os.getenv("STRIPE_STARTER_LINK", "https://buy.stripe.com/example_starter"),
    "pro":     os.getenv("STRIPE_PRO_LINK", "https://buy.stripe.com/example_pro"),
}

# Prezzi per la visualizzazione (embed /premium)
PLAN_PRICES = {
    "free":    "€0",
    "starter": "€1.99",
    "pro":     "€3.99",
}


# ── Cooldown (secondi) ────────────────────────────────────────────────────────

COOLDOWNS = {
    "chat":      15,
    "image":     30,
    "compose":   30,
    "bugreport": 300,    # 5 minuti — anti-spam segnalazioni
    "vote":      43200,  # 12 ore — allineato al cooldown voto di top.gg
}


# ── Configurazione bonus voto ────────────────────────────────────────────────

VOTE_BONUS = {
    "image_bonus":         1,   # +1 immagine per ogni voto riscattato
    "compose_bonus":       0,   # nessun bonus musica in alpha
    "max_votes_per_day":   1,   # 1 riscatto/giorno
}


# ── Helper periodo corrente (mese UTC) ───────────────────────────────────────

def _period() -> str:
    """Restituisce il mese corrente nel formato 'YYYY-MM', UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _day() -> str:
    """Restituisce il giorno corrente nel formato 'YYYY-MM-DD', UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _usage_period(command_group: str) -> str:
    """Sceglie il periodo corretto per il gruppo comando."""
    if command_group in ("chat", "image", "compose"):
        return _day()
    return _period()


# ── Piano utente ─────────────────────────────────────────────────────────────

def get_plan(user_id: str) -> str:
    """
    Restituisce il piano attuale dell'utente. Degrada automaticamente a 'free'
    se l'abbonamento è scaduto.
    """
    uid = str(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT plan, expires_at FROM user_plans WHERE user_id = ?", (uid,)
        ).fetchone()

    if not row:
        return "free"

    plan = row["plan"]
    if plan in ("starter", "pro") and row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            _set_plan(uid, "free", None, False)
            return "free"

    if plan not in PLANS:
        return "free"

    return plan


def get_plan_config(user_id: str) -> dict:
    return PLANS[get_plan(user_id)]  # configurazione completa del piano


def is_premium(user_id: str) -> bool:
    """True se l'utente ha un piano a pagamento (starter o pro)."""
    return get_plan(user_id) in ("starter", "pro")


def is_pro(user_id: str) -> bool:
    return get_plan(user_id) == "pro"


def _set_plan(user_id: str, plan: str, expires_at: str | None, is_trial: bool = False) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_plans (user_id, plan, expires_at, is_trial) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "plan = excluded.plan, "
            "expires_at = excluded.expires_at, "
            "is_trial = excluded.is_trial",
            (str(user_id), plan, expires_at, 1 if is_trial else 0)
        )
        conn.commit()


def grant_plan(user_id: str, plan: str, expires_at: str, is_trial: bool = False) -> None:
    """
    Funzione per la dashboard: attiva un piano a pagamento per un utente.
    `plan` deve essere 'starter' o 'pro'. `expires_at` è una stringa ISO datetime.
    `is_trial` indica che si tratta di una prova gratuita di 7 giorni.
    """
    if plan not in ("starter", "pro"):
        raise ValueError(f"Invalid plan '{plan}' — must be 'starter' or 'pro'")
    _set_plan(str(user_id), plan, expires_at, is_trial)


def revoke_plan(user_id: str) -> None:
    """Declassa l'utente a free (usato dalla dashboard per revocare il piano)."""
    _set_plan(str(user_id), "free", None, False)


# Alias retrocompatibili per vecchi riferimenti nel codice
grant_premium  = grant_plan
revoke_premium = revoke_plan


def get_plan_info(user_id: str) -> dict:
    """
    Returns rich plan info for display purposes:
      {'plan': str, 'expires_at': str|None, 'is_trial': bool}

    Unlike get_plan(), this does NOT auto-downgrade expired plans — it's
    meant for display only. Always use get_plan() for quota decisions.
    """
    uid = str(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT plan, expires_at, is_trial FROM user_plans WHERE user_id = ?", (uid,)
        ).fetchone()
    if not row:
        return {"plan": "free", "expires_at": None, "is_trial": False}

    plan = row["plan"]
    if plan not in PLANS:
        plan = "free"

    # Degrada automaticamente la visualizzazione se scaduto, coerente con get_plan()
    if plan in ("starter", "pro") and row["expires_at"]:
        try:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return {"plan": "free", "expires_at": None, "is_trial": False}
        except Exception:
            pass

    return {
        "plan":       plan,
        "expires_at": row["expires_at"],
        "is_trial":   bool(row["is_trial"] or 0),
    }


# ── Utilizzo mensile ─────────────────────────────────────────────────────────

def get_usage(user_id: str, command_group: str) -> int:
    uid = str(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM daily_usage "
            "WHERE user_id = ? AND command_group = ? AND date = ?",
            (uid, command_group, _usage_period(command_group))
        ).fetchone()
    return row["count"] if row else 0


def _get_limit(plan: str, command_group: str, user_id: str) -> int:
    """
    Risolve il limite mensile per una coppia (piano, gruppo_comando).
    Aggiunge il bonus voto per gli utenti free su image/compose.
    """
    suffix = "daily" if command_group in ("chat", "image", "compose") else "monthly"
    limit = PLANS[plan].get(f"{command_group}_{suffix}", 0)
    if limit == -1:
        return -1

    # Vote bonus only applies to free plan (paying users already have headroom)
    if plan == "free" and command_group in ("image", "compose"):
        bonus_img, bonus_compose = get_vote_bonus(user_id)
        if command_group == "image":
            limit += bonus_img
        else:
            limit += bonus_compose

    return limit


def check_and_increment(user_id: str, command_group: str) -> tuple[bool, int, int]:
    """
    Atomica: controlla la quota mensile e, se disponibile, la incrementa subito.

    Ritorna (ok, nuovo_contatore, limite).
    """
    uid    = str(user_id)
    plan   = get_plan(uid)
    limit  = _get_limit(plan, command_group, uid)
    period = _usage_period(command_group)

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT count FROM daily_usage "
            "WHERE user_id = ? AND command_group = ? AND date = ?",
            (uid, command_group, period)
        ).fetchone()

        current = row["count"] if row else 0

        if limit == -1:
            conn.execute(
                "INSERT INTO daily_usage (user_id, command_group, date, count) "
                "VALUES (?, ?, ?, 1) "
                "ON CONFLICT(user_id, command_group, date) "
                "DO UPDATE SET count = count + 1",
                (uid, command_group, period)
            )
            conn.commit()
            return True, current + 1, -1

        if current >= limit:
            conn.commit()
            return False, current, limit

        conn.execute(
            "INSERT INTO daily_usage (user_id, command_group, date, count) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(user_id, command_group, date) "
            "DO UPDATE SET count = count + 1",
            (uid, command_group, period)
        )
        conn.commit()
        return True, current + 1, limit


def check_quota(user_id: str, command_group: str) -> tuple[bool, int, int]:
    """
    Controlla la quota SENZA incrementarla. Da abbinare a increment_usage al successo.
    Ritorna (ok, usati, limite).
    """
    uid   = str(user_id)
    plan  = get_plan(uid)
    limit = _get_limit(plan, command_group, uid)
    used  = get_usage(uid, command_group)
    if limit == -1:
        return True, used, -1
    if used >= limit:
        return False, used, limit
    return True, used, limit


def check_rate_and_quota(user_id: str, command_group: str) -> tuple[bool, str | None]:
    """
    Controllo combinato cooldown + quota.

    Ritorna (ok, motivo_errore):
      None                   — procedi
      'cooldown:<n>'         — cooldown attivo, n secondi rimanenti
      'quota:<usati>/<limite>' — quota mensile esaurita
    """
    ok_cd, remaining = check_cooldown(user_id, command_group)
    if not ok_cd:
        return False, f"cooldown:{remaining}"

    ok_q, used, limit = check_quota(user_id, command_group)
    if not ok_q:
        return False, f"quota:{used}/{limit}"

    return True, None


def increment_usage(user_id: str, command_group: str) -> None:
    """Incrementa il contatore senza controllare il limite."""
    uid    = str(user_id)
    period = _usage_period(command_group)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO daily_usage (user_id, command_group, date, count) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(user_id, command_group, date) "
            "DO UPDATE SET count = count + 1",
            (uid, command_group, period)
        )
        conn.commit()


def decrement_usage(user_id: str, command_group: str) -> None:
    """Decrementa in caso di errore post-incremento. Non va mai sotto 0."""
    uid    = str(user_id)
    period = _usage_period(command_group)
    with get_conn() as conn:
        conn.execute(
            "UPDATE daily_usage SET count = MAX(0, count - 1) "
            "WHERE user_id = ? AND command_group = ? AND date = ?",
            (uid, command_group, period)
        )
        conn.commit()


# ── Cooldown ─────────────────────────────────────────────────────────────────

def check_cooldown(user_id: str, command_group: str) -> tuple[bool, int]:
    """Ritorna (ok, secondi_rimanenti). ok=True se il cooldown è scaduto."""
    uid      = str(user_id)
    cooldown = COOLDOWNS.get(command_group, 0)
    if cooldown == 0:
        return True, 0

    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_used FROM command_cooldowns "
            "WHERE user_id = ? AND command_group = ?",
            (uid, command_group)
        ).fetchone()

    if not row:
        return True, 0

    last_used = datetime.fromisoformat(row["last_used"])
    if last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=timezone.utc)
    elapsed   = (datetime.now(timezone.utc) - last_used).total_seconds()
    remaining = cooldown - elapsed

    if remaining <= 0:
        return True, 0

    return False, int(remaining) + 1


def set_cooldown(user_id: str, command_group: str) -> None:
    uid = str(user_id)
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO command_cooldowns (user_id, command_group, last_used) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, command_group) "
            "DO UPDATE SET last_used = excluded.last_used",
            (uid, command_group, now)
        )
        conn.commit()


# ── Bonus voto (mensile) ─────────────────────────────────────────────────────

def get_vote_bonus(user_id: str) -> tuple[int, int]:
    """Ritorna (bonus_immagini, bonus_composizioni) accumulati oggi votando."""
    uid = str(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_bonus, compose_bonus FROM vote_bonus "
            "WHERE user_id = ? AND period = ?",
            (uid, _day())
        ).fetchone()
    if not row:
        return 0, 0
    return row["image_bonus"] or 0, row["compose_bonus"] or 0


def get_votes_claimed_this_month(user_id: str) -> int:
    return get_votes_claimed_today(user_id)


def get_votes_claimed_today(user_id: str) -> int:
    uid = str(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT votes_claimed FROM vote_bonus WHERE user_id = ? AND period = ?",
            (uid, _day())
        ).fetchone()
    return row["votes_claimed"] if row else 0


def claim_vote_bonus(user_id: str) -> tuple[bool, str | None]:
    """
    Registra un nuovo riscatto /vote e assegna il bonus giornaliero.

    Ritorna (ok, motivo_errore):
      ok=True                    — bonus assegnato
      motivo_errore='max_reached' — limite mensile già raggiunto
    """
    uid    = str(user_id)
    period = _day()

    img_delta     = VOTE_BONUS["image_bonus"]
    compose_delta = VOTE_BONUS["compose_bonus"]
    now           = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT votes_claimed FROM vote_bonus WHERE user_id = ? AND period = ?",
            (uid, period)
        ).fetchone()
        claimed = row["votes_claimed"] if row else 0
        if claimed >= VOTE_BONUS["max_votes_per_day"]:
            conn.commit()
            return False, "max_reached"

        conn.execute(
            "INSERT INTO vote_bonus "
            "  (user_id, period, image_bonus, compose_bonus, votes_claimed, last_vote_at) "
            "VALUES (?, ?, ?, ?, 1, ?) "
            "ON CONFLICT(user_id, period) DO UPDATE SET "
            "  image_bonus   = image_bonus   + ?, "
            "  compose_bonus = compose_bonus + ?, "
            "  votes_claimed = votes_claimed + 1, "
            "  last_vote_at  = excluded.last_vote_at",
            (uid, period, img_delta, compose_delta, now, img_delta, compose_delta)
        )
        conn.commit()

    return True, None


# Mantenuto per retrocompatibilità
def set_vote_bonus(user_id: str) -> None:
    claim_vote_bonus(user_id)
