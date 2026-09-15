"""
settings_manager.py — Gestione delle preferenze e impostazioni utente.

Gestisce la configurazione personale di ciascun utente Discord:
- Temperatura del modello Gemini (creatività/precisione da 0.1 a 2.0).
- Prompt di sistema personalizzato (custom prompt).
- Formato proporzionale delle immagini generate (aspect ratio 1:1, 16:9, 9:16, 4:3, 3:4).
- Lingua preferita delle risposte (6 lingue supportate: IT, EN, ES, PT, FR, DE).
"""

from bot_managers.db import get_conn
from bot_managers.strings import t, DEFAULT_LANG

DEFAULT_TEMPERATURE   = 1.0
DEFAULT_CUSTOM_PROMPT = ""
DEFAULT_IMAGE_SIZE    = "1:1"
DEFAULT_LANGUAGE      = "en"

LANGUAGE_OPTIONS = [
    ("it", "🇮🇹 Italiano"),
    ("en", "🇬🇧 English"),
    ("es", "🇪🇸 Español"),
    ("pt", "🇧🇷 Português"),
    ("fr", "🇫🇷 Français"),
    ("de", "🇩🇪 Deutsch"),
]

# Valori validi per la temperatura — le label tradotte vengono da strings.py
TEMPERATURE_VALUES = ["0.1", "0.4", "0.7", "1.0", "1.4", "2.0"]

def get_temperature_options(lang: str = DEFAULT_LANG) -> list[tuple[str, str]]:
    """Ritorna le opzioni temperatura con label tradotte per la lingua richiesta."""
    return [(v, t(f"temp.{v}", lang)) for v in TEMPERATURE_VALUES]

# Alias per retrocompatibilità (usato da check in set_temperature)
TEMPERATURE_OPTIONS = [(v, v) for v in TEMPERATURE_VALUES]

# Valori validi per il formato immagine — le label tradotte vengono da strings.py
IMAGE_SIZE_VALUES = ["1:1", "16:9", "9:16", "4:3", "3:4"]

def get_image_size_options(lang: str = DEFAULT_LANG) -> list[tuple[str, str]]:
    """Ritorna le opzioni formato immagine con label tradotte per la lingua richiesta."""
    return [(v, t(f"size.{v}", lang)) for v in IMAGE_SIZE_VALUES]

# Alias per retrocompatibilità (usato da check in set_image_size)
IMAGE_SIZE_OPTIONS = [(v, v) for v in IMAGE_SIZE_VALUES]

SIZE_HINT = {
    "1:1":  "square 1:1 aspect ratio",
    "16:9": "wide landscape 16:9 aspect ratio",
    "9:16": "tall portrait 9:16 aspect ratio",
    "4:3":  "landscape 4:3 aspect ratio",
    "3:4":  "portrait 3:4 aspect ratio",
}


def _ensure(conn, uid: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO user_settings "
        "(user_id, temperature, custom_prompt, image_size, language) VALUES (?, ?, ?, ?, ?)",
        (uid, DEFAULT_TEMPERATURE, DEFAULT_CUSTOM_PROMPT, DEFAULT_IMAGE_SIZE, DEFAULT_LANGUAGE)
    )


def get_settings(user_id: str) -> dict:
    uid = str(user_id)
    with get_conn() as conn:
        _ensure(conn, uid)
        conn.commit()
        row = conn.execute(
            "SELECT temperature, custom_prompt, image_size, language "
            "FROM user_settings WHERE user_id = ?", (uid,)
        ).fetchone()
    return {
        "temperature":   row["temperature"],
        "custom_prompt": row["custom_prompt"],
        "image_size":    row["image_size"],
        "language":      row["language"] or DEFAULT_LANGUAGE,
    }


def set_temperature(user_id: str, temperature: float) -> None:
    uid = str(user_id)
    temp = max(0.0, min(2.0, float(temperature)))
    with get_conn() as conn:
        _ensure(conn, uid)
        conn.execute(
            "UPDATE user_settings SET temperature = ? WHERE user_id = ?", (temp, uid)
        )
        conn.commit()


def set_custom_prompt(user_id: str, prompt: str) -> None:
    uid = str(user_id)
    with get_conn() as conn:
        _ensure(conn, uid)
        conn.execute(
            "UPDATE user_settings SET custom_prompt = ? WHERE user_id = ?",
            (prompt.strip(), uid)
        )
        conn.commit()


def set_image_size(user_id: str, size: str) -> None:
    uid = str(user_id)
    valid = [v for v, _ in IMAGE_SIZE_OPTIONS]
    if size not in valid:
        raise ValueError(f"Aspect ratio non valido: {size}")
    with get_conn() as conn:
        _ensure(conn, uid)
        conn.execute(
            "UPDATE user_settings SET image_size = ? WHERE user_id = ?", (size, uid)
        )
        conn.commit()


def set_language(user_id: str, language: str) -> None:
    uid = str(user_id)
    valid = [v for v, _ in LANGUAGE_OPTIONS]
    if language not in valid:
        raise ValueError(f"Lingua non valida: {language}")
    with get_conn() as conn:
        _ensure(conn, uid)
        conn.execute(
            "UPDATE user_settings SET language = ? WHERE user_id = ?", (language, uid)
        )
        conn.commit()


def reset_settings(user_id: str) -> None:
    uid = str(user_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_settings SET temperature = ?, custom_prompt = ?, image_size = ?, language = ? "
            "WHERE user_id = ?",
            (DEFAULT_TEMPERATURE, DEFAULT_CUSTOM_PROMPT, DEFAULT_IMAGE_SIZE, DEFAULT_LANGUAGE, uid)
        )
        conn.commit()