"""
tos_manager.py — Gestione accettazione Termini di Servizio (ToS).

Traccia se l'utente ha già accettato i Termini di Servizio e Privacy al primo utilizzo
del bot, memorizzando il timestamp di accettazione nel database.
"""

from datetime import datetime, timezone
from bot_managers.db import get_conn


def has_accepted(user_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT tos_accepted FROM users WHERE user_id = ?", (str(user_id),)
        ).fetchone()
    return bool(row and row["tos_accepted"])


def mark_accepted(user_id: str, username: str) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, tos_accepted, accepted_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username     = excluded.username,
                tos_accepted = 1,
                accepted_at  = excluded.accepted_at
        """, (str(user_id), username, datetime.now(timezone.utc).isoformat()))
        conn.commit()