"""
purpleGPT — Admin Dashboard
Avvia con: python dashboard.py
Accesso: http://127.0.0.1:5000 (o tramite reverse proxy Nginx)

Variabili .env richieste:
  DB_PATH, LOG_FILE, DASHBOARD_PORT
  DASHBOARD_USER, DASHBOARD_PASS
  DASHBOARD_SECRET_KEY   — chiave sessioni Flask (genera con: python3 -c "import secrets; print(secrets.token_hex(32))")
  BROADCAST_SECRET       — token API broadcast (genera con: python3 -c "import secrets; print(secrets.token_hex(32))")
  BOT_TOKEN              — token del bot Discord (per il broadcast via discord.py)
"""

import os
import sqlite3
import hmac
import json
import hashlib
import secrets
import asyncio
import threading
import time
from urllib.parse import urlparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import (
    Flask, render_template_string, request,
    redirect, url_for, session, jsonify, get_flashed_messages, flash as flask_flash
)
from dotenv import load_dotenv
from bot_managers.db import init_db, get_conn, DB_FILE

load_dotenv()

app = Flask(__name__)

# Inizializza lo schema SQLite al caricamento se non ancora esistente (cold-start safe)
init_db()

# ── Configurazione ────────────────────────────────────────────────────────────

DB_PATH            = DB_FILE
LOG_FILE           = os.getenv("LOG_FILE", "purplegpt.log")
LOG_LINES          = 200
DASH_USER          = os.getenv("DASHBOARD_USER", "admin")
DASH_PASS          = os.getenv("DASHBOARD_PASS", "changeme")
BROADCAST_SECRET   = os.getenv("BROADCAST_SECRET", "")
INTERNAL_PORT      = int(os.getenv("INTERNAL_PORT", "5001"))
PER_PAGE           = 30

# Chiave segreta per firmare i cookie di sessione — DEVE essere nel .env
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY", "INSECURE_FALLBACK_CHANGE_ME")

if (
    DASH_USER == "admin"
    or DASH_PASS == "changeme"
    or app.secret_key == "INSECURE_FALLBACK_CHANGE_ME"
):
    raise RuntimeError(
        "Dashboard non sicura: configura DASHBOARD_USER, DASHBOARD_PASS "
        "e DASHBOARD_SECRET_KEY nel .env prima di avviarla."
    )

# Cookie di sessione sicuri (in produzione richiede HTTPS; impostare SESSION_COOKIE_SECURE=false in .env solo per test locali)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").strip().lower() in ("true", "1", "yes")
app.config.update(
    SESSION_COOKIE_HTTPONLY  = True,   # JS non può leggere il cookie
    SESSION_COOKIE_SECURE    = SESSION_COOKIE_SECURE,  # True in produzione (solo HTTPS)
    SESSION_COOKIE_SAMESITE  = "Lax",  # protezione CSRF di base
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8),
)

# ── Brute force protection ────────────────────────────────────────────────────
# Contatore tentativi falliti per IP — in memoria (si resetta al riavvio)
_login_attempts: dict[str, dict] = {}
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minuti


def _get_client_ip() -> str:
    """Ottiene l'IP reale del client, gestendo il proxy Nginx."""
    return request.headers.get("X-Real-IP") or request.remote_addr or "unknown"


def _is_locked_out(ip: str) -> bool:
    entry = _login_attempts.get(ip)
    if not entry:
        return False
    if entry["count"] >= MAX_ATTEMPTS:
        elapsed = time.time() - entry["last_attempt"]
        if elapsed < LOCKOUT_SECONDS:
            return True
        # Lockout scaduto — resetta
        _login_attempts.pop(ip, None)
    return False


def _record_failed_attempt(ip: str) -> None:
    entry = _login_attempts.setdefault(ip, {"count": 0, "last_attempt": 0})
    entry["count"] += 1
    entry["last_attempt"] = time.time()


def _reset_attempts(ip: str) -> None:
    _login_attempts.pop(ip, None)


def _safe_next_url(url: str) -> str:
    """
    Valida che l'URL di redirect post-login sia un path interno.
    Previene open redirect attacks, inclusi /\\evil.com e path encoded.
    Usa urllib.parse per controllare che non ci sia un netloc (dominio esterno).
    """
    if not url:
        return "/"
    try:
        parsed = urlparse(url)
        # Sicuro solo se: nessun schema, nessun netloc, path che inizia con /
        if parsed.scheme or parsed.netloc:
            return "/"
        if not parsed.path.startswith("/"):
            return "/"
        # Blocca anche /\\evil.com — i browser lo interpretano come //evil.com
        if parsed.path.startswith("//") or parsed.path.startswith("/\\"):
            return "/"
        return parsed.path + (("?" + parsed.query) if parsed.query else "")
    except Exception:
        return "/"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _check_credentials(username: str, password: str) -> bool:
    """
    Verifica username e password usando hmac.compare_digest per prevenire
    timing attacks. Tutto lato server, nessun hint lato client.
    """
    user_ok = hmac.compare_digest(
        username.encode("utf-8"), DASH_USER.encode("utf-8")
    )
    pass_ok = hmac.compare_digest(
        password.encode("utf-8"), DASH_PASS.encode("utf-8")
    )
    return user_ok and pass_ok


def _check_broadcast_token(token: str) -> bool:
    """Verifica il token Bearer per l'endpoint broadcast."""
    if not BROADCAST_SECRET:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"), BROADCAST_SECRET.encode("utf-8")
    )


def require_login(f):
    """Decorator: richiede sessione autenticata, altrimenti redirect a /login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def require_broadcast_auth(f):
    """Decorator: richiede Bearer token nell'header Authorization."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth_header[len("Bearer "):]
        if not _check_broadcast_token(token):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def _csrf_token() -> str:
    """Genera o recupera il token CSRF della sessione dashboard."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _validate_csrf() -> bool:
    """Valida il token CSRF inviato da un form della dashboard."""
    session_token = session.get("csrf_token", "")
    form_token = request.form.get("csrf_token", "")
    return bool(session_token and form_token and hmac.compare_digest(session_token, form_token))


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": _csrf_token}


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db():
    return get_conn()


def _column_exists(conn, table: str, column: str) -> bool:
    """Whitelist-based column existence check — immune a SQL injection."""
    ALLOWED = {
        "users":       {"user_id", "username", "tos_accepted", "created_at"},
        "daily_usage": {"user_id", "command_group", "date", "count"},
        "guild_setup": {"guild_id", "setup_done", "setup_at"},
        "user_plans":  {"user_id", "plan", "expires_at"},
        "messages":    {"id", "channel_id", "role", "content", "user_id", "username", "created_at"},
    }
    if table not in ALLOWED or column not in ALLOWED[table]:
        return False
    # PRAGMA non supporta parametri ? in SQLite — il nome tabella è già
    # validato dalla whitelist sopra, quindi l'f-string è sicura qui
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def fetch_stats():
    conn  = get_db()
    stats = {}
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    stats["total_users"]   = conn.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]

    # Server attivi: interroga il bot in tempo reale via IPC (bot.guilds in memoria).
    # Se il bot è temporaneamente offline o non raggiungibile, usa il fallback su SQLite.
    live_guilds = _bot_get_guilds()
    if live_guilds is not None:
        stats["total_guilds"] = len(live_guilds)
        # Riconcilia lo stato su SQLite per allineare guild_setup alla realtà
        try:
            live_ids = [str(g["id"]) for g in live_guilds]
            if live_ids:
                placeholders = ",".join("?" for _ in live_ids)
                conn.execute(
                    f"UPDATE guild_setup SET setup_done = 0 WHERE setup_done = 1 AND guild_id NOT IN ({placeholders})",
                    live_ids
                )
            else:
                conn.execute("UPDATE guild_setup SET setup_done = 0 WHERE setup_done = 1")
            conn.commit()
        except Exception:
            pass
    else:
        stats["total_guilds"]  = conn.execute("SELECT COUNT(*) as n FROM guild_setup WHERE setup_done = 1").fetchone()["n"]
    stats["premium_users"] = conn.execute(
        "SELECT COUNT(*) as n FROM user_plans "
        "WHERE plan IN ('starter','pro','premium') "
        "AND (expires_at IS NULL OR expires_at >= ?)", (today,)
    ).fetchone()["n"]
    stats["starter_users"] = conn.execute(
        "SELECT COUNT(*) as n FROM user_plans WHERE plan='starter' "
        "AND (expires_at IS NULL OR expires_at >= ?)", (today,)
    ).fetchone()["n"]
    stats["pro_users"] = conn.execute(
        "SELECT COUNT(*) as n FROM user_plans WHERE plan='pro' "
        "AND (expires_at IS NULL OR expires_at >= ?)", (today,)
    ).fetchone()["n"]
    stats["usage_today"]   = conn.execute(
        "SELECT SUM(count) as n FROM daily_usage WHERE date = ?", (today,)
    ).fetchone()["n"] or 0

    # Nota: Le segnalazioni di bug non sono salvate nel database SQLite,
    # ma inoltrate direttamente al canale Discord di supporto tramite webhook dedicato (BUG_WEBHOOK_URL).

    rows = conn.execute(
        "SELECT command_group, SUM(count) as total FROM daily_usage "
        "WHERE date >= ? GROUP BY command_group ORDER BY total DESC", (cutoff,)
    ).fetchall()
    stats["commands"] = [{"group": r["command_group"], "total": r["total"]} for r in rows]

    rows7 = conn.execute(
        "SELECT date, SUM(count) as total FROM daily_usage "
        "WHERE date >= ? GROUP BY date ORDER BY date ASC",
        ((datetime.now(timezone.utc) - timedelta(days=6)).strftime("%Y-%m-%d"),)
    ).fetchall()
    stats["weekly"] = [{"date": r["date"], "total": r["total"]} for r in rows7]

    stats["new_users_today"] = conn.execute(
        "SELECT COUNT(*) as n FROM users WHERE DATE(accepted_at) = ?", (today,)
    ).fetchone()["n"]

    conn.close()
    return stats


def fetch_users():
    conn  = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows  = conn.execute("""
        SELECT u.user_id, u.username,
               COALESCE(p.plan, 'free') AS plan, p.expires_at
        FROM users u
        LEFT JOIN user_plans p ON u.user_id = p.user_id
        ORDER BY CASE COALESCE(p.plan,'free')
                   WHEN 'pro'     THEN 0
                   WHEN 'starter' THEN 1
                   WHEN 'premium' THEN 2
                   ELSE 3
                 END,
                 u.username COLLATE NOCASE ASC
    """).fetchall()
    conn.close()

    users = []
    for r in rows:
        expires_str, expired = "", False
        if r["expires_at"]:
            try:
                exp         = datetime.fromisoformat(r["expires_at"])
                expired     = exp.strftime("%Y-%m-%d") < today
                expires_str = exp.strftime("%d/%m/%Y")
            except Exception:
                expires_str = r["expires_at"]
        users.append({
            "user_id":  r["user_id"],
            "username": r["username"] or r["user_id"],
            "plan":     r["plan"],
            "expires":  expires_str,
            "expired":  expired,
        })
    return users


def fetch_messages(page=1, user_filter=""):
    conn   = get_db()
    offset = (page - 1) * PER_PAGE

    has_ts = _column_exists(conn, "messages", "created_at")
    select = "SELECT user_id, username, content, channel_id" + (", created_at" if has_ts else "") + " "

    if user_filter:
        total = conn.execute(
            "SELECT COUNT(*) as n FROM messages WHERE role='user' AND (user_id=? OR username LIKE ?)",
            (user_filter, f"%{user_filter}%")
        ).fetchone()["n"]
        rows = conn.execute(
            select + "FROM messages WHERE role='user' AND (user_id=? OR username LIKE ?) "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (user_filter, f"%{user_filter}%", PER_PAGE, offset)
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) as n FROM messages WHERE role='user'").fetchone()["n"]
        rows  = conn.execute(
            select + "FROM messages WHERE role='user' ORDER BY id DESC LIMIT ? OFFSET ?",
            (PER_PAGE, offset)
        ).fetchall()

    conn.close()
    messages = []
    for r in rows:
        ts = ""
        if has_ts and r["created_at"]:
            try:
                ts = datetime.fromisoformat(r["created_at"]).strftime("%d/%m %H:%M")
            except Exception:
                ts = r["created_at"]
        messages.append({
            "user_id":    r["user_id"] or "—",
            "username":   r["username"] or "—",
            "content":    r["content"] or "",
            "channel_id": r["channel_id"] or "—",
            "ts":         ts,
        })

    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    return messages, total, total_pages


def fetch_logs(level_filter="ALL"):
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []

    lines = [l.rstrip() for l in lines if l.strip()]
    if level_filter != "ALL":
        lines = [l for l in lines if f"] {level_filter}" in l or f"] {level_filter} " in l]
    lines = lines[-LOG_LINES:]
    lines.reverse()

    result = []
    for line in lines:
        level = "INFO"
        if "] ERROR" in line or "] CRITICAL" in line:
            level = "ERROR"
        elif "] WARNING" in line:
            level = "WARNING"
        elif "] DEBUG" in line:
            level = "DEBUG"
        result.append({"text": line, "level": level})
    return result



def _bot_get_guilds() -> list[dict] | None:
    """
    Chiede al bot la lista dei server tramite il server IPC interno.
    Ritorna una lista di dict {id, name, member_count} ordinata per nome,
    oppure None se il bot è offline o non raggiungibile.
    """
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{INTERNAL_PORT}/internal/guilds",
            headers={"Authorization": f"Bearer {BROADCAST_SECRET}"}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data.get("guilds", [])
    except urllib.error.HTTPError as e:
        app.logger.error(f"[guilds IPC] HTTP {e.code}: {e.read().decode(errors='replace')}")
        return None
    except urllib.error.URLError:
        # Bot offline o server interno IPC non raggiungibile
        return None
    except Exception as e:
        app.logger.error(f"[guilds IPC] Errore imprevisto: {e}")
        return None


def _bot_send_broadcast(btype: str, title: str, body: str, version: str, target_guild_id: str) -> int:
    """
    Invia il broadcast al bot tramite il server IPC interno.
    Ritorna il numero di server raggiunti, -1 in caso di errore.
    """
    payload = json.dumps({
        "type":            btype,
        "title":           title,
        "body":            body,
        "version":         version,
        "target_guild_id": target_guild_id,
    }).encode()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{INTERNAL_PORT}/internal/broadcast",
            data=payload,
            headers={
                "Authorization":  f"Bearer {BROADCAST_SECRET}",
                "Content-Type":   "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("servers_reached", 0)
    except urllib.error.HTTPError as e:
        body_err = e.read().decode(errors="replace")
        app.logger.error(f"[broadcast IPC] HTTP {e.code}: {body_err}")
        return -1
    except urllib.error.URLError as e:
        app.logger.error(f"[broadcast IPC] Connessione fallita a 127.0.0.1:{INTERNAL_PORT}: {e.reason}")
        return -1
    except Exception as e:
        app.logger.error(f"[broadcast IPC] Errore imprevisto: {e}")
        return -1


def fetch_broadcast_history():
    """
    Legge lo storico dei broadcast inviati salvato nel file JSON locale.
    Il file si trova nella stessa directory del database SQLite.
    """
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    path = os.path.join(db_dir, "broadcast_history.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_broadcast_history(entry: dict) -> None:
    """
    Salva una nuova voce di broadcast nello storico locale (mantiene max 50 voci).
    """
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    path = os.path.join(db_dir, "broadcast_history.json")
    history = fetch_broadcast_history()
    history.insert(0, entry)
    history = history[:50]  # Limite conservativo per evitare file troppo grandi
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ── CSS comune ────────────────────────────────────────────────────────────────

COMMON_CSS = """
  :root {
    --bg:#0b0b0f; --surface:#111118; --border:#1e1e2e;
    --purple:#9b59e8; --purple2:#7a3bc7; --accent:#9b59e8; --accent1:#9b59e8; --accent2:#7a3bc7; --surf2:#161622;
    --text:#e2e8f0; --muted:#64748b; --green:#34d399; --red:#f87171;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Syne',sans-serif; min-height:100vh; }
  body::before {
    content:''; position:fixed; inset:0;
    background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events:none; z-index:0;
  }
  header {
    position:sticky; top:0; z-index:100;
    display:flex; align-items:center; gap:0.75rem;
    padding:0.9rem 1.5rem; background:rgba(11,11,15,0.85);
    backdrop-filter:blur(12px); border-bottom:1px solid var(--border);
  }
  .logo { font-size:1.4rem; }
  h1 { font-size:1.1rem; font-weight:800; letter-spacing:-0.02em; color:#ffffff; }
  h1 span { color:var(--purple); }
  nav { display:flex; gap:0.3rem; margin-left:1rem; }
  .nav-link { font-family:'DM Mono',monospace; font-size:0.72rem; color:var(--muted); text-decoration:none; padding:0.3rem 0.7rem; border-radius:6px; transition:all 0.15s; }
  .nav-link:hover, .nav-link.active { background:rgba(155,89,232,0.12); color:var(--accent); }
  .header-right { margin-left:auto; display:flex; align-items:center; gap:0.75rem; }
  .badge { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--accent); background:rgba(155,89,232,0.12); border:1px solid rgba(155,89,232,0.25); padding:0.2rem 0.5rem; border-radius:4px; }
  .refresh-btn, .logout-btn { font-family:'DM Mono',monospace; font-size:0.72rem; color:var(--muted); text-decoration:none; padding:0.3rem 0.6rem; border-radius:6px; transition:color 0.15s; }
  .refresh-btn:hover { color:var(--accent); }
  .logout-btn:hover { color:var(--red); }
  main { position:relative; z-index:1; max-width:1100px; margin:0 auto; padding:2rem 1.5rem; }
  footer { text-align:center; font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); padding:2rem; }
  .section-label { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.75rem; margin-top:2rem; }
  .section-label:first-child { margin-top:0; }
  .cards { display:grid; grid-template-columns:repeat(auto-fill, minmax(160px,1fr)); gap:0.75rem; margin-bottom:1.5rem; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:1rem 1.1rem; transition:border-color 0.2s; }
  .card:hover { border-color:rgba(155,89,232,0.3); }
  .card-label { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); margin-bottom:0.4rem; }
  .card-value { font-size:1.6rem; font-weight:800; color:var(--text); line-height:1; }
  .card-sub { font-family:'DM Mono',monospace; font-size:0.62rem; color:var(--muted); margin-top:0.25rem; }
  .flash-ok { background:rgba(52,211,153,0.1); border:1px solid rgba(52,211,153,0.25); color:var(--green); font-family:'DM Mono',monospace; font-size:0.75rem; padding:0.6rem 1rem; border-radius:8px; margin-bottom:1rem; }
  .flash-err { background:rgba(248,113,113,0.1); border:1px solid rgba(248,113,113,0.25); color:var(--red); font-family:'DM Mono',monospace; font-size:0.75rem; padding:0.6rem 1rem; border-radius:8px; margin-bottom:1rem; }
  table { width:100%; border-collapse:collapse; font-size:0.82rem; }
  th { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); text-align:left; padding:0.5rem 0.75rem; border-bottom:1px solid var(--border); }
  td { padding:0.55rem 0.75rem; border-bottom:1px solid rgba(30,30,46,0.5); vertical-align:middle; }
  tr:hover td { background:rgba(155,89,232,0.03); }
  .badge-premium { background:rgba(155,89,232,0.15); color:var(--accent); font-family:'DM Mono',monospace; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:4px; }
  .badge-free    { background:rgba(100,116,139,0.12); color:var(--muted); font-family:'DM Mono',monospace; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:4px; }
  .badge-expired { background:rgba(248,113,113,0.12); color:var(--red); font-family:'DM Mono',monospace; font-size:0.65rem; padding:0.15rem 0.5rem; border-radius:4px; }
  .action-form { display:inline; }
  .action-btn { font-family:'DM Mono',monospace; font-size:0.68rem; padding:0.25rem 0.6rem; border-radius:5px; border:1px solid; cursor:pointer; background:none; transition:all 0.15s; }
  .btn-grant  { color:var(--green); border-color:rgba(52,211,153,0.3); }
  .btn-grant:hover  { background:rgba(52,211,153,0.1); }
  .btn-revoke { color:var(--red); border-color:rgba(248,113,113,0.3); }
  .btn-revoke:hover { background:rgba(248,113,113,0.1); }
  .table-scroll { overflow-x:auto; }
  @media (max-width:600px) {
    .cards { grid-template-columns: 1fr 1fr; }
    header { flex-wrap:wrap; gap:0.5rem; }
    nav { order:3; width:100%; }
  }
"""

# ── Login HTML ─────────────────────────────────────────────────────────────────

HTML_LOGIN = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Accesso</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root { --bg:#0b0b0f; --surface:#111118; --border:#1e1e2e; --purple:#9b59e8; --purple2:#7a3bc7; --accent:#9b59e8; --text:#e2e8f0; --muted:#64748b; --red:#f87171; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background:var(--bg); color:var(--text); font-family:'Syne',sans-serif;
    min-height:100vh; display:flex; align-items:center; justify-content:center;
  }
  body::before {
    content:''; position:fixed; inset:0;
    background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events:none; z-index:0;
  }
  .card {
    position:relative; z-index:1;
    background:var(--surface); border:1px solid var(--border);
    border-radius:18px; padding:2.5rem 2rem; width:100%; max-width:360px;
    box-shadow: 0 0 60px rgba(155,89,232,0.08);
  }
  .logo { text-align:center; font-size:2.5rem; margin-bottom:0.5rem; }
  h1 { text-align:center; font-size:1.3rem; font-weight:800; margin-bottom:0.25rem; color:#ffffff; }
  h1 span { color:var(--purple); }
  .subtitle { text-align:center; font-family:'DM Mono',monospace; font-size:0.68rem; color:var(--muted); margin-bottom:2rem; }
  label { display:block; font-family:'DM Mono',monospace; font-size:0.68rem; color:var(--muted); margin-bottom:0.35rem; margin-top:1rem; }
  label:first-of-type { margin-top:0; }
  input {
    width:100%; background:rgba(255,255,255,0.04); border:1px solid var(--border);
    border-radius:8px; color:var(--text); font-family:'DM Mono',monospace;
    font-size:0.85rem; padding:0.65rem 0.9rem; outline:none;
    transition:border-color 0.15s;
  }
  input:focus { border-color:var(--purple); }
  .btn {
    width:100%; margin-top:1.5rem;
    background:linear-gradient(135deg, var(--purple), var(--purple2));
    border:none; border-radius:8px; color:#fff; font-family:'Syne',sans-serif;
    font-size:0.9rem; font-weight:700; padding:0.75rem; cursor:pointer;
    transition:opacity 0.15s;
  }
  .btn:hover { opacity:0.9; }
  .error {
    background:rgba(248,113,113,0.1); border:1px solid rgba(248,113,113,0.25);
    color:var(--red); font-family:'DM Mono',monospace; font-size:0.72rem;
    padding:0.5rem 0.8rem; border-radius:6px; margin-bottom:1rem;
    text-align:center;
  }
  .lockout {
    background:rgba(248,113,113,0.1); border:1px solid rgba(248,113,113,0.25);
    color:var(--red); font-family:'DM Mono',monospace; font-size:0.72rem;
    padding:0.5rem 0.8rem; border-radius:6px; margin-bottom:1rem;
    text-align:center;
  }
</style>
</head>
<body>
<div class="card">
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <p class="subtitle">Pannello di Amministrazione</p>

  {% if lockout %}
  <div class="lockout">⛔ Troppi tentativi. Riprova tra qualche minuto.</div>
  {% elif error %}
  <div class="error">{{ error }}</div>
  {% endif %}

  {% if not lockout %}
  <form method="POST" action="/login" autocomplete="off">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input type="hidden" name="next" value="{{ next }}">
    <label for="username">Username</label>
    <input type="text" id="username" name="username" required autofocus autocomplete="off">
    <label for="password">Password</label>
    <input type="password" id="password" name="password" required autocomplete="off">
    <button type="submit" class="btn">Accedi</button>
  </form>
  {% endif %}
</div>
</body></html>
"""

# ── Dashboard HTML ─────────────────────────────────────────────────────────────

HTML_DASH = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Statistiche</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>{{ css | safe }}</style>
</head><body>
<header>
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <nav>
    <a href="/" class="nav-link active">📊 Statistiche</a>
    <a href="/messages" class="nav-link">💬 Messaggi</a>
    <a href="/logs" class="nav-link">🪵 Log</a>
    <a href="/plans" class="nav-link">💎 Piani</a>
    <a href="/broadcast" class="nav-link">📣 Broadcast</a>
  </nav>
  <div class="header-right">
    <span class="badge">🧪 BETA</span>
    <a href="/" class="refresh-btn">↻</a>
    <a href="/logout" class="logout-btn">Esci</a>
  </div>
</header>
<main>

  {% if flash %}<div class="flash-ok">✓ {{ flash }}</div>{% endif %}
  {% if error %}<div class="flash-err">✗ {{ error }}</div>{% endif %}

  <p class="section-label">Panoramica</p>
  <div class="cards">
    <div class="card"><div class="card-label">👤 Utenti</div><div class="card-value">{{ stats.total_users }}</div><div class="card-sub">registrati</div></div>
    <div class="card"><div class="card-label">🌐 Server</div><div class="card-value">{{ stats.total_guilds }}</div><div class="card-sub">attivi</div></div>
    <div class="card"><div class="card-label">⚡ Starter</div><div class="card-value">{{ stats.starter_users }}</div><div class="card-sub">utenti</div></div>
    <div class="card"><div class="card-label">🚀 Pro</div><div class="card-value">{{ stats.pro_users }}</div><div class="card-sub">utenti</div></div>
    <div class="card"><div class="card-label">⚡ Oggi</div><div class="card-value">{{ stats.usage_today }}</div><div class="card-sub">comandi</div></div>
    <div class="card"><div class="card-label">🆕 Nuovi oggi</div><div class="card-value">{{ stats.new_users_today }}</div><div class="card-sub">utenti</div></div>
  </div>

  {% if stats.commands %}
  <p class="section-label">Utilizzo ultimi 30 giorni</p>
  <div class="table-scroll">
  <table>
    <tr><th>Comando</th><th>Utilizzi</th></tr>
    {% for c in stats.commands %}
    <tr><td><code>{{ c.group }}</code></td><td>{{ c.total }}</td></tr>
    {% endfor %}
  </table>
  </div>
  {% endif %}

  <p class="section-label">Utenti <span style="font-weight:400;color:var(--muted);font-size:0.85rem">— gestisci abbonamenti in <a href="/plans" style="color:var(--accent2)">Piani</a></span></p>
  <div class="table-scroll">
  <table>
    <tr><th>Username</th><th>User ID</th><th>Piano</th><th>Scadenza</th></tr>
    {% for u in users %}
    <tr>
      <td>{{ u.username }}</td>
      <td><code style="font-size:0.7rem;color:var(--muted)">{{ u.user_id }}</code></td>
      <td>
        {% if u.expired %}
          <span class="badge-expired">⌛ Scaduto</span>
        {% elif u.plan == 'pro' %}
          <span class="badge-premium">🚀 Pro</span>
        {% elif u.plan == 'starter' %}
          <span class="badge-premium">⚡ Starter</span>
        {% elif u.plan == 'premium' %}
          <span class="badge-premium">✨ Premium</span>
        {% else %}
          <span class="badge-free">Free</span>
        {% endif %}
      </td>
      <td><span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">{{ u.expires or '—' }}</span></td>
    </tr>
    {% endfor %}
  </table>
  </div>

</main>
<footer>purpleGPT Dashboard &nbsp;·&nbsp; jLabs by justmarcolin &nbsp;·&nbsp; {{ now }}</footer>
</body></html>
"""

# ── Messages HTML ──────────────────────────────────────────────────────────────

HTML_MESSAGES = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Messaggi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
{{ css | safe }}
  .search-bar { display:flex; gap:0.6rem; margin-bottom:1.25rem; flex-wrap:wrap; }
  .search-bar input { flex:1; min-width:180px; background:var(--surface); border:1px solid var(--border); border-radius:8px; color:var(--text); font-family:'DM Mono',monospace; font-size:0.8rem; padding:0.5rem 0.9rem; outline:none; transition:border-color 0.15s; }
  .search-bar input:focus { border-color:var(--purple); }
  .search-bar button { background:rgba(155,89,232,0.15); border:1px solid rgba(155,89,232,0.3); color:var(--accent); font-family:'DM Mono',monospace; font-size:0.78rem; padding:0.5rem 1rem; border-radius:8px; cursor:pointer; }
  .reset-link { font-family:'DM Mono',monospace; font-size:0.78rem; color:var(--muted); padding:0.5rem 0.75rem; text-decoration:none; }
  .msg-card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.6rem; transition:border-color 0.15s; }
  .msg-card:hover { border-color:var(--purple); }
  .msg-meta { display:flex; gap:0.6rem; align-items:center; flex-wrap:wrap; margin-bottom:0.45rem; }
  .msg-user { font-weight:700; font-size:0.85rem; color:var(--accent); }
  .msg-id, .msg-ch { font-family:'DM Mono',monospace; font-size:0.67rem; color:var(--muted); }
  .msg-ts { font-family:'DM Mono',monospace; font-size:0.67rem; color:var(--muted); margin-left:auto; }
  .msg-content { font-size:0.875rem; line-height:1.55; color:var(--text); word-break:break-word; white-space:pre-wrap; }
  .pagination { display:flex; gap:0.4rem; justify-content:center; flex-wrap:wrap; margin-top:1.5rem; }
  .page-btn { font-family:'DM Mono',monospace; font-size:0.72rem; padding:0.35rem 0.7rem; border-radius:6px; text-decoration:none; color:var(--muted); border:1px solid var(--border); transition:all 0.15s; }
  .page-btn:hover, .page-btn.cur { background:rgba(155,89,232,0.12); color:var(--accent); border-color:rgba(155,89,232,0.3); }
  .total-label { font-family:'DM Mono',monospace; font-size:0.68rem; color:var(--muted); margin-bottom:1rem; }
</style>
</head><body>
<header>
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <nav>
    <a href="/" class="nav-link">📊 Statistiche</a>
    <a href="/messages" class="nav-link active">💬 Messaggi</a>
    <a href="/logs" class="nav-link">🪵 Log</a>
    <a href="/plans" class="nav-link">💎 Piani</a>
    <a href="/broadcast" class="nav-link">📣 Broadcast</a>
  </nav>
  <div class="header-right"><span class="badge">🧪 BETA</span><a href="/messages" class="refresh-btn">↻</a><a href="/logout" class="logout-btn">Esci</a></div>
</header>
<main>
  <p class="section-label">Messaggi utenti</p>
  <form method="GET" action="/messages" class="search-bar">
    <input type="text" name="q" placeholder="Cerca per username o user ID..." value="{{ q }}">
    <button type="submit">Cerca</button>
    {% if q %}<a href="/messages" class="reset-link">✕ Annulla</a>{% endif %}
  </form>
  <p class="total-label">{{ total }} messaggi — pagina {{ page }} di {{ total_pages }}</p>
  {% for m in messages %}
  <div class="msg-card">
    <div class="msg-meta">
      <span class="msg-user">{{ m.username }}</span>
      <span class="msg-id">{{ m.user_id }}</span>
      <span class="msg-ch">canale:{{ m.channel_id }}</span>
      <span class="msg-ts">{{ m.ts }}</span>
    </div>
    <div class="msg-content">{{ m.content }}</div>
  </div>
  {% else %}
  <p style="color:var(--muted);font-family:'DM Mono',monospace;font-size:0.8rem">Nessun messaggio trovato.</p>
  {% endfor %}
  {% if total_pages > 1 %}
  <div class="pagination">
    {% if page > 1 %}<a href="/messages?page={{ page-1 }}&q={{ q }}" class="page-btn">← Prec</a>{% endif %}
    {% for p in range([1, page-2]|max, [total_pages+1, page+3]|min) %}
      <a href="/messages?page={{ p }}&q={{ q }}" class="page-btn {% if p == page %}cur{% endif %}">{{ p }}</a>
    {% endfor %}
    {% if page < total_pages %}<a href="/messages?page={{ page+1 }}&q={{ q }}" class="page-btn">Succ →</a>{% endif %}
  </div>
  {% endif %}
</main>
<footer>purpleGPT Dashboard &nbsp;·&nbsp; jLabs by justmarcolin &nbsp;·&nbsp; {{ now }}</footer>
</body></html>
"""

# ── Logs HTML ──────────────────────────────────────────────────────────────────

HTML_LOGS = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Log</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
{{ css | safe }}
  .log-controls { display:flex; gap:0.5rem; margin-bottom:1.25rem; flex-wrap:wrap; align-items:center; }
  .log-filter-btn { font-family:'DM Mono',monospace; font-size:0.7rem; padding:0.3rem 0.75rem; border-radius:6px; text-decoration:none; border:1px solid var(--border); color:var(--muted); transition:all 0.15s; cursor:pointer; background:none; }
  .log-filter-btn:hover { border-color:var(--purple); color:var(--accent); }
  .log-filter-btn.active { background:rgba(155,89,232,0.15); border-color:var(--purple); color:var(--accent); }
  .log-filter-btn.err  { border-color:rgba(248,113,113,0.3); color:var(--red); }
  .log-filter-btn.err.active { background:rgba(248,113,113,0.1); }
  .log-filter-btn.warn { border-color:rgba(251,191,36,0.3); color:#fbbf24; }
  .log-filter-btn.warn.active { background:rgba(251,191,36,0.08); }
  .log-wrap { background:var(--surface); border:1px solid var(--border); border-radius:12px; overflow:hidden; }
  .log-line { display:flex; gap:0.75rem; align-items:baseline; padding:0.4rem 1rem; border-bottom:1px solid rgba(30,30,46,0.6); font-family:'DM Mono',monospace; font-size:0.73rem; line-height:1.5; }
  .log-line:last-child { border-bottom:none; }
  .log-line:hover { background:rgba(155,89,232,0.04); }
  .log-line.ERROR   { background:rgba(248,113,113,0.05); }
  .log-line.WARNING { background:rgba(251,191,36,0.04); }
  .log-badge { flex-shrink:0; font-size:0.62rem; padding:0.1rem 0.4rem; border-radius:4px; font-weight:500; letter-spacing:0.04em; }
  .badge-INFO    { background:rgba(155,89,232,0.15); color:var(--accent); }
  .badge-ERROR   { background:rgba(248,113,113,0.2); color:var(--red); }
  .badge-WARNING { background:rgba(251,191,36,0.15); color:#fbbf24; }
  .badge-DEBUG   { background:rgba(100,116,139,0.15); color:var(--muted); }
  .log-text { color:var(--text); word-break:break-all; }
  .log-empty { padding:2rem; text-align:center; font-family:'DM Mono',monospace; font-size:0.8rem; color:var(--muted); }
  .log-count { font-family:'DM Mono',monospace; font-size:0.7rem; color:var(--muted); margin-left:auto; }
</style>
</head><body>
<header>
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <nav>
    <a href="/" class="nav-link">📊 Statistiche</a>
    <a href="/messages" class="nav-link">💬 Messaggi</a>
    <a href="/logs" class="nav-link active">🪵 Log</a>
    <a href="/plans" class="nav-link">💎 Piani</a>
    <a href="/broadcast" class="nav-link">📣 Broadcast</a>
  </nav>
  <div class="header-right"><span class="badge">🧪 BETA</span><a href="/logs?level={{ level }}" class="refresh-btn">↻</a><a href="/logout" class="logout-btn">Esci</a></div>
</header>
<main>
  <p class="section-label">Log di sistema</p>
  <div class="log-controls">
    <a href="/logs?level=ALL"     class="log-filter-btn {% if level == 'ALL' %}active{% endif %}">TUTTI</a>
    <a href="/logs?level=INFO"    class="log-filter-btn {% if level == 'INFO' %}active{% endif %}">INFO</a>
    <a href="/logs?level=WARNING" class="log-filter-btn warn {% if level == 'WARNING' %}active{% endif %}">WARNING</a>
    <a href="/logs?level=ERROR"   class="log-filter-btn err {% if level == 'ERROR' %}active{% endif %}">ERROR</a>
    <span class="log-count">{{ logs | length }} righe</span>
  </div>
  <div class="log-wrap">
    {% for entry in logs %}
    <div class="log-line {{ entry.level }}">
      <span class="log-badge badge-{{ entry.level }}">{{ entry.level }}</span>
      <span class="log-text">{{ entry.text }}</span>
    </div>
    {% else %}
    <div class="log-empty">
      {% if level != 'ALL' %}Nessun log con livello {{ level }}.{% else %}Nessun log trovato.{% endif %}
    </div>
    {% endfor %}
  </div>
</main>
<footer>purpleGPT Dashboard &nbsp;·&nbsp; jLabs by justmarcolin &nbsp;·&nbsp; {{ now }}</footer>
</body></html>
"""

# ── Broadcast HTML ─────────────────────────────────────────────────────────────

HTML_BROADCAST = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Broadcast</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
{{ css | safe }}
  .broadcast-form { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:1.5rem; margin-bottom:1.5rem; }
  .form-group { margin-bottom:1rem; }
  .form-group label { display:block; font-family:'DM Mono',monospace; font-size:0.68rem; color:var(--muted); margin-bottom:0.35rem; }
  .form-group input, .form-group textarea, .form-group select {
    width:100%; background:rgba(255,255,255,0.04); border:1px solid var(--border);
    border-radius:8px; color:var(--text); font-family:'DM Mono',monospace;
    font-size:0.82rem; padding:0.55rem 0.9rem; outline:none; transition:border-color 0.15s;
  }
  .form-group input:focus, .form-group textarea:focus, .form-group select:focus { border-color:var(--purple); }
  .form-group textarea { resize:vertical; min-height:120px; }
  .form-group select { cursor:pointer; }
  .type-avviso  { border-left:3px solid #fbbf24; }
  .type-changelog { border-left:3px solid var(--green); }
  .btn-broadcast {
    background:linear-gradient(135deg, var(--purple), var(--purple2));
    border:none; border-radius:8px; color:#fff; font-family:'Syne',sans-serif;
    font-size:0.9rem; font-weight:700; padding:0.7rem 1.5rem; cursor:pointer; transition:opacity 0.15s;
  }
  .btn-broadcast:hover { opacity:0.9; }
  .history-item { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.6rem; }
  .history-meta { display:flex; gap:0.75rem; align-items:center; margin-bottom:0.4rem; flex-wrap:wrap; }
  .history-type-avviso    { font-family:'DM Mono',monospace; font-size:0.65rem; background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.25); padding:0.15rem 0.5rem; border-radius:4px; }
  .history-type-changelog { font-family:'DM Mono',monospace; font-size:0.65rem; background:rgba(52,211,153,0.12); color:var(--green); border:1px solid rgba(52,211,153,0.25); padding:0.15rem 0.5rem; border-radius:4px; }
  .history-title { font-weight:700; font-size:0.88rem; }
  .history-ts { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); margin-left:auto; }
  .history-servers { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--muted); }
  .history-body { font-size:0.82rem; color:var(--muted); margin-top:0.3rem; white-space:pre-wrap; word-break:break-word; }
  .divider { border:none; border-top:1px solid var(--border); margin:1.5rem 0; }
</style>
</head><body>
<header>
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <nav>
    <a href="/" class="nav-link">📊 Statistiche</a>
    <a href="/messages" class="nav-link">💬 Messaggi</a>
    <a href="/logs" class="nav-link">🪵 Log</a>
    <a href="/plans" class="nav-link">💎 Piani</a>
    <a href="/broadcast" class="nav-link active">📣 Broadcast</a>
  </nav>
  <div class="header-right"><span class="badge">🧪 BETA</span><a href="/broadcast" class="refresh-btn">↻</a><a href="/logout" class="logout-btn">Esci</a></div>
</header>
<main>

  {% if flash %}<div class="flash-ok">✓ {{ flash }}</div>{% endif %}
  {% if error %}<div class="flash-err">✗ {{ error }}</div>{% endif %}

  <p class="section-label">Nuovo broadcast</p>

  <div class="broadcast-form">
    <form method="POST" action="/broadcast/send">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="form-group">
        <label>Tipo</label>
        <select name="type">
          <option value="avviso">⚠️ Avviso — comunicazioni urgenti, manutenzione</option>
          <option value="changelog">📋 Changelog — nuove funzionalità, aggiornamenti</option>
        </select>
      </div>
      <div class="form-group">
        <label>Titolo</label>
        <input type="text" name="title" placeholder="Es: Manutenzione programmata / purpleGPT v1.3" required maxlength="100">
      </div>
      <div class="form-group">
        <label>Messaggio</label>
        <textarea name="body" placeholder="Testo del messaggio inviato nei server..." required maxlength="1500"></textarea>
      </div>
      <div class="form-group">
        <label>Versione (solo changelog, opzionale)</label>
        <input type="text" name="version" placeholder="Es: 1.3.0" maxlength="20">
      </div>
      <div class="form-group">
        <label>Destinatario</label>
        <select name="target_guild_id">
          <option value="">📡 Tutti i server</option>
          {% for g in guilds %}
          <option value="{{ g.id }}">🖥️ {{ g.name }} ({{ g.member_count }} membri)</option>
          {% endfor %}
          {% if not guilds %}
          <option disabled>— Bot non raggiungibile —</option>
          {% endif %}
        </select>
      </div>
      <button type="submit" class="btn-broadcast">📣 Invia</button>
    </form>
  </div>

  <hr class="divider">
  <p class="section-label">Ultimi broadcast inviati</p>

  {% for h in history %}
  <div class="history-item">
    <div class="history-meta">
      {% if h.type == 'avviso' %}
        <span class="history-type-avviso">⚠️ Avviso</span>
      {% else %}
        <span class="history-type-changelog">📋 Changelog</span>
      {% endif %}
      <span class="history-title">{{ h.title }}</span>
      {% if h.version %}<span style="font-family:'DM Mono',monospace;font-size:0.65rem;color:var(--muted)">v{{ h.version }}</span>{% endif %}
      <span class="history-ts">{{ h.sent_at }}</span>
      <span class="history-servers">{% if h.target_guild_id and h.target_guild_id != "tutti" %}🎯 server specifico{% else %}📡 tutti{% endif %} · {{ h.servers_reached }} raggiunto/i</span>
    </div>
    <div class="history-body">{{ h.body }}</div>
  </div>
  {% else %}
  <p style="color:var(--muted);font-family:'DM Mono',monospace;font-size:0.8rem">Nessun broadcast inviato.</p>
  {% endfor %}

</main>
<footer>purpleGPT Dashboard &nbsp;·&nbsp; jLabs by justmarcolin &nbsp;·&nbsp; {{ now }}</footer>
</body></html>
"""

# ── Routes: Auth ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    # Se già autenticato, vai alla dashboard
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    next_url = request.args.get("next", "/")
    error    = None
    ip       = _get_client_ip()

    if request.method == "POST":
        next_url  = request.form.get("next", "/")
        username  = request.form.get("username", "").strip()
        password  = request.form.get("password", "")

        if not _validate_csrf():
            return "CSRF token non valido.", 403

        if _is_locked_out(ip):
            return render_template_string(HTML_LOGIN, lockout=True, error=None, next=next_url)

        if _check_credentials(username, password):
            _reset_attempts(ip)
            session.permanent = True
            session["authenticated"] = True
            return redirect(_safe_next_url(next_url))
        else:
            _record_failed_attempt(ip)
            # Messaggio generico — non rivela se username o password è sbagliata
            error = "Credenziali non valide."

    if _is_locked_out(ip):
        return render_template_string(HTML_LOGIN, lockout=True, error=None, next=next_url)

    return render_template_string(HTML_LOGIN, lockout=False, error=error, next=next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Routes: Dashboard ─────────────────────────────────────────────────────────

@app.route("/")
@require_login
def dashboard():
    stats  = fetch_stats()
    users  = fetch_users()
    now    = datetime.now().strftime("%d/%m/%Y %H:%M")
    msgs   = get_flashed_messages(with_categories=True)
    flash  = next((m for c, m in msgs if c == "ok"), "")
    error  = next((m for c, m in msgs if c == "err"), "")
    return render_template_string(HTML_DASH, css=COMMON_CSS, stats=stats, users=users, now=now, flash=flash, error=error)


@app.route("/messages")
@require_login
def messages_view():
    page     = max(1, int(request.args.get("page", 1)))
    q        = request.args.get("q", "").strip()
    messages, total, total_pages = fetch_messages(page, q)
    now      = datetime.now().strftime("%d/%m/%Y %H:%M")
    return render_template_string(
        HTML_MESSAGES, css=COMMON_CSS,
        messages=messages, total=total, total_pages=total_pages,
        page=page, q=q, now=now
    )


@app.route("/logs")
@require_login
def logs_view():
    level = request.args.get("level", "ALL").upper()
    if level not in ("ALL", "INFO", "WARNING", "ERROR", "DEBUG"):
        level = "ALL"
    logs = fetch_logs(level)
    now  = datetime.now().strftime("%d/%m/%Y %H:%M")
    return render_template_string(HTML_LOGS, css=COMMON_CSS, logs=logs, level=level, now=now)


@app.route("/set_plan", methods=["POST"])
@require_login
def set_plan():
    if not _validate_csrf():
        return "CSRF token non valido.", 403

    user_id  = request.form.get("user_id", "").strip()
    action   = request.form.get("action", "").strip()
    plan     = request.form.get("plan", "starter").strip()
    days     = request.form.get("days", "30").strip()
    is_trial = request.form.get("is_trial", "0") == "1"

    if not user_id.isdigit():
        return "user_id non valido.", 400
    if action not in ("grant", "revoke"):
        return "Azione non valida.", 400
    if action == "grant" and plan not in ("starter", "pro"):
        return "Piano non valido (usa starter o pro).", 400

    # Per i trial, forza 7 giorni indipendentemente dal valore inviato
    if is_trial:
        days_int = 7
    else:
        try:
            days_int = max(1, min(365, int(days)))
        except ValueError:
            days_int = 30

    conn = get_db()
    if action == "grant":
        expires = (datetime.now(timezone.utc) + timedelta(days=days_int)).isoformat()
        conn.execute(
            "INSERT INTO user_plans (user_id, plan, expires_at, is_trial) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  plan       = excluded.plan, "
            "  expires_at = excluded.expires_at, "
            "  is_trial   = excluded.is_trial",
            (user_id, plan, expires, 1 if is_trial else 0)
        )
        label = f"{plan} ({'PROVA ' if is_trial else ''}{days_int} giorni)"
        flask_flash(f"Piano '{label}' attivato per {user_id}.", "ok")
    else:
        conn.execute(
            "INSERT INTO user_plans (user_id, plan, expires_at, is_trial) "
            "VALUES (?, 'free', NULL, 0) "
            "ON CONFLICT(user_id) DO UPDATE SET plan='free', expires_at=NULL, is_trial=0",
            (user_id,)
        )
        flask_flash(f"Piano reimpostato su Free per {user_id}.", "ok")

    conn.commit()
    conn.close()
    return redirect("/plans")


# ── Routes: Plans (UI) ────────────────────────────────────────────────────────

def fetch_active_plans():
    """Restituisce tutti gli utenti con un piano a pagamento attivo, dal più recente."""
    conn  = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows  = conn.execute("""
        SELECT p.user_id, p.plan, p.expires_at,
               COALESCE(p.is_trial, 0) AS is_trial,
               COALESCE(u.username, p.user_id) AS username
        FROM user_plans p
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.plan IN ('starter', 'pro', 'premium')
        ORDER BY p.expires_at DESC
    """).fetchall()
    conn.close()

    active = []
    for r in rows:
        expired = False
        expires_str = "—"
        if r["expires_at"]:
            try:
                exp         = datetime.fromisoformat(r["expires_at"])
                expired     = exp.strftime("%Y-%m-%d") < today
                expires_str = exp.strftime("%Y-%m-%d")
            except Exception:
                expires_str = r["expires_at"][:10]
        active.append({
            "user_id":  r["user_id"],
            "username": r["username"],
            "plan":     r["plan"],
            "expires":  expires_str,
            "expired":  expired,
            "is_trial": bool(r["is_trial"]),
        })
    return active


@app.route("/plans")
@require_login
def plans_page():
    active = fetch_active_plans()
    stats  = fetch_stats()
    msgs   = get_flashed_messages(with_categories=True)
    flash  = next((m for c, m in msgs if c == "ok"), "")
    error  = next((m for c, m in msgs if c == "err"), "")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M")
    return render_template_string(
        HTML_PLANS,
        css=COMMON_CSS,
        active=active,
        stats=stats,
        flash=flash,
        error=error,
        now=now,
    )


HTML_PLANS = """
<!DOCTYPE html><html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>purpleGPT — Piani</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>{{ css | safe }}</style>
<style>
.plan-form{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.5rem;margin-bottom:2rem}
.plan-form h3{font-family:'Syne',sans-serif;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--accent2);margin-bottom:1rem}
.plan-form .grid{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:0.75rem;align-items:end}
.plan-form label{display:block;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-bottom:0.35rem;font-family:'DM Mono',monospace}
.plan-form input,.plan-form select{width:100%;background:var(--surf2);border:1px solid var(--border);border-radius:8px;padding:0.55rem 0.7rem;color:var(--text);font-family:'DM Mono',monospace;font-size:0.88rem}
.plan-form input:focus,.plan-form select:focus{outline:none;border-color:var(--accent2);box-shadow:0 0 0 2px rgba(155,89,232,0.15)}
.plan-form button{background:linear-gradient(135deg,var(--accent1),var(--accent2));color:#fff;border:none;border-radius:8px;padding:0.7rem 1.2rem;font-family:'Syne',sans-serif;font-weight:600;cursor:pointer;font-size:0.85rem;white-space:nowrap}
.plan-form button:hover{filter:brightness(1.1)}
.plan-form .help{font-size:0.72rem;color:var(--muted);margin-top:0.5rem;font-family:'DM Mono',monospace}
.revoke-btn{background:transparent;border:1px solid var(--border);color:var(--muted);padding:0.35rem 0.7rem;border-radius:6px;cursor:pointer;font-size:0.72rem;font-family:'DM Mono',monospace;transition:all 0.15s}
.revoke-btn:hover{border-color:#ef4444;color:#ef4444}
@media(max-width:720px){.plan-form .grid{grid-template-columns:1fr;gap:0.5rem}}
</style>
</head><body>
<header>
  <div class="logo">🟣</div>
  <h1><span>purple</span>GPT</h1>
  <nav>
    <a href="/" class="nav-link">📊 Statistiche</a>
    <a href="/messages" class="nav-link">💬 Messaggi</a>
    <a href="/logs" class="nav-link">🪵 Log</a>
    <a href="/plans" class="nav-link active">💎 Piani</a>
    <a href="/broadcast" class="nav-link">📣 Broadcast</a>
  </nav>
  <div class="header-right">
    <span class="badge">🧪 BETA</span>
    <a href="/plans" class="refresh-btn">↻</a>
    <a href="/logout" class="logout-btn">Esci</a>
  </div>
</header>
<main>

  {% if flash %}<div class="flash-ok">✓ {{ flash }}</div>{% endif %}
  {% if error %}<div class="flash-err">✗ {{ error }}</div>{% endif %}

  <p class="section-label">Piani attivi</p>
  <div class="cards">
    <div class="card"><div class="card-label">⚡ Starter</div><div class="card-value">{{ stats.starter_users }}</div><div class="card-sub">abbonati attivi</div></div>
    <div class="card"><div class="card-label">🚀 Pro</div><div class="card-value">{{ stats.pro_users }}</div><div class="card-sub">abbonati attivi</div></div>
    <div class="card"><div class="card-label">✨ Totali</div><div class="card-value">{{ stats.premium_users }}</div><div class="card-sub">paganti</div></div>
  </div>

  <p class="section-label">Attiva un abbonamento</p>
  <form class="plan-form" method="POST" action="/set_plan">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <h3>Assegna un piano a un utente Discord</h3>
    <div class="grid">
      <div>
        <label>ID Utente Discord</label>
        <input type="text" name="user_id" placeholder="es. 123456789012345678" pattern="[0-9]+" required>
      </div>
      <div>
        <label>Piano</label>
        <select name="plan" required>
          <option value="starter">⚡ Starter — €1.99/mese</option>
          <option value="pro">🚀 Pro — €3.99/mese</option>
        </select>
      </div>
      <div>
        <label>Durata (giorni)</label>
        <input type="number" name="days" id="days-input" value="30" min="1" max="365" required>
      </div>
      <input type="hidden" name="action" value="grant">
      <button type="submit">✨ Attiva</button>
    </div>
    <div style="margin-top:1rem;display:flex;align-items:center;gap:0.5rem">
      <input type="checkbox" name="is_trial" id="is-trial" value="1" style="width:18px;height:18px;accent-color:var(--accent2);cursor:pointer">
      <label for="is-trial" style="display:inline;font-size:0.82rem;color:var(--text);cursor:pointer;margin:0;text-transform:none;letter-spacing:0;font-family:'Syne',sans-serif">
        🎁 Prova gratuita (Trial) <span style="color:var(--muted);font-size:0.75rem">(imposta 7 giorni, contrassegnato come "Trial" per l'utente)</span>
      </label>
    </div>
    <p class="help">Dopo che un utente completa il pagamento su Stripe, inserisci il suo Discord User ID, seleziona il piano e clicca "Attiva". Spunta "Prova gratuita" per attivare il periodo di prova di 7 giorni.</p>
  </form>

  <script>
    // Auto-set days to 7 when trial is checked, restore 30 when unchecked
    (function(){
      var cb  = document.getElementById('is-trial');
      var inp = document.getElementById('days-input');
      if(!cb || !inp) return;
      cb.addEventListener('change', function(){
        if(cb.checked){ inp.value = 7; inp.disabled = true; }
        else          { inp.value = 30; inp.disabled = false; }
      });
    })();
  </script>

  <p class="section-label">Abbonamenti attivi</p>
  {% if active %}
  <div class="table-scroll">
  <table>
    <tr><th>Username</th><th>User ID</th><th>Piano</th><th>Scadenza</th><th>Stato</th><th>Azioni</th></tr>
    {% for u in active %}
    <tr>
      <td>{{ u.username }}</td>
      <td><code style="font-size:0.7rem;color:var(--muted)">{{ u.user_id }}</code></td>
      <td>
        {% if u.plan == 'pro' %}
          <span class="badge-premium">🚀 Pro</span>
        {% elif u.plan == 'starter' %}
          <span class="badge-premium">⚡ Starter</span>
        {% else %}
          <span class="badge-premium">✨ {{ u.plan }}</span>
        {% endif %}
        {% if u.is_trial %}
          <span style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.3);padding:0.15rem 0.5rem;border-radius:6px;font-size:0.68rem;font-family:'DM Mono',monospace;margin-left:0.3rem">🎁 PROVA</span>
        {% endif %}
      </td>
      <td><span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted)">{{ u.expires }}</span></td>
      <td>
        {% if u.expired %}
          <span class="badge-expired">⌛ Scaduto</span>
        {% else %}
          <span style="color:#22c55e;font-size:0.75rem;font-family:'DM Mono',monospace">● Attivo</span>
        {% endif %}
      </td>
      <td>
        <form class="action-form" method="POST" action="/set_plan" onsubmit="return confirm('Revocare il piano di {{ u.username }}? L''utente tornerà al piano free.');">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <input type="hidden" name="user_id" value="{{ u.user_id }}">
          <input type="hidden" name="action" value="revoke">
          <button class="revoke-btn" type="submit">Revoca</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
  </div>
  {% else %}
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:2rem;text-align:center;color:var(--muted);font-family:'DM Mono',monospace;font-size:0.85rem">
    Nessun abbonamento attivo al momento. Attivane uno sopra ↑
  </div>
  {% endif %}

</main>
<footer>purpleGPT Dashboard &nbsp;·&nbsp; jLabs by justmarcolin &nbsp;·&nbsp; {{ now }}</footer>
</body></html>
"""


# ── Routes: Broadcast (UI) ────────────────────────────────────────────────────

@app.route("/broadcast")
@require_login
def broadcast_page():
    history = fetch_broadcast_history()
    guilds  = _bot_get_guilds() or []
    now     = datetime.now().strftime("%d/%m/%Y %H:%M")
    msgs    = get_flashed_messages(with_categories=True)
    flash   = next((m for c, m in msgs if c == "ok"), "")
    error   = next((m for c, m in msgs if c == "err"), "")
    return render_template_string(
        HTML_BROADCAST, css=COMMON_CSS,
        history=history, guilds=guilds, now=now, flash=flash, error=error
    )


@app.route("/broadcast/send", methods=["POST"])
@require_login
def broadcast_send():
    """Invio broadcast dalla UI della dashboard."""
    if not _validate_csrf():
        return "CSRF token non valido.", 403

    return _do_broadcast(
        btype           = request.form.get("type", "avviso").strip(),
        title           = request.form.get("title", "").strip(),
        body            = request.form.get("body", "").strip(),
        version         = request.form.get("version", "").strip(),
        target_guild_id = request.form.get("target_guild_id", "").strip(),
    )


@app.route("/api/broadcast", methods=["POST"])
@require_broadcast_auth
def broadcast_api():
    """
    Endpoint API per broadcast programmatico.
    Autenticazione: header Authorization: Bearer <BROADCAST_SECRET>

    Payload JSON:
      {
        "type":    "avviso" | "changelog",   (default: "avviso")
        "title":   "Titolo del messaggio",
        "body":    "Corpo del messaggio",
        "version": "1.3.0"                   (opzionale, solo changelog)
      }
    """
    data = request.get_json(silent=True) or {}
    result = _do_broadcast(
        btype           = str(data.get("type", "avviso")).strip(),
        title           = str(data.get("title", "")).strip(),
        body            = str(data.get("body", "")).strip(),
        version         = str(data.get("version", "")).strip(),
        target_guild_id = str(data.get("target_guild_id", "")).strip(),
        api_mode        = True,
    )
    # In API mode ritorna JSON invece di redirect
    if isinstance(result, tuple):
        return result
    return jsonify({"ok": True, "message": "Broadcast inviato"}), 200


def _do_broadcast(btype: str, title: str, body: str, version: str = "", target_guild_id: str = "", api_mode: bool = False):
    """Logica condivisa tra UI e API per inviare il broadcast."""
    # Validazione
    if btype not in ("avviso", "changelog"):
        btype = "avviso"
    if not title or not body:
        if api_mode:
            return jsonify({"error": "title e body sono obbligatori"}), 400
        flask_flash("Titolo e messaggio sono obbligatori.", "err")
        return redirect("/broadcast")
    if target_guild_id and not target_guild_id.isdigit():
        if api_mode:
            return jsonify({"error": "target_guild_id non valido"}), 400
        flask_flash("Destinatario non valido.", "err")
        return redirect("/broadcast")

    # Tronca per sicurezza
    title   = title[:100]
    body    = body[:1500]
    version = version[:20]

    # Invia tramite il server IPC interno del bot
    servers_reached = _bot_send_broadcast(btype, title, body, version, target_guild_id)
    if servers_reached == -1:
        if api_mode:
            return jsonify({"error": "Bot non raggiungibile — assicurati che sia in esecuzione"}), 503
        flask_flash("Bot non raggiungibile — assicurati che sia in esecuzione.", "err")
        return redirect("/broadcast")

    # Salva nella history
    entry = {
        "type":            btype,
        "title":           title,
        "body":            body,
        "version":         version,
        "target_guild_id": target_guild_id or "tutti",
        "sent_at":         datetime.now().strftime("%d/%m/%Y %H:%M"),
        "servers_reached": servers_reached,
    }
    save_broadcast_history(entry)

    if api_mode:
        return None  # il chiamante gestisce la risposta

    flask_flash(f"Broadcast inviato a {servers_reached} server.", "ok")
    return redirect("/broadcast")



# ── Avvio ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    # In produzione Flask gira dietro Nginx — debug=False sempre
    app.run(host="127.0.0.1", port=port, debug=False)
