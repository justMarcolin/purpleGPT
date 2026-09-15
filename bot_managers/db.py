"""
db.py — Connessione e inizializzazione del database SQLite.

Gestisce la creazione delle tabelle, le migrazioni dello schema e fornisce
connessioni SQLite ottimizzate in modalità WAL (Write-Ahead Logging).
"""

import sqlite3
import os

# Percorso assoluto basato sulla posizione di questo file — indipendente dalla
# directory di avvio del bot.
DB_FILE = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "purplegpt.db"))


def get_conn() -> sqlite3.Connection:
    """
    Crea e restituisce una connessione SQLite configurata per le alte prestazioni:
    - row_factory = sqlite3.Row per accedere alle colonne tramite nome
    - WAL mode per permettere letture concorrenti senza bloccare le scritture
    - Foreign keys abilitate esplicitamente per l'integrità referenziale
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """
    Inizializza lo schema del database SQLite (11 tabelle) ed esegue
    le migrazioni automatiche se il database esiste già da una versione precedente.
    """
    with get_conn() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      TEXT PRIMARY KEY,
                username     TEXT NOT NULL,
                tos_accepted INTEGER NOT NULL DEFAULT 0,
                accepted_at  TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_settings (
                channel_id TEXT PRIMARY KEY,
                enabled    INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                role       TEXT NOT NULL CHECK(role IN ('user','ai')),
                content    TEXT NOT NULL,
                timestamp  TEXT NOT NULL,
                user_id    TEXT,
                username   TEXT,
                FOREIGN KEY (channel_id)
                    REFERENCES channel_settings(channel_id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_channel
            ON messages(channel_id, id)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id       TEXT PRIMARY KEY,
                temperature   REAL NOT NULL DEFAULT 1.0,
                custom_prompt TEXT NOT NULL DEFAULT '',
                image_size    TEXT NOT NULL DEFAULT '1:1',
                language      TEXT NOT NULL DEFAULT 'en'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_images (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                message_id TEXT NOT NULL,
                timestamp  TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_genimg_user_channel
            ON generated_images(channel_id, user_id, id)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_activities (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                command    TEXT NOT NULL,
                prompt     TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'success',
                guild_id   TEXT,
                channel_id TEXT,
                timestamp  TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activities_user
            ON user_activities(user_id, id)
        """)

        # Piano utente (free/starter/pro) con flag prova gratuita
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_plans (
                user_id    TEXT PRIMARY KEY,
                plan       TEXT NOT NULL DEFAULT 'free',
                expires_at TEXT,
                is_trial   INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Contatore utilizzi mensili per gruppo comando
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id       TEXT NOT NULL,
                command_group TEXT NOT NULL,
                date          TEXT NOT NULL,
                count         INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, command_group, date)
            )
        """)

        # Cooldown per gruppo comando
        conn.execute("""
            CREATE TABLE IF NOT EXISTS command_cooldowns (
                user_id       TEXT NOT NULL,
                command_group TEXT NOT NULL,
                last_used     TEXT NOT NULL,
                PRIMARY KEY (user_id, command_group)
            )
        """)

        # Tracciamento setup iniziale per ogni server
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_setup (
                guild_id   TEXT PRIMARY KEY,
                setup_done INTEGER NOT NULL DEFAULT 0,
                setup_at   TEXT
            )
        """)

        # Prompt personalizzato del server + impostazioni broadcast e welcome
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_settings (
                guild_id            TEXT PRIMARY KEY,
                server_prompt       TEXT,
                broadcast_enabled   INTEGER NOT NULL DEFAULT 1,
                broadcast_channel_id TEXT,
                welcome_enabled     INTEGER NOT NULL DEFAULT 0,
                welcome_channel_id  TEXT
            )
        """)

        # Bonus voto mensile da top.gg
        # Vecchio schema: (user_id PK, date) per bonus giornaliero — sostituito con
        # accumulatore mensile (user_id, period) con contatori separati.
        try:
            cursor = conn.execute("PRAGMA table_info(vote_bonus)")
            cols = {row["name"] for row in cursor.fetchall()}
            # Vecchio schema con colonna 'date' ma senza 'period' — drop e ricreazione
            if cols and "date" in cols and "period" not in cols:
                conn.execute("DROP TABLE vote_bonus")
        except Exception:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS vote_bonus (
                user_id       TEXT NOT NULL,
                period        TEXT NOT NULL,
                image_bonus   INTEGER NOT NULL DEFAULT 0,
                compose_bonus INTEGER NOT NULL DEFAULT 0,
                votes_claimed INTEGER NOT NULL DEFAULT 0,
                last_vote_at  TEXT,
                PRIMARY KEY (user_id, period)
            )
        """)

        # Migrazioni per database già esistenti
        for migration in [
            "ALTER TABLE user_settings ADD COLUMN image_size TEXT NOT NULL DEFAULT '1:1'",
            "ALTER TABLE user_settings ADD COLUMN language TEXT NOT NULL DEFAULT 'en'",
            "ALTER TABLE server_settings ADD COLUMN broadcast_enabled INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE server_settings ADD COLUMN broadcast_channel_id TEXT",
            "ALTER TABLE server_settings ADD COLUMN welcome_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE server_settings ADD COLUMN welcome_channel_id TEXT",
            "ALTER TABLE user_plans ADD COLUMN is_trial INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass  # colonna già presente, ignorato

        # Migrazione bonus voto: limita votes_claimed a 1 per chi aveva riscattato più volte
        # con la vecchia regola da 3/mese. I bonus vengono ridotti proporzionalmente.
        try:
            conn.execute("""
                UPDATE vote_bonus
                SET
                    votes_claimed = 1,
                    image_bonus   = MIN(image_bonus,   2),
                    compose_bonus = MIN(compose_bonus, 1)
                WHERE votes_claimed > 1
            """)
            migrated = conn.execute(
                "SELECT changes()"
            ).fetchone()[0]
            if migrated:
                print(f"[DB] Migrazione bonus voto: {migrated} riga/righe riportate a 1 riscatto/mese")
        except Exception as e:
            print(f"[DB] Migrazione bonus voto saltata: {e}")

        conn.commit()

    print(f"[DB] Database pronto: {os.path.abspath(DB_FILE)}")
