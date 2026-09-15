"""
history_manager.py — Gestione della memoria di conversazione e privacy GDPR.

Questo modulo si occupa di:
- Salvare e recuperare i messaggi del canale (fino a 20 messaggi per canale per la memoria dell'AI).
- Offrire funzioni GDPR per l'export completo dei dati utente in formato JSON (`export_user_data`).
- Permettere la cancellazione definitiva di tutti i dati associati a un utente (`delete_user_data`).
- Mantenere lo storico delle ultime 5 attività creative dell'utente per arricchire il contesto delle risposte.
"""

from datetime import datetime, timezone
from bot_managers.db import get_conn

MAX_MESSAGES = 20
MAX_USER_ACTIVITIES = 5


def _ensure_channel(conn, channel_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO channel_settings (channel_id, enabled) VALUES (?, 1)",
        (channel_id,)
    )


def set_enabled(channel_id: int, value: bool) -> None:
    cid = str(channel_id)
    with get_conn() as conn:
        _ensure_channel(conn, cid)
        conn.execute(
            "UPDATE channel_settings SET enabled = ? WHERE channel_id = ?",
            (int(value), cid)
        )
        conn.commit()


def clear(channel_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE channel_id = ?", (str(channel_id),))
        conn.commit()


def add_message(channel_id: int, role: str, content: str,
                user_id: str = None, username: str = None) -> None:
    cid = str(channel_id)
    with get_conn() as conn:
        _ensure_channel(conn, cid)
        row = conn.execute(
            "SELECT enabled FROM channel_settings WHERE channel_id = ?", (cid,)
        ).fetchone()
        if not row or not row["enabled"]:
            return

        conn.execute(
            "INSERT INTO messages (channel_id, role, content, timestamp, user_id, username) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (cid, role, content, datetime.now(timezone.utc).isoformat(), user_id, username)
        )

        conn.execute(
            "DELETE FROM messages WHERE channel_id = ? AND id NOT IN ("
            "    SELECT id FROM messages WHERE channel_id = ? ORDER BY id DESC LIMIT ?"
            ")",
            (cid, cid, MAX_MESSAGES)
        )
        conn.commit()


def get_context(channel_id: int) -> list:
    cid = str(channel_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled FROM channel_settings WHERE channel_id = ?", (cid,)
        ).fetchone()
        if not row or not row["enabled"]:
            return []
        msgs = conn.execute(
            "SELECT role, content, user_id, username FROM messages "
            "WHERE channel_id = ? ORDER BY id ASC", (cid,)
        ).fetchall()
    return [dict(m) for m in msgs]


def delete_user_data(user_id: str) -> None:
    uid = str(user_id)
    with get_conn() as conn:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM messages WHERE user_id = ?", (uid,)
        ).fetchall()]
        for mid in ids:
            ai = conn.execute(
                "SELECT id FROM messages "
                "WHERE channel_id = (SELECT channel_id FROM messages WHERE id = ?) "
                "  AND id > ? AND role = 'ai' "
                "ORDER BY id ASC LIMIT 1",
                (mid, mid)
            ).fetchone()
            conn.execute("DELETE FROM messages WHERE id = ?", (mid,))
            if ai:
                conn.execute("DELETE FROM messages WHERE id = ?", (ai["id"],))

        # Cancella anche le immagini generate dall'utente
        conn.execute("DELETE FROM generated_images WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_activities WHERE user_id = ?", (uid,))
        conn.commit()


def export_user_data(user_id: str, username: str) -> dict:
    uid = str(user_id)
    with get_conn() as conn:
        channels = [r["channel_id"] for r in conn.execute(
            "SELECT DISTINCT channel_id FROM messages WHERE user_id = ?", (uid,)
        ).fetchall()]
        data = []
        for cid in channels:
            rows = list(conn.execute(
                "SELECT id, role, content, timestamp, user_id FROM messages "
                "WHERE channel_id = ? ORDER BY id ASC", (cid,)
            ).fetchall())
            collected = []
            for i, m in enumerate(rows):
                if m["user_id"] == uid:
                    collected.append({
                        "role": "user",
                        "content": m["content"],
                        "time": m["timestamp"]
                    })
                    if i + 1 < len(rows) and rows[i + 1]["role"] == "ai":
                        a = rows[i + 1]
                        collected.append({
                            "role": "ai",
                            "content": a["content"],
                            "time": a["timestamp"]
                        })
            if collected:
                data.append({"channel_id": cid, "messages": collected})
        activities = [
            dict(row) for row in conn.execute(
                "SELECT command, prompt, status, guild_id, channel_id, timestamp "
                "FROM user_activities WHERE user_id = ? ORDER BY id ASC",
                (uid,)
            ).fetchall()
        ]
    return {
        "user": {
            "user_id": uid,
            "username": username,
            "export_time": datetime.now(timezone.utc).isoformat()
        },
        "data": data,
        "activities": activities
    }


def save_user_activity(
    user_id: str,
    command: str,
    prompt: str,
    status: str = "success",
    guild_id: int | str | None = None,
    channel_id: int | str | None = None,
) -> None:
    """Salva una richiesta creativa recente dell'utente, tenendo solo le ultime 5."""
    uid = str(user_id)
    clean_command = str(command or "").strip()[:32]
    clean_prompt = " ".join(str(prompt or "").split())[:500]
    clean_status = str(status or "success").strip()[:32]

    if not uid or not clean_command or not clean_prompt:
        return

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_activities "
            "(user_id, command, prompt, status, guild_id, channel_id, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                uid,
                clean_command,
                clean_prompt,
                clean_status,
                str(guild_id) if guild_id is not None else None,
                str(channel_id) if channel_id is not None else None,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.execute(
            "DELETE FROM user_activities WHERE user_id = ? AND id NOT IN ("
            "    SELECT id FROM user_activities WHERE user_id = ? ORDER BY id DESC LIMIT ?"
            ")",
            (uid, uid, MAX_USER_ACTIVITIES)
        )
        conn.commit()


def get_recent_user_activities(user_id: str, limit: int = MAX_USER_ACTIVITIES) -> list[dict]:
    """Ritorna le ultime attivita creative dell'utente, dalla piu vecchia alla piu recente."""
    uid = str(user_id)
    safe_limit = max(1, min(int(limit or MAX_USER_ACTIVITIES), MAX_USER_ACTIVITIES))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT command, prompt, status, guild_id, channel_id, timestamp "
            "FROM user_activities WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (uid, safe_limit)
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


# ── Immagini generate ─────────────────────────────────────────────────────────

def save_generated_image(channel_id: int, user_id: str, message_id: int) -> None:
    """Salva il riferimento all'ultimo messaggio con immagine generata per un utente."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO generated_images (channel_id, user_id, message_id, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (str(channel_id), str(user_id), str(message_id), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()


def get_last_generated_image_id(channel_id: int, user_id: str) -> str | None:
    """
    Ritorna il message_id dell'ultima immagine generata da purpleGPT
    per questo specifico utente in questo canale.
    Ritorna None se non ne trova nessuna.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT message_id FROM generated_images "
            "WHERE channel_id = ? AND user_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (str(channel_id), str(user_id))
        ).fetchone()
    return row["message_id"] if row else None
