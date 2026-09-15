"""
purpleGPT — Your community. Your AI. Your rules.
main.py — File principale del bot.
Sviluppato da jLabs (justmarcolin)

Architettura del Bot:
- Intelligenza Artificiale: Integrata con Google Gemini 3.8 Flash / 3.1 Pro via Vertex AI (Google Gen AI SDK).
- Generazione Immagini: Gemini 3.1 Flash Image con supporto all'edit dell'ultima immagine generata.
- Composizione Musicale AI: Integrata con Lyria 3 via Google Enterprise Agent Platform REST API.
- Sistema IPC Interno: Server HTTP aiohttp su 127.0.0.1:5001 per la comunicazione sicura con la Dashboard Admin Flask.
- Gestione Abbonamenti: Integrazione bidirezionale con Discord Premium App Entitlements e Stripe Payment Links.
- Persistenza & GDPR: Database SQLite in modalità WAL con supporto per export dati ed eliminazione permanente.
"""

import discord
import os
import io
import asyncio
import base64
import time
import json
import aiohttp
from aiohttp import web as aio_web
import uuid
import subprocess
import traceback
import logging
import logging.handlers
import hmac
import re
import tempfile
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv
from discord import File, app_commands
from discord.ext import commands
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.genai import types, Client
from bot_managers import history_manager, tos_manager, settings_manager, quota_manager
from bot_managers.db import init_db, get_conn
from bot_managers.strings import t, get_lang, DEFAULT_LANG


# Configurazione

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
TOKEN         = os.getenv("TOKEN")
PROJECT_ID    = os.getenv("PROJECT_ID")
LOCATION      = os.getenv("LOCATION")
BUG_WEBHOOK_URL = os.getenv("BUG_WEBHOOK_URL")  # Webhook Discord per ricevere i bug report
LOG_FILE           = os.getenv("LOG_FILE", "purplegpt.log")
INTERNAL_PORT      = int(os.getenv("INTERNAL_PORT", "5001"))
INTERNAL_SECRET    = os.getenv("BROADCAST_SECRET", "")
BOT_TIMEZONE       = os.getenv("BOT_TIMEZONE", "Europe/Rome")
CHAT_MODEL         = os.getenv("CHAT_MODEL", "gemini-3.8-flash")
LYRIA_MODEL        = os.getenv("LYRIA_MODEL", "lyria-3-clip-preview")
IMAGE_MODEL        = os.getenv("IMAGE_MODEL", "gemini-3.1-flash-image")
CHAT_IMAGE_MODEL   = os.getenv("CHAT_IMAGE_MODEL", CHAT_MODEL)
CHAT_IMAGE_MODEL_PRO = os.getenv("CHAT_IMAGE_MODEL_PRO", "gemini-3.1-pro-preview")
DISCORD_SKU_STARTER = os.getenv("DISCORD_SKU_STARTER", "").strip()
DISCORD_SKU_PRO     = os.getenv("DISCORD_SKU_PRO", "").strip()
DISCORD_SKU_TO_PLAN = {
    DISCORD_SKU_STARTER: "starter",
    DISCORD_SKU_PRO:     "pro",
}
DISCORD_SKU_TO_PLAN = {sku: plan for sku, plan in DISCORD_SKU_TO_PLAN.items() if sku}
DISCORD_CONFIGURED_SKU_TO_PLAN = dict(DISCORD_SKU_TO_PLAN)
DISCORD_SKU_TYPE_SUBSCRIPTION = 5
DISCORD_SKU_TYPE_SUBSCRIPTION_GROUP = 6
DISCORD_SKU_FLAG_GUILD_SUBSCRIPTION = 1 << 7
DISCORD_SKU_FLAG_USER_SUBSCRIPTION = 1 << 8

if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID e LOCATION sono obbligatori per usare Gemini tramite Vertex AI.")

# Logging

def setup_logging() -> logging.Logger:
    """
    Configura il logging su file rotante + console.
    - File: purplegpt.log, max 5MB, 3 backup
    - Formato: [2026-01-01 12:00:00] LEVEL [modulo] messaggio
    """
    logger = logging.getLogger("purplegpt")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Gestore per il file di log rotante
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Gestore console: mostra solo INFO e livelli superiori
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

log = setup_logging()

# Client Gemini su Vertex AI.
# vertexai=True forza il Google Gen AI SDK a usare il backend Vertex AI
# invece della Gemini Developer API basata su API key.
client = Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

# Disabilita l'Automatic Function Calling (AFC) nelle chiamate generate_content
# per evitare warning e chiamate a tool automatiche non necessarie.
NO_AFC = types.AutomaticFunctionCallingConfig(disable=True)

# Sessione HTTP globale - creata in on_ready, riutilizzata per tutte le richieste
http_session: aiohttp.ClientSession | None = None
internal_server_started = False
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB: evita letture troppo grandi in memoria
ATTACHMENT_TIMEOUT = aiohttp.ClientTimeout(total=20)
LYRIA_TIMEOUT = aiohttp.ClientTimeout(total=180)
LYRIA_POLL_ATTEMPTS = int(os.getenv("LYRIA_POLL_ATTEMPTS", "12"))
LYRIA_POLL_INTERVAL = float(os.getenv("LYRIA_POLL_INTERVAL", "5"))


async def get_session() -> aiohttp.ClientSession:
    """Ritorna la sessione HTTP globale, ricreandola se e chiusa o None."""
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()
    return http_session


async def close_http_session() -> None:
    """Chiude la sessione HTTP globale quando il bot si spegne."""
    global http_session
    if http_session is not None and not http_session.closed:
        await http_session.close()
    http_session = None


def detect_supported_image_mime(data: bytes) -> str | None:
    """Riconosce PNG, JPEG e WEBP dai magic bytes reali del file."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def download_discord_attachment(
    attachment: discord.Attachment,
    supported_mimes: tuple[str, ...],
) -> tuple[bytes, str]:
    """
    Scarica un allegato Discord solo se tipo e dimensione sono accettabili.
    Ritorna (bytes, mime_type). Solleva ValueError con un codice leggibile.
    """
    mime = (attachment.content_type or "").split(";")[0].strip()
    if mime not in supported_mimes:
        raise ValueError("unsupported_type")

    if attachment.size and attachment.size > MAX_ATTACHMENT_BYTES:
        raise ValueError("too_large")

    try:
        data = await attachment.read(use_cached=True)
    except TypeError:
        data = await attachment.read()
    except Exception:
        async with (await get_session()).get(attachment.url, timeout=ATTACHMENT_TIMEOUT) as resp:
            if resp.status != 200:
                raise ValueError("download_failed")
            data = await resp.content.read(MAX_ATTACHMENT_BYTES + 1)

    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("too_large")

    detected_mime = detect_supported_image_mime(data)
    if detected_mime is None or detected_mime not in supported_mimes:
        raise ValueError("invalid_image")

    if mime != detected_mime:
        log.info(f"[attachment] MIME dichiarato {mime}, rilevato {detected_mime}. Uso quello rilevato.")

    return data, detected_mime


def attachment_error_text(error_code: str, lang: str, mime: str | None = None) -> str:
    """Messaggio utente per errori di download allegati."""
    if error_code == "too_large":
        return t("error.file_too_large", lang, mb=MAX_ATTACHMENT_BYTES // (1024 * 1024))
    if error_code == "unsupported_type":
        return t("error.format_not_supported", lang, mime=mime or "unknown")
    if error_code == "invalid_image":
        return t("error.format_not_supported", lang, mime=mime or "invalid image")
    return t("error.generic", lang)


def build_multimodal_content(image_bytes: bytes, mime_type: str, text: str) -> list:
    """Costruisce contenuti multimodali nel formato consigliato dal Google Gen AI SDK."""
    return [
        types.Part.from_text(text=text),
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
    ]


async def sync_discord_sku_mapping() -> None:
    """
    Verifica gli SKU configurati seguendo la regola ufficiale Discord:
    per gli abbonamenti va usato lo SKU type 5, non il type 6 generato come gruppo.
    Se trova un type 6, prova a risolverlo automaticamente verso il type 5 con lo stesso nome.
    """
    global DISCORD_SKU_TO_PLAN

    if not DISCORD_CONFIGURED_SKU_TO_PLAN:
        log.warning("[ENTITLEMENT] Nessuno SKU Discord configurato nel .env.")
        return
    if not TOKEN:
        log.warning("[ENTITLEMENT] TOKEN mancante: impossibile verificare gli SKU Discord.")
        return

    app_id = bot.application_id or (bot.user.id if bot.user else None)
    if not app_id:
        log.warning("[ENTITLEMENT] Application ID non disponibile: salto verifica SKU.")
        return

    session = await get_session()
    url = f"https://discord.com/api/v10/applications/{app_id}/skus"

    try:
        async with session.get(url, headers={"Authorization": f"Bot {TOKEN}"}) as resp:
            raw_body = await resp.text()
            if resp.status != 200:
                log.warning(f"[ENTITLEMENT] Verifica SKU fallita: HTTP {resp.status} - {raw_body[:250]}")
                return
            skus = json.loads(raw_body)
    except Exception as exc:
        log.warning(f"[ENTITLEMENT] Errore durante la verifica SKU: {exc}")
        return

    if not isinstance(skus, list):
        log.warning("[ENTITLEMENT] Risposta SKU non valida: mi aspettavo una lista.")
        return

    sku_by_id = {str(sku.get("id")): sku for sku in skus if sku.get("id")}
    subscription_skus_by_name: dict[str, list[str]] = {}

    for sku in skus:
        sku_id = str(sku.get("id", ""))
        sku_type = sku.get("type")
        sku_name = str(sku.get("name") or "")
        flags = int(sku.get("flags") or 0)

        if sku_type == DISCORD_SKU_TYPE_SUBSCRIPTION:
            subscription_skus_by_name.setdefault(sku_name.casefold(), []).append(sku_id)

        access_kind = "user" if flags & DISCORD_SKU_FLAG_USER_SUBSCRIPTION else "guild" if flags & DISCORD_SKU_FLAG_GUILD_SUBSCRIPTION else "unknown"
        log.info(f"[ENTITLEMENT] SKU trovato: id={sku_id}, type={sku_type}, access={access_kind}, name={sku_name!r}")

    resolved_mapping: dict[str, str] = {}

    for configured_sku_id, plan in DISCORD_CONFIGURED_SKU_TO_PLAN.items():
        sku = sku_by_id.get(configured_sku_id)
        if not sku:
            log.warning(f"[ENTITLEMENT] SKU {configured_sku_id} per piano {plan} non trovato nell'app Discord.")
            resolved_mapping[configured_sku_id] = plan
            continue

        sku_type = sku.get("type")
        sku_name = str(sku.get("name") or "")
        flags = int(sku.get("flags") or 0)

        if flags & DISCORD_SKU_FLAG_GUILD_SUBSCRIPTION:
            log.warning(
                f"[ENTITLEMENT] SKU {configured_sku_id} ({sku_name}) e' una guild subscription. "
                "Il bot oggi assegna piani per utente: usa User Subscription nel Developer Portal."
            )

        if sku_type == DISCORD_SKU_TYPE_SUBSCRIPTION:
            resolved_mapping[configured_sku_id] = plan
            continue

        if sku_type == DISCORD_SKU_TYPE_SUBSCRIPTION_GROUP:
            candidates = subscription_skus_by_name.get(sku_name.casefold(), [])
            if len(candidates) == 1:
                resolved_mapping[candidates[0]] = plan
                log.warning(
                    f"[ENTITLEMENT] SKU {configured_sku_id} per {plan} e' type 6. "
                    f"Uso automaticamente lo SKU subscription type 5: {candidates[0]}."
                )
                continue

            resolved_mapping[configured_sku_id] = plan
            log.warning(
                f"[ENTITLEMENT] SKU {configured_sku_id} per {plan} e' type 6, ma non riesco "
                f"a trovare un unico type 5 con nome {sku_name!r}. Correggi DISCORD_SKU_{plan.upper()} nel .env."
            )
            continue

        resolved_mapping[configured_sku_id] = plan
        log.warning(f"[ENTITLEMENT] SKU {configured_sku_id} per {plan} ha type={sku_type}; Discord richiede type=5 per gli abbonamenti.")

    DISCORD_SKU_TO_PLAN = resolved_mapping


async def sync_active_discord_entitlements() -> None:
    """
    Recupera gli entitlement attivi da Discord e applica i piani gia' acquistati.
    Serve quando un utente si abbona mentre il bot e' offline o prima di una patch.
    """
    if not DISCORD_SKU_TO_PLAN:
        log.warning("[ENTITLEMENT] Nessuno SKU valido configurato: salto sync entitlement attivi.")
        return
    if not TOKEN:
        log.warning("[ENTITLEMENT] TOKEN mancante: impossibile sincronizzare gli entitlement.")
        return

    app_id = bot.application_id or (bot.user.id if bot.user else None)
    if not app_id:
        log.warning("[ENTITLEMENT] Application ID non disponibile: salto sync entitlement attivi.")
        return

    session = await get_session()
    headers = {"Authorization": f"Bot {TOKEN}"}
    sku_ids = ",".join(DISCORD_SKU_TO_PLAN.keys())
    after: str | None = None
    total_seen = 0
    total_applied = 0

    while True:
        params = {
            "sku_ids": sku_ids,
            "exclude_ended": "true",
            "exclude_deleted": "true",
            "limit": "100",
        }
        if after:
            params["after"] = after

        try:
            async with session.get(
                f"https://discord.com/api/v10/applications/{app_id}/entitlements",
                headers=headers,
                params=params,
            ) as resp:
                raw_body = await resp.text()
                if resp.status != 200:
                    log.warning(f"[ENTITLEMENT] Sync entitlement fallita: HTTP {resp.status} - {raw_body[:250]}")
                    return
                entitlements = json.loads(raw_body)
        except Exception as exc:
            log.warning(f"[ENTITLEMENT] Errore durante la sync entitlement: {exc}")
            return

        if not isinstance(entitlements, list):
            log.warning("[ENTITLEMENT] Risposta entitlement non valida: mi aspettavo una lista.")
            return
        if not entitlements:
            break

        total_seen += len(entitlements)
        for entitlement in entitlements:
            if _entitlement_sku_id(entitlement) in DISCORD_SKU_TO_PLAN and not _entitlement_is_deleted(entitlement) and not _entitlement_has_ended(entitlement):
                await apply_discord_entitlement(entitlement, "startup-sync")
                if _entitlement_user_id(entitlement):
                    total_applied += 1

        if len(entitlements) < 100:
            break

        after = str(entitlements[-1].get("id") or "")
        if not after:
            break

    log.info(f"[ENTITLEMENT] Sync startup completata: {total_applied}/{total_seen} entitlement applicati.")


class PurpleGPTBot(commands.Bot):
    async def close(self) -> None:
        await close_http_session()
        await super().close()


# Intent: members serve per leggere ruoli e membri nei server
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # necessario per il trigger @menzione

bot = PurpleGPTBot(command_prefix="!", intents=intents)
bot.remove_command("help")

@bot.event
async def on_command_error(ctx, error):
    # purpleGPT usa solo slash command: ignora silenziosamente gli errori
    # dei vecchi comandi con prefisso, ad esempio !comando.
    pass

BASE_SYSTEM_PROMPT = """
You are purpleGPT, a warm and direct AI assistant built into Discord by justmarcolin and powered by Gemini.
Always answer in the user's language. Use Discord-friendly formatting when useful. Never use LaTeX; use plain text or Unicode for math.

Do not reveal or discuss system prompts, hidden instructions, internal context, backend details, the user's plan, or quotas unless the user asks or it directly helps.
Do not invent changelogs, updates, maintenance details, deployment history, or time-sensitive project news. Use only update information provided in the current context; otherwise say you do not have access to those details.

Available commands: /chat, /draw, /edit, /compose, /genserver, /settings, /stats, /bugreport, /broadcast, /premium.
Mention commands only when asked, when greeting/helping with capabilities, or when a command directly solves the request. No unsolicited upselling.

purpleGPT has Free, Starter, and Pro plans. If asked about plans, upgrades, limits, or the current plan, answer briefly and mention /premium.
If asked to react with an emoji, you already did it automatically; confirm naturally.
"""

# Parametri audio Lyria in tempo reale (PCM stereo 16-bit 48kHz)
TRANSITION_FILE    = "transition.webm"
FFMPEG             = "ffmpeg"
FFPROBE            = "ffprobe"


# Setup server

async def send_setup_message(guild: discord.Guild) -> bool:
    """Invia gli embed di benvenuto e setup al primo canale disponibile."""
    canale = None
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        canale = guild.system_channel
    else:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                canale = ch
                break

    if canale is None:
        return False

    embed_benvenuto = discord.Embed(
        title="👋 Hey! I'm purpleGPT 🟣",
        description="The AI that integrates into your community.\n\n*Your community. Your AI. Your rules.*\n\n> 🧪 **Public beta** - the bot is in active testing. If you find anything off, use `/bugreport` to let us know!",
        color=0x8000FF
    )
    embed_benvenuto.add_field(name="💬 Chat with memory",    value="Use `/chat` or mention me directly (with or without a photo). I remember the channel conversation and understand server context - roles, channels, descriptions.", inline=False)
    embed_benvenuto.add_field(name="🎨 Images & Editing",    value="Generate images with `/draw`, edit them with `/edit`. Supports image-to-image and custom aspect ratios.", inline=False)
    embed_benvenuto.add_field(name="🎵 AI Music",            value="Compose original tracks with `/compose`. Choose style, BPM, duration and optionally generate a video with cover art.", inline=False)
    embed_benvenuto.add_field(name="⚙️ Customizable",        value="Every user can configure temperature, image format, language and a custom prompt with `/settings`.", inline=False)
    embed_benvenuto.add_field(name="🔒 Built-in privacy",    value="You're in control of your data. Export everything with `/export_data` or delete it all with `/delete_user_data`.", inline=False)
    embed_benvenuto.set_footer(text="purpleGPT - jLabs - by justmarcolin - /help for all commands")

    embed_setup = discord.Embed(
        title="🔧 Setup - what to do now",
        description="One quick thing before you get started:",
        color=0x5b21b6
    )

    bot_top_role = guild.me.top_role
    ruoli_sopra  = [r for r in guild.roles if r.position > bot_top_role.position and r.name != "@everyone" and not r.managed]

    if ruoli_sopra:
        nomi = ", ".join(f"@{r.name}" for r in ruoli_sopra[:5])
        embed_setup.add_field(
            name="⚠️ Role position - action needed",
            value=(
                f"**@{bot_top_role.name}** should be the first role in the list "
                f"so I can correctly read server roles and member permissions.\n\n"
                f"Roles currently above me: {nomi}\n\n"
                f"**Fix:** Server Settings -> Roles -> drag **@{bot_top_role.name}** to the top."
            ),
            inline=False
        )
    else:
        embed_setup.add_field(
            name="✅ Role position",
            value=f"**@{bot_top_role.name}** is already first in the list. Nothing to do here.",
            inline=False
        )

    embed_setup.add_field(
        name="📣 Broadcast notifications",
        value="If you want me to send updates and announcements to a specific channel, make sure I have permission to write there - some locked channels may need an explicit override for my role.",
        inline=False
    )
    embed_setup.add_field(
        name="💎 Premium plans available",
        value="Unlock more images, music and /genserver uses. **Starter includes a 7-day free trial** - cancel anytime. Use `/premium` to see plans.",
        inline=False
    )
    embed_setup.add_field(name="📖 Terms of service", value="Every user will see the ToS on first use. Full text: https://example.com/purplegpt-tos", inline=False)
    embed_setup.set_footer(text="Use /help at any time to review all available commands.")

    await canale.send(embeds=[embed_benvenuto, embed_setup])
    return True


def _is_setup_done(guild_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT setup_done FROM guild_setup WHERE guild_id = ?", (str(guild_id),)).fetchone()
    return bool(row and row["setup_done"])


def _mark_setup_done(guild_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO guild_setup (guild_id, setup_done, setup_at) VALUES (?, 1, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET setup_done = 1, setup_at = excluded.setup_at",
            (str(guild_id), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()



# Server HTTP interno (IPC dashboard <-> bot)
# Ascolta solo su 127.0.0.1 - non esposto su internet.
# La dashboard lo usa per inviare broadcast e ottenere la lista server.

_last_broadcast_time: float = 0.0
BROADCAST_MIN_INTERVAL = 10  # secondi minimi tra broadcast consecutivi


def _verify_internal_token(request: aio_web.Request) -> bool:
    """Verifica il token Bearer nelle richieste interne dalla dashboard."""
    if not INTERNAL_SECRET:
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[len("Bearer "):]
    return hmac.compare_digest(token.encode(), INTERNAL_SECRET.encode())


async def _handle_guilds(request: aio_web.Request) -> aio_web.Response:
    """GET /internal/guilds - ritorna la lista dei server in cui e presente il bot."""
    if not _verify_internal_token(request):
        return aio_web.json_response({"error": "Unauthorized"}, status=401)
    guilds = [
        {"id": str(g.id), "name": g.name, "member_count": g.member_count}
        for g in sorted(bot.guilds, key=lambda g: g.name.lower())
    ]
    return aio_web.json_response({"guilds": guilds})


async def _handle_broadcast(request: aio_web.Request) -> aio_web.Response:
    """POST /internal/broadcast - invia un broadcast ai server specificati."""
    global _last_broadcast_time
    if not _verify_internal_token(request):
        return aio_web.json_response({"error": "Unauthorized"}, status=401)

    elapsed = time.monotonic() - _last_broadcast_time
    if elapsed < BROADCAST_MIN_INTERVAL:
        wait = int(BROADCAST_MIN_INTERVAL - elapsed) + 1
        return aio_web.json_response(
            {"error": f"Troppo presto. Attendi {wait}s prima del prossimo broadcast."},
            status=429
        )

    try:
        data = await request.json()
    except Exception:
        return aio_web.json_response({"error": "JSON non valido"}, status=400)

    btype        = str(data.get("type", "avviso"))
    title        = str(data.get("title", "")).strip()[:100]
    body         = str(data.get("body", "")).strip()[:1500]
    version      = str(data.get("version", "")).strip()[:20]
    target_guild = str(data.get("target_guild_id", "")).strip()  # "" = tutti

    # Valida che target_guild sia un ID numerico Discord o stringa vuota
    if target_guild and not target_guild.isdigit():
        return aio_web.json_response({"error": "target_guild_id non valido"}, status=400)

    if btype not in ("avviso", "changelog"):
        btype = "avviso"
    if not title or not body:
        return aio_web.json_response({"error": "title e body obbligatori"}, status=400)

    # Costruisci embed
    if btype == "changelog":
        color       = 0x34d399
        emoji       = "📋"
        footer_text = f"purpleGPT - Changelog{' v' + version if version else ''}"
    else:
        color       = 0xfbbf24
        emoji       = "⚠️"
        footer_text = "purpleGPT - Notice"

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=body,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=footer_text)

    # Determina destinatari
    if target_guild:
        guilds_to_notify = [g for g in bot.guilds if str(g.id) == target_guild]
    else:
        guilds_to_notify = list(bot.guilds)

    reached = 0
    for guild in guilds_to_notify:
        # Controlla impostazioni broadcast del server
        bc_settings = get_broadcast_settings(guild.id)
        if not bc_settings["enabled"]:
            log.info(f"[BROADCAST] {guild.name} ha le notifiche disattivate: salto il server")
            continue

        # Usa il canale configurato, poi system_channel, poi primo canale scrivibile
        channel = None
        if bc_settings["channel_id"]:
            channel = guild.get_channel(int(bc_settings["channel_id"]))
            if channel and not channel.permissions_for(guild.me).send_messages:
                channel = None  # canale configurato ma bot senza permessi
        if channel is None:
            channel = guild.system_channel
            if channel and not channel.permissions_for(guild.me).send_messages:
                channel = None
        if channel is None:
            channel = next(
                (ch for ch in guild.text_channels
                 if ch.permissions_for(guild.me).send_messages),
                None
            )

        if channel:
            try:
                await channel.send(embed=embed)
                reached += 1
            except Exception as e:
                log.warning(f"[BROADCAST] Errore durante l'invio a {guild.name}: {e}")

    _last_broadcast_time = time.monotonic()
    log.info(f"[BROADCAST] Inviato a {reached}/{len(guilds_to_notify)} server - tipo={btype} titolo={title!r}")
    return aio_web.json_response({"ok": True, "servers_reached": reached})


async def start_internal_server() -> None:
    """Avvia il server HTTP interno su 127.0.0.1:INTERNAL_PORT."""
    global internal_server_started
    if internal_server_started:
        return
    app_internal = aio_web.Application()
    app_internal.router.add_get("/internal/guilds",    _handle_guilds)
    app_internal.router.add_post("/internal/broadcast", _handle_broadcast)
    runner = aio_web.AppRunner(app_internal)
    await runner.setup()
    site = aio_web.TCPSite(runner, "127.0.0.1", INTERNAL_PORT)
    await site.start()
    internal_server_started = True
    log.info(f"[INTERNO] Server IPC avviato su 127.0.0.1:{INTERNAL_PORT}")


# Discord Premium App entitlements

def _entitlement_value(entitlement, name: str):
    if isinstance(entitlement, dict):
        return entitlement.get(name)
    return getattr(entitlement, name, None)


def _entitlement_sku_id(entitlement) -> str:
    value = _entitlement_value(entitlement, "sku_id")
    return str(value) if value is not None else ""


def _entitlement_user_id(entitlement) -> str | None:
    value = _entitlement_value(entitlement, "user_id")
    if value is None:
        user = _entitlement_value(entitlement, "user")
        value = getattr(user, "id", None) if user is not None else None
    return str(value) if value is not None else None


def _entitlement_guild_id(entitlement) -> str | None:
    value = _entitlement_value(entitlement, "guild_id")
    if value is None:
        guild = _entitlement_value(entitlement, "guild")
        value = getattr(guild, "id", None) if guild is not None else None
    return str(value) if value is not None else None


def _entitlement_expires_at(entitlement) -> str | None:
    value = _entitlement_value(entitlement, "ends_at")
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _entitlement_is_deleted(entitlement) -> bool:
    return bool(_entitlement_value(entitlement, "deleted"))


def _entitlement_has_ended(entitlement) -> bool:
    value = _entitlement_value(entitlement, "ends_at")
    if value is None:
        return False
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value <= datetime.now(timezone.utc)
    except Exception:
        return False


async def apply_discord_entitlement(entitlement, source: str) -> None:
    sku_id = _entitlement_sku_id(entitlement)
    plan   = DISCORD_SKU_TO_PLAN.get(sku_id)
    uid    = _entitlement_user_id(entitlement)
    guild_id = _entitlement_guild_id(entitlement)

    if not plan:
        log.info(f"[ENTITLEMENT] SKU ignorato: {sku_id or 'mancante'}")
        return
    if not uid:
        if guild_id:
            log.warning(
                f"[ENTITLEMENT] {source}: entitlement guild-level per guild {guild_id}, SKU {sku_id}. "
                "Il grant automatico attuale supporta solo abbonamenti utente."
            )
        else:
            log.warning(f"[ENTITLEMENT] {source}: user_id mancante per SKU {sku_id}")
        return

    if _entitlement_is_deleted(entitlement) or _entitlement_has_ended(entitlement):
        quota_manager.revoke_plan(uid)
        log.info(f"[ENTITLEMENT] {source}: entitlement eliminato, piano revocato a {uid}")
        return

    expires_at = _entitlement_expires_at(entitlement)
    quota_manager.grant_plan(uid, plan, expires_at, is_trial=False)
    log.info(f"[ENTITLEMENT] {source}: piano {plan} attivato per {uid} (sku={sku_id}, expires={expires_at or 'attivo'})")


async def revoke_discord_entitlement(entitlement, source: str) -> None:
    sku_id = _entitlement_sku_id(entitlement)
    plan   = DISCORD_SKU_TO_PLAN.get(sku_id)
    uid    = _entitlement_user_id(entitlement)

    if not plan or not uid:
        return

    quota_manager.revoke_plan(uid)
    log.info(f"[ENTITLEMENT] {source}: piano {plan} revocato per {uid} (sku={sku_id})")


# Eventi

@bot.event
async def on_ready():
    init_db()
    await get_session()

    await start_internal_server()
    synced = await bot.tree.sync()
    await sync_discord_sku_mapping()
    await sync_active_discord_entitlements()
    log.info(f"[SYNC] {len(synced)} comandi registrati - connesso a {len(bot.guilds)} server.")
    log.info(f"[ENTITLEMENT] SKU configurati: {DISCORD_SKU_TO_PLAN or 'nessuno'}")
    await bot.change_presence(activity=discord.CustomActivity(name="Mention me to start chatting 💬"))

    # Riconcilia lo stato dei server in DB con i server attuali connessi a Discord
    # (aggiorna setup_done=0 per i server che hanno rimosso il bot mentre era offline)
    active_guild_ids = [str(g.id) for g in bot.guilds]
    try:
        with get_conn() as conn:
            if active_guild_ids:
                placeholders = ",".join("?" for _ in active_guild_ids)
                conn.execute(
                    f"UPDATE guild_setup SET setup_done = 0 WHERE setup_done = 1 AND guild_id NOT IN ({placeholders})",
                    active_guild_ids
                )
            else:
                conn.execute("UPDATE guild_setup SET setup_done = 0 WHERE setup_done = 1")
            conn.commit()
        log.info(f"[SYNC] Server attivi verificati e riconciliati in DB: {len(bot.guilds)}")
    except Exception as e:
        log.error(f"[SYNC] Errore durante la riconciliazione server in DB: {e}")

    # Invia setup ai server aggiunti mentre il bot era offline
    for guild in bot.guilds:
        if not _is_setup_done(guild.id):
            log.info(f"[SETUP] Server ancora da configurare: {guild.name}")
            try:
                if await send_setup_message(guild):
                    _mark_setup_done(guild.id)
                    log.info(f"[SETUP] ✅ {guild.name}")
                else:
                    log.warning(f"[SETUP] Nessun canale scrivibile trovato in {guild.name}")
            except Exception as e:
                log.error(f"[SETUP] {guild.name}: {e}")


@bot.event
async def on_entitlement_create(entitlement):
    await apply_discord_entitlement(entitlement, "create")


@bot.event
async def on_entitlement_update(entitlement):
    if _entitlement_is_deleted(entitlement) or _entitlement_has_ended(entitlement):
        await revoke_discord_entitlement(entitlement, "update")
    else:
        await apply_discord_entitlement(entitlement, "update")


@bot.event
async def on_entitlement_delete(entitlement):
    await revoke_discord_entitlement(entitlement, "delete")


@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"[INGRESSO] {guild.name} (ID: {guild.id}, membri: {guild.member_count})")
    try:
        if await send_setup_message(guild):
            _mark_setup_done(guild.id)
    except Exception as e:
        log.error(f"[SETUP] Errore {guild.name}: {e}")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Triggered quando il bot viene rimosso da un server (kick, ban o leave manuale)."""
    log.info(f"[USCITA] Rimosso da: {guild.name} (ID: {guild.id})")
    try:
        with get_conn() as conn:
            # Marca il server come non piu attivo
            conn.execute(
                "UPDATE guild_setup SET setup_done = 0 WHERE guild_id = ?",
                (str(guild.id),)
            )
            # Rimuove il server prompt - non ha piu senso tenerlo
            conn.execute(
                "DELETE FROM server_settings WHERE guild_id = ?",
                (str(guild.id),)
            )
            conn.commit()
        log.info(f"[USCITA] Dati server rimossi: {guild.name}")
    except Exception as e:
        log.error(f"[USCITA] Errore durante la pulizia dati di {guild.name}: {e}")

@bot.event
async def on_message(message: discord.Message):
    """Trigger alternativo a /chat: tagga il bot per una risposta rapida. Supporta immagini allegate."""
    # Ignora messaggi del bot stesso e messaggi senza menzione diretta
    if message.author.bot:
        return
    if bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    uid        = str(message.author.id)
    channel_id = message.channel.id

    # Rimuovi la menzione dal testo
    prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    # Controlla allegati immagine
    immagine_allegata = None
    SUPPORTED_IMG = ("image/png", "image/jpeg", "image/webp")
    for att in message.attachments:
        if att.content_type and att.content_type.split(";")[0].strip() in SUPPORTED_IMG:
            immagine_allegata = att
            break

    # Se non c'e testo ne immagine, ignora
    if not prompt and immagine_allegata is None:
        user_cfg_hello = settings_manager.get_settings(uid)
        await message.reply(t("mention.hello", get_lang(uid, user_cfg_hello)))
        return
    if not prompt and immagine_allegata:
        prompt = "Analyze this image."

    # Controllo accettazione ToS
    user_cfg     = settings_manager.get_settings(uid)
    lang         = get_lang(uid, user_cfg)

    if not tos_manager.has_accepted(uid):
        tos_manager.mark_accepted(uid, message.author.name)
        await message.reply(t("tos.first_use", lang))
        return

    # Cooldown (stesso gruppo "chat")
    cd_ok, remaining = quota_manager.check_cooldown(uid, "chat")
    if not cd_ok:
        await message.reply(t("cooldown.message", lang, remaining=remaining, command="/chat"))
        return

    ok_q, used, limit = quota_manager.check_and_increment(uid, "chat")
    if not ok_q:
        msg = t("quota.exceeded", lang, limit=limit, command="/chat")
        if quota_manager.get_plan(uid) == "free":
            msg += "\n\n" + t("quota.hint.upgrade", lang)
        await message.reply(msg)
        return

    quota_manager.set_cooldown(uid, "chat")

    # Costruisci system prompt (sempre Flash, no Pro via menzione)
    extra_prompt = user_cfg["custom_prompt"]
    temperature  = user_cfg["temperature"]

    system_prompt = build_system_prompt(
        username=message.author.name,
        user_id=uid,
        extra_prompt=extra_prompt,
        guild=message.guild,
        channel=message.channel,
        guild_id=message.guild.id if message.guild else None,
        is_dm=(message.guild is None),
    )

    # Cronologia del canale
    history_data  = history_manager.get_context(channel_id)
    context_lines = []
    for m in history_data:
        prefix = m.get("username", "User") if m["role"] == "user" else "purpleGPT"
        context_lines.append(f"{prefix}: {m['content']}")
    context_lines.append(f"{message.author.name}: {prompt}")

    # Costruisce il contenuto: multimodale se c'e un'immagine, solo testo altrimenti
    if immagine_allegata:
        try:
            img_bytes, mime = await download_discord_attachment(immagine_allegata, SUPPORTED_IMG)
        except ValueError as exc:
            quota_manager.decrement_usage(uid, "chat")
            await message.reply(attachment_error_text(str(exc), lang, immagine_allegata.content_type))
            return
        testo_ctx = system_prompt + "\n\nContext:\n" + "\n".join(context_lines[:-1]) + f"\n\n{message.author.name}: {prompt}"
        contents = build_multimodal_content(img_bytes, mime, testo_ctx)
    else:
        contents = system_prompt + "\n\n" + "\n".join(context_lines)

    async with message.channel.typing():
        try:
            risposta = await asyncio.to_thread(
                client.models.generate_content,
                model=CHAT_IMAGE_MODEL if immagine_allegata else CHAT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    automatic_function_calling=NO_AFC,
                )
            )
            testo = (risposta.text or "").strip()

            if not testo:
                quota_manager.decrement_usage(uid, "chat")
                await message.reply(t("mention.error_no_response", lang))
                return

            history_manager.add_message(
                channel_id, "user",
                prompt + (" [+ immagine allegata]" if immagine_allegata else ""),
                user_id=uid, username=message.author.name
            )
            history_manager.add_message(channel_id, "ai", testo)

            LIMIT = 2000
            chunks = [testo[i:i + LIMIT] for i in range(0, len(testo), LIMIT)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.reply(chunk)
                else:
                    await message.channel.send(chunk)

            # Reazione AI al messaggio originale dell'utente - lanciata in background
            asyncio.create_task(apply_reaction(message, prompt, testo))

        except Exception as e:
            quota_manager.decrement_usage(uid, "chat")
            log.error(f"[MENZIONE] {e}", exc_info=True)
            await message.reply(t("error.generic", lang))

    await bot.process_commands(message)




# Utility: rilevamento richiesta reazione

def _is_reaction_request(prompt: str) -> bool:
    """
    Rileva se l'utente sta chiedendo esplicitamente al bot di reagire a qualcosa.
    Controlla parole chiave multilingua nel prompt.
    """
    prompt_lower = prompt.lower()
    keywords = [
        # italiano
        "reagisci", "metti una reazione", "aggiungi una reazione", "reagire",
        "metti un'emoji", "aggiungi un'emoji",
        # inglese
        "react", "add a reaction", "put a reaction", "add an emoji",
        # spagnolo
        "reacciona", "pon una reaccion", "anade una reaccion",
        # portoghese
        "reage", "reaja", "adiciona uma reacaoo", "poe uma reacaoo",
        # francese
        "reagis", "ajoute une reaction", "mets une reaction",
        # tedesco
        "reagiere", "fuge eine reaktion hinzu", "eine reaktion hinzufugen",
    ]
    return any(kw in prompt_lower for kw in keywords)


# Utility: reazione AI

async def get_reaction_emoji(prompt: str, risposta: str) -> str | None:
    """
    Chiede a Gemini un'emoji appropriata da aggiungere come reaction Discord.
    Ritorna un emoji Unicode oppure None se non ha senso reagire.
    La chiamata e leggera e non blocca la risposta principale.
    """
    mini_prompt = (
        "Look at this exchange between a user and an AI chatbot:\n\n"
        f"User: {prompt[:300]}\n"
        f"Bot: {risposta[:300]}\n\n"
        "Reply with ONE Unicode emoji that best represents the emotional reaction "
        "to the user's message, not to the bot response. "
        "If the message is neutral, technical, a dry question, or has no clear emotional tone, "
        "reply exactly with: NONE\n"
        "Reply only with the emoji or with NONE, nothing else."
    )
    try:
        result = await asyncio.to_thread(
            client.models.generate_content,
            model=CHAT_MODEL,
            contents=mini_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                automatic_function_calling=NO_AFC,
            )
        )
        raw = (result.text or "").strip()
        if not raw or raw.upper() in ("NONE", "NESSUNA"):
            return None
        # Valida che sia effettivamente un emoji e non testo ASCII
        # Un emoji Unicode ha codepoint > 127; escludiamo stringhe con lettere/cifre ASCII
        if any(c.isascii() and (c.isalpha() or c.isdigit()) for c in raw):
            return None
        # Prendi solo il primo "cluster" grafico (max 10 char per emoji composte)
        emoji = raw[:10].strip()
        return emoji if emoji else None
    except Exception:
        return None


async def apply_reaction(target_message: discord.Message, prompt: str, risposta: str) -> None:
    """
    Ottiene l'emoji da Gemini e la aggiunge come reaction al messaggio target.
    Se l'utente ha chiesto esplicitamente una reaction, la forza sempre.
    """
    explicit = _is_reaction_request(prompt)

    if explicit:
        # Richiesta esplicita - chiedi a Gemini quale emoji usare basandosi sul contesto
        forced_prompt = (
            f"The user asked the bot to react. This is the request: \"{prompt[:200]}\"\n"
            f"The bot replied: \"{risposta[:200]}\"\n\n"
            "Choose ONE Discord emoji suitable as a reaction. "
            "Reply only with the emoji, nothing else."
        )
        try:
            result = await asyncio.to_thread(
                client.models.generate_content,
                model=CHAT_MODEL,
                contents=forced_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    automatic_function_calling=NO_AFC,
                )
            )
            raw = (result.text or "").strip()
            if raw and not any(c.isascii() and (c.isalpha() or c.isdigit()) for c in raw):
                emoji = raw[:10].strip()
            else:
                emoji = "👍"  # risposta di ripiego se Gemini risponde con testo
        except Exception:
            emoji = "👍"
    else:
        emoji = await get_reaction_emoji(prompt, risposta)

    if emoji:
        try:
            await target_message.add_reaction(emoji)
        except discord.HTTPException:
            pass  # emoji non valida o permessi mancanti - ignora silenziosamente



# Utility: costruzione del system prompt

def build_current_time_context() -> str:
    """
    Costruisce il contesto temporale da dare al modello.
    I tag <t:...> vengono renderizzati da Discord nella timezone di chi legge.
    """
    now_utc = datetime.now(timezone.utc)
    unix_ts = int(now_utc.timestamp())

    try:
        local_tz = ZoneInfo(BOT_TIMEZONE)
    except ZoneInfoNotFoundError:
        local_tz = timezone.utc

    now_local = now_utc.astimezone(local_tz)
    local_tz_name = getattr(local_tz, "key", "UTC")

    return (
        "Current date/time context:\n"
        f"- Current UTC datetime: {now_utc.isoformat()}\n"
        f"- Current configured local datetime ({local_tz_name}): {now_local.isoformat()}\n"
        f"- Current Unix timestamp: {unix_ts}\n"
        f"- Discord localized timestamp: <t:{unix_ts}:F>\n"
        "If the user asks what day or time it is, use this context. "
        "When useful in Discord messages, you may include Discord timestamp tags "
        "like <t:UNIX:F> or <t:UNIX:R>; Discord renders them in each user's local timezone."
    )


def build_user_activity_context(user_id: str | None) -> str:
    """Riassume le ultime 5 richieste creative dell'utente per il modello chat."""
    if not user_id:
        return ""

    activities = history_manager.get_recent_user_activities(user_id, limit=5)
    if not activities:
        return ""

    lines = [
        "Recent creative requests by this user:",
        "Use this only when relevant. Do not invent missing requests.",
    ]
    for item in activities:
        command = item.get("command", "unknown")
        status = item.get("status", "success")
        prompt = item.get("prompt", "")
        timestamp = item.get("timestamp", "")
        lines.append(f"- {command} ({status}) at {timestamp}: {prompt}")
    return "\n".join(lines)


def build_user_quota_context(user_id: str | None) -> str:
    """Espone al modello chat lo stato dei limiti dei comandi non-chat."""
    if not user_id:
        return ""

    plan = quota_manager.get_plan(user_id)
    rows = []
    for label, command_group, period in [
        ("/draw and /edit", "image", "daily"),
        ("/compose", "compose", "daily"),
        ("/genserver", "genserver", "monthly"),
        ("/chat Pro model", "chat_pro", "monthly"),
    ]:
        used = quota_manager.get_usage(user_id, command_group)
        limit = quota_manager._get_limit(plan, command_group, user_id)
        if limit == -1:
            rows.append(f"- {label}: used {used}, limit unlimited, period {period}, exhausted: no")
            continue
        remaining = max(0, limit - used)
        exhausted = "yes" if remaining <= 0 else "no"
        rows.append(
            f"- {label}: used {used}/{limit}, remaining {remaining}, period {period}, exhausted: {exhausted}"
        )

    return (
        "User quota context:\n"
        "Use this only when the user asks about availability, limits, or related commands.\n"
        + "\n".join(rows)
    )


def build_system_prompt(
    username: str,
    user_id: str | None = None,
    extra_prompt: str = "",
    guild=None,
    channel=None,
    guild_id=None,
    is_dm: bool = False,
) -> str:
    """
    Costruisce il system prompt completo per /chat e la menzione.
    Centralizza la logica condivisa tra i due handler.
    """
    current_plan = quota_manager.get_plan(user_id) if user_id else "free"
    activity_context = build_user_activity_context(user_id)
    quota_context = build_user_quota_context(user_id)
    prompt = (
        BASE_SYSTEM_PROMPT
        + "\n"
        + build_current_time_context()
        + "\n"
        + f"\nThe user's name is {username}.\n"
        + f"User {username} has {current_plan} plan.\n"
        + (f"\n{quota_context}\n" if quota_context else "")
        + (f"\n{activity_context}\n" if activity_context else "")
        + (f"\nAdditional user instructions:\n{extra_prompt}\n" if extra_prompt else "")
    )

    if is_dm or guild is None:
        prompt += "\nYou are chatting privately with the user. Behave like a general personal assistant.\n"
    else:
        prompt += "\nYou are integrated into a Discord community. Use server context to give relevant answers.\n"
        ctx_lines = [f"Server: {guild.name}"]
        if guild.description:
            ctx_lines.append(f"Description: {guild.description}")
        if channel:
            ctx_lines.append(f"Channel: #{channel.name}")
            if hasattr(channel, "topic") and channel.topic:
                ctx_lines.append(f"Topic: {channel.topic}")
        prompt += "\n".join(ctx_lines) + "\n"

        srv_prompt = get_server_prompt(guild_id or guild.id)
        if srv_prompt:
            prompt += f"\nServer instructions:\n{srv_prompt}\n"

    return prompt


# Utility: ToS

async def check_tos(interaction: discord.Interaction, lang: str = DEFAULT_LANG) -> bool:
    """Ritorna True se l'utente ha gia accettato i ToS, altrimenti li mostra e ritorna False."""
    uid = str(interaction.user.id)
    if not tos_manager.has_accepted(uid):
        tos_manager.mark_accepted(uid, interaction.user.name)
        await interaction.response.send_message(t("tos.first_use", lang), ephemeral=True)
        return False
    return True


# Utility: contesto server

def build_server_context(interaction: discord.Interaction) -> str:
    """Costruisce una stringa di contesto del server da iniettare nel system prompt."""
    guild = interaction.guild
    if guild is None:
        return ""

    lines = ["=== SERVER CONTEXT ===", f"Server name: {guild.name}"]

    if guild.description:
        lines.append(f"Description: {guild.description}")

    channel = interaction.channel
    if channel:
        lines.append(f"Current channel: #{channel.name}")
        if hasattr(channel, "topic") and channel.topic:
            lines.append(f"Channel topic: {channel.topic}")

    # Canali testuali visibili al bot
    canali = [
        f"  - #{ch.name}" + (f": {ch.topic}" if ch.topic else "")
        for ch in guild.text_channels
        if ch.permissions_for(guild.me).view_channel
    ]
    if canali:
        lines.append("Channels:")
        lines.extend(canali[:20])
        if len(canali) > 20:
            lines.append(f"  ... and {len(canali) - 20} more")

    # Ruoli del server (escludi @everyone e ruoli managed dei bot)
    ruoli = sorted(
        [r for r in guild.roles if r.name != "@everyone" and not r.managed],
        key=lambda r: r.position, reverse=True
    )
    if ruoli:
        lines.append("Roles, highest first:")
        for r in ruoli[:20]:
            n = len(r.members)
            lines.append(f"  - @{r.name} ({n} {'member' if n == 1 else 'members'})")
        if len(ruoli) > 20:
            lines.append(f"  ... and {len(ruoli) - 20} more")

    # Ruoli dell'utente che sta usando il comando
    member = guild.get_member(interaction.user.id)
    if member:
        ruoli_utente = [r.name for r in member.roles if r.name != "@everyone"]
        if ruoli_utente:
            lines.append(f"{interaction.user.name}'s roles: {', '.join(ruoli_utente)}")
        else:
            lines.append(f"{interaction.user.name} has no special roles.")

    if guild.member_count:
        lines.append(f"Total members: {guild.member_count}")

    lines.append("=== END SERVER CONTEXT ===")
    return "\n".join(lines)


def build_image_context(interaction: discord.Interaction) -> str:
    """
    Contesto per la generazione immagine quando contesto=True.
    Include: nome server, server prompt (se impostato), ultimi 3 messaggi utente del canale.
    """
    parts = []

    if interaction.guild:
        parts.append(f"Discord server name: {interaction.guild.name}")

    # Server prompt impostato dall'admin con /server_prompt (non il system prompt base)
    srv_prompt = get_server_prompt(interaction.guild_id) if interaction.guild_id else ""
    if srv_prompt:
        parts.append(f"Server instructions: {srv_prompt}")

    # Ultimi 3 messaggi utente del canale - orientano il tema visivo
    history_data = history_manager.get_context(interaction.channel_id)
    ultimi = [m["content"] for m in history_data if m["role"] == "user"][-3:]
    if ultimi:
        parts.append("Recent conversation: " + " / ".join(ultimi))

    return ". ".join(parts)


# Utility: aggiornamento progresso

async def progress_updater(
    interaction: discord.Interaction,
    messages: list[str],
    interval: float = 4.0
) -> None:
    """
    Task asincrono che aggiorna il messaggio di risposta ciclando tra i testi
    forniti ogni `interval` secondi. Va cancellato quando la generazione finisce.
    """
    for msg in messages:
        await asyncio.sleep(interval)
        try:
            await interaction.edit_original_response(content=msg)
        except Exception:
            return  # interazione scaduta o gia completata - stop silenzioso


async def check_rate_and_quota(
    interaction: discord.Interaction,
    command_group: str,
    has_quota: bool = True,
    lang: str = DEFAULT_LANG
) -> bool:
    """
    Controlla cooldown e quota giornaliera in sequenza.
    Se has_quota=True, incrementa atomicamente il contatore.
    Ritorna True se l'utente puo procedere.
    """
    uid = str(interaction.user.id)
    group_label = {"chat": "/chat", "image": "/draw e /edit", "compose": "/compose"}.get(command_group, command_group)

    cd_ok, remaining = quota_manager.check_cooldown(uid, command_group)
    if not cd_ok:
        await interaction.response.send_message(
            t("cooldown.message", lang, remaining=remaining, command=group_label), ephemeral=True
        )
        return False

    if has_quota:
        ok, used, limit = quota_manager.check_and_increment(uid, command_group)
        if not ok:
            msg = t("quota.exceeded", lang, limit=limit, command=group_label)
            if command_group == "image" and quota_manager.get_plan(uid) == "free":
                bonus_img, _ = quota_manager.get_vote_bonus(uid)
                if bonus_img <= 0:
                    msg += "\n\n" + t("quota.secret_vote_tip", lang)
            # Suggerisce il passaggio di piano solo agli utenti free
            if quota_manager.get_plan(uid) == "free":
                msg += "\n\n" + t("quota.hint.upgrade", lang)
            await interaction.response.send_message(msg, ephemeral=True)
            return False

    quota_manager.set_cooldown(uid, command_group)
    return True


# /chat

@bot.tree.command(name="chat", description="Chat with purpleGPT AI - supports images and Pro model")
@app_commands.describe(
    prompt="Your message",
    image="Image to analyse (optional)",
    pro="Use the advanced Pro model (Pro plan only)",
)
async def chat(
    interaction: discord.Interaction,
    prompt: str,
    image: discord.Attachment | None = None,
    pro: bool = False,
):
    uid        = str(interaction.user.id)
    user_cfg   = settings_manager.get_settings(uid)
    lang         = get_lang(uid, user_cfg)
    if not await check_tos(interaction, lang):
        return
    if not await check_rate_and_quota(interaction, "chat", has_quota=True, lang=lang):
        return

    await interaction.response.defer(thinking=True)
    await interaction.edit_original_response(content=t("chat.progress.0", lang))
    _progress_task = asyncio.create_task(progress_updater(
        interaction,
        [t("chat.progress.1", lang), t("chat.progress.2", lang)],
        interval=5.0
    ))

    channel_id = interaction.channel_id
    temperature  = user_cfg["temperature"]
    extra_prompt = user_cfg["custom_prompt"]

    # Selezione modello: Pro disponibile solo per utenti del piano pro che lo richiedono.
    # Gli utenti non-pro cadono silenziosamente su Flash senza messaggi invasivi.
    avviso_pro = ""
    chat_model = CHAT_MODEL
    used_pro_model = False

    if pro:
        if quota_manager.is_pro(uid):
            # Controlla la quota mensile del modello Pro
            ok_pro, used_pro, limit_pro = quota_manager.check_and_increment(uid, "chat_pro")
            if ok_pro:
                chat_model = quota_manager.PLANS["pro"]["chat_model_pro"]
                # La quota Pro e stata prenotata; la quota Flash non si applica alle chiamate Pro
                used_pro_model = True
            else:
                avviso_pro = t("quota.chat_pro.exceeded", lang, limit=limit_pro)
        else:
            avviso_pro = t("quota.chat_pro.not_available", lang, price=quota_manager.PLAN_PRICES["pro"])

    # System prompt con contesto server o DM
    # build_server_context gestisce i dettagli dei canali visibili; build_system_prompt
    # gestisce il resto (username, extra_prompt, srv_prompt, DM vs server)
    system_prompt = build_system_prompt(
        username=interaction.user.name,
        user_id=uid,
        extra_prompt=extra_prompt,
        guild=interaction.guild,
        channel=interaction.channel,
        guild_id=interaction.guild_id,
        is_dm=(interaction.guild is None),
    )
    # Aggiungi contesto canali visibili (solo in server)
    if interaction.guild:
        server_context = build_server_context(interaction)
        if server_context:
            system_prompt += f"\n{server_context}\n"

    # Cronologia del canale
    history_data  = history_manager.get_context(channel_id)
    context_lines = [
        f"{'purpleGPT' if m['role'] == 'ai' else m.get('username', 'User')}: {m['content']}"
        for m in history_data
    ]

    try:
        if image is not None:
            SUPPORTED = ("image/png", "image/jpeg", "image/webp")
            try:
                image_bytes, mime = await download_discord_attachment(image, SUPPORTED)
            except ValueError as exc:
                quota_manager.decrement_usage(uid, "chat")
                await interaction.followup.send(attachment_error_text(str(exc), lang, image.content_type), ephemeral=True)
                return

            # Per richieste multimodali costruiamo contenuti strutturati
            testo_utente = (
                f"{system_prompt}\n\nContext:\n" + "\n".join(context_lines) + f"\n\n{interaction.user.name}: {prompt}"
            )
            contents = build_multimodal_content(image_bytes, mime, testo_utente)
            chat_model = CHAT_IMAGE_MODEL_PRO if used_pro_model else CHAT_IMAGE_MODEL
        else:
            context_lines.append(f"{interaction.user.name}: {prompt}")
            contents = system_prompt + "\n\n" + "\n".join(context_lines)

        risposta = await asyncio.to_thread(
            client.models.generate_content,
            model=chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                automatic_function_calling=NO_AFC,
            )
        )
        testo = (risposta.text or "").strip()

        if not testo:
            quota_manager.decrement_usage(uid, "chat")
            if used_pro_model:
                quota_manager.decrement_usage(uid, "chat_pro")
            await interaction.followup.send(t("chat.error_no_response", lang), ephemeral=True)
            return

        history_manager.add_message(
            channel_id, "user",
            prompt + (" [+ image attached]" if image else ""),
            user_id=uid, username=interaction.user.name
        )
        history_manager.add_message(channel_id, "ai", testo)

        risposta_finale = avviso_pro + testo
        LIMIT = 2000
        chunks = [risposta_finale[i:i + LIMIT] for i in range(0, len(risposta_finale), LIMIT)]
        first_msg = None
        for i, chunk in enumerate(chunks):
            if i == 0:
                # Il primo pezzo di risposta sostituisce il messaggio "sto elaborando..."
                await interaction.edit_original_response(content=chunk)
                first_msg = await interaction.original_response()
            else:
                await interaction.followup.send(chunk)

        # Reazione AI al messaggio di risposta del bot - lanciata in background
        if first_msg:
            asyncio.create_task(apply_reaction(first_msg, prompt, testo))

    except Exception as e:
        quota_manager.decrement_usage(uid, "chat")
        if used_pro_model:
            quota_manager.decrement_usage(uid, "chat_pro")
        log.error(f"[/chat] {e}", exc_info=True)
        await interaction.followup.send(t("error.generic", lang), ephemeral=True)

    finally:
        _progress_task.cancel()


# /draw

@bot.tree.command(name="draw", description="Generate an AI image - attach a photo as a style reference (optional)")
@app_commands.describe(
    prompt="Image description",
    image="Reference image (optional)",
    context="Use server context to guide the style (default: No)"
)
async def draw(
    interaction: discord.Interaction,
    prompt: str,
    image: discord.Attachment | None = None,
    context: bool = False
):
    uid        = str(interaction.user.id)
    user_cfg   = settings_manager.get_settings(uid)
    lang       = get_lang(uid, user_cfg)
    if not await check_tos(interaction, lang):
        return
    if not await check_rate_and_quota(interaction, "image", has_quota=True, lang=lang):
        return

    await interaction.response.defer(thinking=True)
    await interaction.edit_original_response(content=t("draw.progress.0", lang))
    _progress_task = asyncio.create_task(progress_updater(
        interaction,
        [t("draw.progress.1", lang), t("draw.progress.2", lang)],
        interval=4.0
    ))

    channel_id = interaction.channel_id
    _draw_try_started = True
    image_size = user_cfg["image_size"]
    size_hint  = settings_manager.SIZE_HINT.get(image_size, "square 1:1 aspect ratio")

# Contesto server opzionale - aggiunto al prompt testuale
    ctx_suffix = ""
    if context:
        ctx_str = build_image_context(interaction)
        if ctx_str:
            ctx_suffix = f" Consider this server context to inform the style or theme: {ctx_str}."

    try:
        if image is not None:
            SUPPORTED = ("image/png", "image/jpeg", "image/webp")
            try:
                ref_bytes, mime = await download_discord_attachment(image, SUPPORTED)
            except ValueError as exc:
                quota_manager.decrement_usage(uid, "image")
                await interaction.followup.send(attachment_error_text(str(exc), lang, image.content_type), ephemeral=True)
                return

            contents = build_multimodal_content(
                ref_bytes,
                mime,
                f"Using this image as a reference, generate a new image: {prompt}. The output must have a {size_hint}.{ctx_suffix}"
            )
        else:
            contents = f"Generate an image: {prompt}. The image must have a {size_hint}.{ctx_suffix}"

        result = await asyncio.to_thread(
            client.models.generate_content,
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                automatic_function_calling=NO_AFC,
            )
        )

        testo_risposta   = ""
        immagine_binaria = None
        for part in (result.parts or []):
            if part.text:
                testo_risposta += part.text + "\n"
            elif part.inline_data:
                immagine_binaria = part.inline_data.data

        if immagine_binaria:
            file_discord = discord.File(fp=io.BytesIO(immagine_binaria), filename="creazione.png")
            msg  = testo_risposta.strip() or t("draw.caption", lang, prompt=prompt)
            msg += f"\n-# {t('draw.size_label', lang, size=image_size)}"
            if image:
                msg += f"  •  {t('draw.from_reference', lang)}"
            await interaction.edit_original_response(content=msg, attachments=[file_discord])
            sent = await interaction.original_response()
            history_manager.save_generated_image(channel_id, uid, sent.id)
            history_manager.save_user_activity(
                uid,
                "/draw",
                prompt + (" [with reference image]" if image else ""),
                "success",
                guild_id=interaction.guild_id,
                channel_id=interaction.channel_id,
            )

            # Mostra agli utenti free quante immagini giornaliere restano
            if not quota_manager.is_premium(uid):
                used      = quota_manager.get_usage(uid, "image")
                bonus_img, _ = quota_manager.get_vote_bonus(uid)
                base      = quota_manager.PLANS["free"]["image_daily"]
                limit     = base + bonus_img
                remaining = max(0, limit - used)
                vote_hint = "" if bonus_img > 0 else t("quota.remaining.image.vote_hint", lang)
                await interaction.followup.send(
                    t("quota.remaining.image", lang, remaining=remaining, limit=limit, vote_hint=vote_hint),
                    ephemeral=True
                )

        elif testo_risposta:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(t("draw.error_text_only", lang, reason=testo_risposta))
        else:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(t("draw.error_no_content", lang))

    except Exception as e:
        quota_manager.decrement_usage(uid, "image")
        log.error(f"[/draw] {e}", exc_info=True)
        await interaction.followup.send(t("error.generic", lang), ephemeral=True)

    finally:
        if "_draw_try_started" in dir():
            _progress_task.cancel()


# /edit

@bot.tree.command(name="edit", description="Edit an image with AI - attach a photo or use the last one generated for you")
@app_commands.describe(
    instructions="Editing instructions",
    image="Image to edit (optional)",
    context="Use server context to guide the style (default: No)"
)
async def edit_image(
    interaction: discord.Interaction,
    instructions: str,
    image: discord.Attachment | None = None,
    context: bool = False
):
    uid        = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)
    if not await check_tos(interaction, lang):
        return

    channel_id = interaction.channel_id
    _progress_task: asyncio.Task | None = None

    image_bytes: bytes | None = None
    media_type = "image/png"

    if image is not None:
        SUPPORTED = ("image/png", "image/jpeg", "image/webp")
        if not await check_rate_and_quota(interaction, "image", has_quota=True, lang=lang):
            return

        await interaction.response.defer(thinking=True)
        await interaction.edit_original_response(content=t("edit.progress.0", lang))
        _progress_task = asyncio.create_task(progress_updater(
            interaction,
            [t("edit.progress.1", lang), t("edit.progress.2", lang)],
            interval=4.0
        ))

        try:
            image_bytes, media_type = await download_discord_attachment(image, SUPPORTED)
        except ValueError as exc:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(attachment_error_text(str(exc), lang, image.content_type), ephemeral=True)
            return

    else:
        # Recupera l'ultima immagine generata per l'utente in questo canale
        last_msg_id = history_manager.get_last_generated_image_id(channel_id, uid)

        if last_msg_id is None:
            await interaction.response.send_message(t("edit.no_image_found", lang), ephemeral=True)
            return

        if not await check_rate_and_quota(interaction, "image", has_quota=True, lang=lang):
            return

        await interaction.response.defer(thinking=True)
        await interaction.edit_original_response(content=t("edit.progress.0", lang))
        _progress_task = asyncio.create_task(progress_updater(
            interaction,
            [t("edit.progress.1", lang), t("edit.progress.2", lang)],
            interval=4.0
        ))

        try:
            ref_message = await interaction.channel.fetch_message(int(last_msg_id))
        except discord.NotFound:
            await interaction.followup.send(t("edit.image_deleted", lang), ephemeral=True)
            return

        if not ref_message.attachments:
            await interaction.followup.send(t("edit.no_attachment", lang), ephemeral=True)
            return

        attachment = ref_message.attachments[0]
        SUPPORTED = ("image/png", "image/jpeg", "image/webp")
        try:
            image_bytes, media_type = await download_discord_attachment(attachment, SUPPORTED)
        except ValueError as exc:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(attachment_error_text(str(exc), lang, attachment.content_type), ephemeral=True)
            return

    # Chiama Gemini per la modifica
    image_size = user_cfg["image_size"]
    size_hint  = settings_manager.SIZE_HINT.get(image_size, "square 1:1 aspect ratio")
    # Contesto server opzionale
    ctx_suffix = ""
    if context:
        ctx_str = build_image_context(interaction)
        if ctx_str:
            ctx_suffix = f" Consider this server context to inform the style or theme: {ctx_str}."

    try:
        contents = build_multimodal_content(
            image_bytes,
            media_type,
            f"Edit this image: {instructions}. Keep the general style. Output: {size_hint}. Return only the image.{ctx_suffix}"
        )

        result = await asyncio.to_thread(
            client.models.generate_content,
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                automatic_function_calling=NO_AFC,
            )
        )

        testo_risposta    = ""
        immagine_modificata = None
        for part in (result.parts or []):
            if part.text:
                testo_risposta += part.text + "\n"
            elif part.inline_data:
                immagine_modificata = part.inline_data.data

        if immagine_modificata:
            file_discord = discord.File(fp=io.BytesIO(immagine_modificata), filename="modifica.png")
            msg  = testo_risposta.strip() or t("edit.caption", lang)
            msg += f"\n-# ✏️ `{instructions}`  •  📐 `{image_size}`"
            await interaction.edit_original_response(content=msg, attachments=[file_discord])
            sent = await interaction.original_response()
            history_manager.save_generated_image(channel_id, uid, sent.id)
            history_manager.save_user_activity(
                uid,
                "/edit",
                instructions + (" [with uploaded image]" if image else " [from last generated image]"),
                "success",
                guild_id=interaction.guild_id,
                channel_id=interaction.channel_id,
            )

            # Mostra agli utenti free quante immagini giornaliere restano
            if not quota_manager.is_premium(uid):
                used      = quota_manager.get_usage(uid, "image")
                bonus_img, _ = quota_manager.get_vote_bonus(uid)
                base      = quota_manager.PLANS["free"]["image_daily"]
                limit     = base + bonus_img
                remaining = max(0, limit - used)
                vote_hint = "" if bonus_img > 0 else t("quota.remaining.image.vote_hint", lang)
                await interaction.followup.send(
                    t("quota.remaining.image", lang, remaining=remaining, limit=limit, vote_hint=vote_hint),
                    ephemeral=True
                )

        elif testo_risposta:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(t("edit.error_text_only", lang, reason=testo_risposta))
        else:
            quota_manager.decrement_usage(uid, "image")
            await interaction.followup.send(t("edit.error_no_content", lang))

    except Exception as e:
        quota_manager.decrement_usage(uid, "image")
        log.error(f"[/edit] {e}", exc_info=True)
        await interaction.followup.send(t("error.generic", lang), ephemeral=True)

    finally:
        if _progress_task is not None:
            _progress_task.cancel()


# /compose

def get_google_access_token() -> str:
    """Recupera un access token ADC per chiamate REST ad Agent Platform."""
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not credentials.valid:
        credentials.refresh(GoogleAuthRequest())
    return credentials.token


def _audio_extension_from_mime(mime_type: str) -> str:
    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if mime == "audio/wav":
        return "wav"
    if mime in ("audio/mpeg", "audio/mp3"):
        return "mp3"
    return "mp3"


def _extract_lyria_audio(data: dict) -> tuple[bytes, str] | None:
    """Estrae il primo output audio valido da una risposta Lyria 3."""
    def iter_outputs(obj):
        if isinstance(obj, list):
            for item in obj:
                yield from iter_outputs(item)
        elif isinstance(obj, dict):
            if obj.get("type") == "audio" or str(obj.get("mime_type") or obj.get("mimeType") or "").startswith("audio/"):
                yield obj
            for key in ("outputs", "output", "response", "result", "content", "audio"):
                if key in obj:
                    yield from iter_outputs(obj[key])

    for output in iter_outputs(data):
        audio_b64 = str(output.get("data") or output.get("bytes") or "")
        if not audio_b64:
            continue
        if "," in audio_b64 and audio_b64.startswith("data:"):
            audio_b64 = audio_b64.split(",", 1)[1]
        mime_type = str(output.get("mime_type") or output.get("mimeType") or "audio/mpeg")
        return base64.b64decode(audio_b64), mime_type

    return None


async def _get_lyria_interaction(
    session: aiohttp.ClientSession,
    token: str,
    interaction_id: str,
) -> dict | None:
    """Recupera una interaction Lyria 3 per ID provando i path noti dell'API preview."""
    headers = {"Authorization": f"Bearer {token}"}
    urls = [
        f"https://aiplatform.googleapis.com/v1beta1/interactions/{interaction_id}",
        f"https://global-aiplatform.googleapis.com/v1beta1/interactions/{interaction_id}",
        f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions/{interaction_id}",
    ]

    for url in urls:
        try:
            async with session.get(url, headers=headers, timeout=LYRIA_TIMEOUT) as resp:
                body = await resp.text()
                if resp.status == 200:
                    try:
                        return json.loads(body)
                    except Exception as exc:
                        log.warning(f"[/compose] Lyria 3 GET non JSON da {url}: {body[:300]}")
                        raise RuntimeError("Lyria 3 interaction response is not JSON") from exc
                if resp.status not in (404, 405):
                    log.warning(f"[/compose] Lyria 3 GET {resp.status} da {url}: {body[:300]}")
        except asyncio.TimeoutError:
            log.warning(f"[/compose] Timeout recuperando interaction Lyria 3 da {url}")
        except aiohttp.ClientError as exc:
            log.warning(f"[/compose] Errore HTTP recuperando interaction Lyria 3 da {url}: {exc}")

    return None


async def _wait_for_lyria_audio(
    session: aiohttp.ClientSession,
    token: str,
    interaction_id: str,
) -> tuple[bytes, str] | None:
    """Aspetta che una interaction Lyria 3 esponga gli outputs audio."""
    for attempt in range(1, LYRIA_POLL_ATTEMPTS + 1):
        await asyncio.sleep(LYRIA_POLL_INTERVAL)
        data = await _get_lyria_interaction(session, token, interaction_id)
        if not data:
            continue

        audio = _extract_lyria_audio(data)
        if audio:
            return audio

        status = data.get("status")
        if status in ("failed", "cancelled", "canceled"):
            log.error(f"[/compose] Lyria 3 interaction {interaction_id} terminata con status {status}: {str(data)[:500]}")
            return None
        log.info(f"[/compose] Lyria 3 interaction {interaction_id} senza audio al tentativo {attempt}/{LYRIA_POLL_ATTEMPTS} (status={status})")

    return None


async def generate_lyria3_music(stile: str, bpm: int, durata: int) -> tuple[bytes, str]:
    """
    Genera musica con Lyria 3 tramite Gemini Enterprise Agent Platform API.
    Ritorna (audio_bytes, mime_type).
    """
    token = await asyncio.to_thread(get_google_access_token)
    prompt = (
        "Create an original instrumental music clip. "
        f"Style and mood: {stile}. "
        f"Target tempo: around {bpm} BPM. "
        f"Target duration: about {durata} seconds. "
        "No vocals, no lyrics, no copyrighted melodies, clean mix, high quality."
    )
    payload = {
        "model": LYRIA_MODEL,
        "input": [
            {
                "type": "text",
                "text": prompt,
            }
        ],
    }
    url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions"
    session = await get_session()

    async with session.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=LYRIA_TIMEOUT,
    ) as resp:
        raw_body = await resp.text()
        if resp.status != 200:
            log.error(f"[/compose] Lyria 3 errore HTTP {resp.status}: {raw_body[:500]}")
            raise RuntimeError(f"Lyria 3 HTTP {resp.status}")

    try:
        data = json.loads(raw_body)
    except Exception as exc:
        log.error(f"[/compose] Risposta Lyria 3 non JSON: {raw_body[:500]}")
        raise RuntimeError("Lyria 3 response is not JSON") from exc

    if data.get("status") and data.get("status") not in ("completed", "running", "pending"):
        log.error(f"[/compose] Lyria 3 status non completato: {data.get('status')} - {raw_body[:500]}")
        raise RuntimeError(f"Lyria 3 status {data.get('status')}")

    audio = _extract_lyria_audio(data)
    if audio:
        return audio

    interaction_id = data.get("id")
    if interaction_id:
        audio = await _wait_for_lyria_audio(session, token, str(interaction_id))
        if audio:
            return audio

    log.error(f"[/compose] Risposta Lyria 3 senza audio: {raw_body[:500]}")
    raise RuntimeError("Lyria 3 response did not contain audio")


def _get_media_duration(path: str) -> float:
    """Ritorna la durata in secondi di un file audio/video tramite ffprobe."""
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def trim_audio_duration(audio_path: str, target_durata: int) -> bool:
    """
    Lyria 3 (lyria-3-clip-preview) genera una clip musicale a lunghezza fissa (~28-30s).
    Se l'utente ha richiesto una durata inferiore (es. 10s), questa funzione taglia
    l'audio esattamente a target_durata secondi con ffmpeg, applicando una dissolvenza
    in uscita (fade-out) morbida per garantire una chiusura naturale del brano.
    """
    actual_dur = _get_media_duration(audio_path)
    # Se l'audio generato rispetta già la durata target (+0.5s di margine), non serve ritagliarlo
    if actual_dur <= 0.0 or actual_dur <= (target_durata + 0.5):
        return False

    fade_len = 1.0 if target_durata <= 10 else 1.5
    fade_start = max(0.0, float(target_durata) - fade_len)

    base, ext = os.path.splitext(audio_path)
    tmp_trimmed = f"{base}_trimmed{ext}"
    try:
        cmd = [
            FFMPEG, "-y",
            "-i", audio_path,
            "-t", str(target_durata),
            "-af", f"afade=t=out:st={fade_start:.2f}:d={fade_len:.2f}",
        ]
        if ext.lower() == ".mp3":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2", "-f", "mp3"])
        elif ext.lower() == ".wav":
            cmd.extend(["-c:a", "pcm_s16le", "-f", "wav"])

        cmd.append(tmp_trimmed)
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            log.warning(f"[ffmpeg trim] {r.stderr.decode('utf-8', errors='ignore')}")
            return False

        if os.path.exists(tmp_trimmed) and os.path.getsize(tmp_trimmed) > 0:
            os.replace(tmp_trimmed, audio_path)
            return True
        return False
    except Exception as exc:
        log.warning(f"[trim_audio_duration] Errore durante il trim dell'audio: {exc}")
        return False
    finally:
        if os.path.exists(tmp_trimmed):
            try:
                os.remove(tmp_trimmed)
            except Exception:
                pass


def build_video(image_path: str, audio_path: str, output_path: str, durata: int) -> bool:
    """
    Assembla il video finale con ffmpeg in 4 step:
    1. immagine ferma (durata audio - durata transition)
    2. transition convertita in MP4
    3. concatenazione dei due clip (video silenzioso)
    4. merge video + audio
    """
    audio_dur = _get_media_duration(audio_path)

    # Se la clip di transizione non è presente, esegui un fallback pulito con sola immagine + audio
    if not os.path.exists(TRANSITION_FILE):
        r = subprocess.run([
            FFMPEG, "-y",
            "-loop", "1", "-t", str(audio_dur),
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-shortest", "-movflags", "+faststart",
            output_path
        ], capture_output=True)
        if r.returncode != 0:
            log.warning(f"[ffmpeg merge no-trans] {r.stderr.decode('utf-8', errors='ignore')}")
            return False
        return True

    transition_dur = _get_media_duration(TRANSITION_FILE)
    still_dur      = max(0.1, audio_dur - transition_dur)

    tmp_id          = str(uuid.uuid4())[:8]
    still_path      = f"tmp_still_{tmp_id}.mp4"
    transition_path = f"tmp_transition_{tmp_id}.mp4"
    concat_list     = f"tmp_concat_{tmp_id}.txt"
    silent_video    = f"tmp_silent_{tmp_id}.mp4"

    try:
        r1 = subprocess.run([FFMPEG, "-y", "-loop", "1", "-t", str(still_dur), "-i", image_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", still_path], capture_output=True)
        if r1.returncode != 0:
            log.warning(f"[ffmpeg still] {r1.stderr.decode('utf-8', errors='ignore')}")
            return False

        r2 = subprocess.run([FFMPEG, "-y", "-i", TRANSITION_FILE, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", transition_path], capture_output=True)
        if r2.returncode != 0:
            log.warning(f"[ffmpeg trans] {r2.stderr.decode('utf-8', errors='ignore')}")
            return False

        with open(concat_list, "w") as f:
            f.write(f"file '{os.path.abspath(still_path)}'\n")
            f.write(f"file '{os.path.abspath(transition_path)}'\n")

        r3 = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", silent_video], capture_output=True)
        if r3.returncode != 0:
            log.warning(f"[ffmpeg concat] {r3.stderr.decode('utf-8', errors='ignore')}")
            return False

        r4 = subprocess.run([FFMPEG, "-y", "-i", silent_video, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", output_path], capture_output=True)
        if r4.returncode != 0:
            log.warning(f"[ffmpeg merge] {r4.stderr.decode('utf-8', errors='ignore')}")
            return False

        return True

    finally:
        for f in [still_path, transition_path, concat_list, silent_video]:
            if os.path.exists(f):
                os.remove(f)


@bot.tree.command(name="compose", description="Compose an original AI music track - optionally generate a video too")
@app_commands.describe(
    style="Genre or mood (e.g. 'lofi chill', 'epic orchestral')",
    bpm="Beats per minute - default 90",
    duration="Duration in seconds (5-30) - default 30",
    video="Also generate a video with cover image - default No"
)
async def compose(
    interaction: discord.Interaction,
    style: str,
    bpm: int = 90,
    duration: int = 30,
    video: bool = False
):
    uid      = str(interaction.user.id)
    user_cfg_c = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg_c)
    if not await check_tos(interaction, lang):
        return

    bpm      = max(60,  min(200, bpm))
    duration = max(5,   min(30,  duration))

    if not await check_rate_and_quota(interaction, "compose", has_quota=True, lang=lang):
        return

    await interaction.response.defer(thinking=True)
    video_suffix = t("compose.status_video_suffix", lang) if video else ""
    await interaction.edit_original_response(
        content=t("compose.status_generating", lang, style=style, bpm=bpm, duration=duration, video=video_suffix)
    )

    tmp_id = str(uuid.uuid4())[:8]
    audio_path = f"tmp_audio_{tmp_id}.mp3"
    img_path   = f"tmp_image_{tmp_id}.png"
    video_path = f"tmp_video_{tmp_id}.mp4"

    async def genera_audio() -> tuple[bytes, str]:
        return await generate_lyria3_music(style, bpm, duration)

    async def genera_immagine() -> bytes | None:
        """Cover art 1:1 ispirata allo stile. Ritorna None se fallisce."""
        try:
            result = await asyncio.to_thread(
                client.models.generate_content,
                model=IMAGE_MODEL,
                contents=(
                    f"Generate an evocative artistic image representing the musical style: {style}. "
                    f"Abstract, atmospheric, suitable as music cover art. No text. Square 1:1 aspect ratio."
                ),
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    automatic_function_calling=NO_AFC,
                )
            )
            for part in (result.parts or []):
                if part.inline_data:
                    return part.inline_data.data
            return None
        except Exception as e:
            log.warning(f"[/compose] Immagine copertina fallita: {e}")
            return None

    try:
        if video:
            await interaction.edit_original_response(
                content=t("compose.status_parallel", lang, style=style, bpm=bpm, duration=duration)
            )
            (audio_bytes, audio_mime), image_bytes = await asyncio.gather(genera_audio(), genera_immagine())
        else:
            audio_bytes, audio_mime = await genera_audio()
            image_bytes = None

        audio_ext = _audio_extension_from_mime(audio_mime)
        audio_path = f"tmp_audio_{tmp_id}.{audio_ext}"

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # Se Lyria 3 genera una clip più lunga della durata richiesta dall'utente,
        # ritagliamo l'audio a `duration` secondi con fade-out morbido
        trimmed = await asyncio.to_thread(trim_audio_duration, audio_path, duration)
        if trimmed:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

        video_ok = False
        if video and image_bytes is not None:
            with open(img_path, "wb") as f:
                f.write(image_bytes)
            await interaction.edit_original_response(content=t("compose.status_assembling", lang, style=style, bpm=bpm, duration=duration))
            video_ok = await asyncio.to_thread(build_video, img_path, audio_path, video_path, duration)

        # Scegli il tipo di risposta in base al risultato
        footer = f"-# 🎼 `{style}`  •  🥁 `{bpm} BPM`  •  ⏱️ `{duration}s`"
        if video_ok and os.path.exists(video_path):
            await interaction.edit_original_response(content=f"{t('compose.result_video', lang)}\n{footer}", attachments=[discord.File(fp=video_path, filename="composizione.mp4")])
        elif video and image_bytes is None:
            await interaction.edit_original_response(content=f"{t('compose.result_image_failed', lang)}\n{footer}", attachments=[discord.File(fp=io.BytesIO(audio_bytes), filename=f"composizione.{audio_ext}")])
        elif video and not video_ok:
            await interaction.edit_original_response(content=f"{t('compose.result_video_failed', lang)}\n{footer}", attachments=[discord.File(fp=io.BytesIO(audio_bytes), filename=f"composizione.{audio_ext}")])
        else:
            await interaction.edit_original_response(content=f"{t('compose.result_audio', lang)}\n{footer}", attachments=[discord.File(fp=io.BytesIO(audio_bytes), filename=f"composizione.{audio_ext}")])

        history_manager.save_user_activity(
            uid,
            "/compose",
            f"style={style}; bpm={bpm}; duration={duration}s; video={video}",
            "success",
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
        )

        # Mostra agli utenti free quante composizioni giornaliere restano
        if not quota_manager.is_premium(uid):
            plan_limit = quota_manager.PLANS["free"]["compose_daily"]
            if plan_limit != -1:
                used      = quota_manager.get_usage(uid, "compose")
                _, bonus_compose = quota_manager.get_vote_bonus(uid)
                limit     = plan_limit + bonus_compose
                remaining = max(0, limit - used)
                await interaction.followup.send(
                    t("quota.remaining.compose", lang, remaining=remaining, limit=limit),
                    ephemeral=True
                )

    except Exception as e:
        quota_manager.decrement_usage(uid, "compose")
        log.error(f"[/compose] {e}", exc_info=True)
        await interaction.edit_original_response(content=t("error.generic", lang))

    finally:
        for f in [audio_path, img_path, video_path]:
            if os.path.exists(f):
                os.remove(f)


# /help

def _build_help_embed(lang: str) -> discord.Embed:
    """Costruisce l'embed /help nella lingua richiesta usando strings.py."""
    embed = discord.Embed(
        title=t("help.title", lang),
        description=t("help.description", lang),
        color=0x8000FF
    )
    field_keys = ["chat", "draw", "edit", "compose", "settings", "stats",
                  "history", "bugreport", "delete", "export", "premium",
                  "vote", "server_prompt", "broadcast", "genserver", "help"]
    for key in field_keys:
        embed.add_field(
            name=t(f"help.field.{key}.name", lang),
            value=t(f"help.field.{key}.value", lang),
            inline=False
        )
    embed.set_footer(text=t("help.footer", lang))
    return embed


# /stats

@bot.tree.command(name="stats", description="View your personal purpleGPT usage stats")
async def stats_cmd(interaction: discord.Interaction):
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)
    await interaction.response.defer(thinking=True, ephemeral=True)

    with get_conn() as conn:
        # Data del primo utilizzo (tabella users)
        user_row = conn.execute(
            "SELECT accepted_at FROM users WHERE user_id = ?", (uid,)
        ).fetchone()

        # Messaggi inviati totali
        msg_count = conn.execute(
            "SELECT COUNT(*) as n FROM messages WHERE user_id = ? AND role = 'user'", (uid,)
        ).fetchone()["n"]

        # Immagini generate totali
        img_count = conn.execute(
            "SELECT COUNT(*) as n FROM generated_images WHERE user_id = ?", (uid,)
        ).fetchone()["n"]

        # Utilizzo oggi per ogni gruppo
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage_rows = conn.execute(
            "SELECT command_group, count FROM daily_usage "
            "WHERE user_id = ? AND date = ?", (uid, today)
        ).fetchall()
        usage_today = {r["command_group"]: r["count"] for r in usage_rows}

        # Utilizzo totale storico
        total_rows = conn.execute(
            "SELECT command_group, SUM(count) as total FROM daily_usage "
            "WHERE user_id = ? GROUP BY command_group", (uid,)
        ).fetchall()
        usage_total = {r["command_group"]: r["total"] for r in total_rows}

    # Piano
    #plan = quota_manager.get_plan(uid)
    #plan_label = "Premium" if plan == "premium" else "Free"

    # Data di registrazione dell'utente
    member_since = "-"
    if user_row and user_row["accepted_at"]:
        try:
            dt = datetime.fromisoformat(user_row["accepted_at"])
            member_since = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    embed = discord.Embed(
        title=t("stats.title", lang),
        color=0x8000FF
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.add_field(name=t("stats.field.since", lang),    value=member_since, inline=True)
    #embed.add_field(name="Piano",           value=plan_label,         inline=True)
    embed.add_field(name=" ",             value=" ",           inline=True)

    embed.add_field(name=t("stats.field.messages", lang), value=t("stats.field.total_value", lang, n=msg_count), inline=True)
    embed.add_field(name=t("stats.field.images", lang),   value=t("stats.field.total_value", lang, n=img_count),   inline=True)
    embed.add_field(name=" ",               value=" ",                   inline=True)

    # Utilizzo oggi
    chat_oggi    = usage_today.get("chat", 0)
    image_oggi   = usage_today.get("image", 0)
    compose_oggi = usage_today.get("compose", 0)
    embed.add_field(
        name=t("stats.field.today", lang),
        value=(
            f"`/chat` **{chat_oggi}** - "
            f"`/draw & /edit` **{image_oggi}** - "
            f"`/compose` **{compose_oggi}**"
        ),
        inline=False
    )

    # Utilizzo totale storico
    chat_tot    = usage_total.get("chat", 0)
    image_tot   = usage_total.get("image", 0)
    compose_tot = usage_total.get("compose", 0)
    embed.add_field(
        name=t("stats.field.history", lang),
        value=(
            f"`/chat` **{chat_tot}** - "
            f"`/draw & /edit` **{image_tot}** - "
            f"`/compose` **{compose_tot}**"
        ),
        inline=False
    )

    embed.set_footer(text=t("stats.footer", lang))
    log.info(f"[/stats] {interaction.user.name} ({uid})")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="Show all available purpleGPT commands")
async def help_command(interaction: discord.Interaction):
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(embed=_build_help_embed(lang))


# /history

class HistorySelect(discord.ui.Select):
    def __init__(self, channel_id: int, lang: str = DEFAULT_LANG):
        self.channel_id = channel_id
        self.lang = lang
        super().__init__(
            placeholder=t("history.select.placeholder", lang),
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(label=t("history.option.enable",  lang), value="on",    emoji="🟢"),
                discord.SelectOption(label=t("history.option.disable", lang), value="off",   emoji="🔴"),
                discord.SelectOption(label=t("history.option.clear",   lang), value="clear", emoji="🗑️"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        lang = self.lang
        action = self.values[0]
        if action == "on":
            history_manager.set_enabled(self.channel_id, True)
            msg = t("history.enabled", lang)
        elif action == "off":
            history_manager.set_enabled(self.channel_id, False)
            msg = t("history.disabled", lang)
        else:
            history_manager.clear(self.channel_id)
            msg = t("history.cleared", lang)
        await interaction.response.edit_message(content=msg, view=None)


class HistoryView(discord.ui.View):
    def __init__(self, channel_id: int, lang: str = DEFAULT_LANG):
        super().__init__(timeout=60)
        self.add_item(HistorySelect(channel_id, lang))


@bot.tree.command(name="history", description="[Admin] Manage message history memory for this channel")
async def history_cmd(interaction: discord.Interaction):
    # In server: controlla i permessi prima di procedere
    uid  = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang = get_lang(uid, user_cfg)
    if interaction.guild is not None and not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(t("history.no_permission", lang), ephemeral=True)
        return

    await interaction.response.send_message(t("history.title", lang), view=HistoryView(interaction.channel_id, lang), ephemeral=True)


# /settings

class CustomPromptModal(discord.ui.Modal, title="✏️ Prompt"):
    def __init__(self, user_id: str, current_prompt: str, lang: str = DEFAULT_LANG):
        super().__init__()
        self.user_id = user_id
        self.prompt_input = discord.ui.TextInput(
            label=t("settings.modal.prompt.label", lang),
            style=discord.TextStyle.paragraph,
            placeholder=t("settings.modal.prompt.placeholder", lang),
            default=current_prompt,
            required=False,
            max_length=500
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        new_prompt = self.prompt_input.value.strip()
        lang = get_lang(self.user_id, settings_manager.get_settings(self.user_id))
        settings_manager.set_custom_prompt(self.user_id, new_prompt)
        await interaction.response.send_message(
            t("settings.prompt.saved", lang) if new_prompt else t("settings.prompt.removed", lang),
            ephemeral=True
        )


class TemperatureSelect(discord.ui.Select):
    def __init__(self, user_id: str, current_temp: float, lang: str = DEFAULT_LANG):
        self.user_id = user_id
        options = [
            discord.SelectOption(label=f"🌡️ {label}", value=val, default=(abs(float(val) - current_temp) < 0.01))
            for val, label in settings_manager.get_temperature_options(lang)
        ]
        super().__init__(placeholder=t("settings.temperature.placeholder", lang), min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        settings_manager.set_temperature(self.user_id, float(self.values[0]))
        lang = get_lang(self.user_id, settings_manager.get_settings(self.user_id))
        await interaction.response.send_message(t("settings.temperature.saved", lang, value=self.values[0]), ephemeral=True)


class ImageSizeSelect(discord.ui.Select):
    def __init__(self, user_id: str, current_size: str, lang: str = DEFAULT_LANG):
        self.user_id = user_id
        options = [
            discord.SelectOption(label=f"📐 {label}", value=val, default=(val == current_size))
            for val, label in settings_manager.get_image_size_options(lang)
        ]
        super().__init__(placeholder=t("settings.image_size.placeholder", lang), min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        settings_manager.set_image_size(self.user_id, self.values[0])
        lang = get_lang(self.user_id, settings_manager.get_settings(self.user_id))
        await interaction.response.send_message(t("settings.image_size.saved", lang, value=self.values[0]), ephemeral=True)



class LanguageSelect(discord.ui.Select):
    def __init__(self, user_id: str, current_lang: str):
        self.user_id = user_id
        options = [
            discord.SelectOption(label=label, value=val, default=(val == current_lang))
            for val, label in settings_manager.LANGUAGE_OPTIONS
        ]
        super().__init__(placeholder=t("settings.language.placeholder", current_lang), min_values=1, max_values=1, options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        settings_manager.set_language(self.user_id, self.values[0])
        # Leggi il label della lingua scelta per mostrarlo nel messaggio
        label = next((l for v, l in settings_manager.LANGUAGE_OPTIONS if v == self.values[0]), self.values[0])
        # Usa la nuova lingua gia per il messaggio di conferma
        lang = self.values[0]
        await interaction.response.send_message(
            t("settings.language.saved", lang, value=label), ephemeral=True
        )


class SettingsView(discord.ui.View):
    def __init__(self, user_id: str, cfg: dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.cfg     = cfg
        self.lang    = cfg.get("language", DEFAULT_LANG)
        self.add_item(TemperatureSelect(user_id, cfg["temperature"], self.lang))
        self.add_item(ImageSizeSelect(user_id, cfg["image_size"], self.lang))
        self.add_item(LanguageSelect(user_id, cfg.get("language", DEFAULT_LANG)))

        btn_prompt = discord.ui.Button(
            label=t("settings.button.edit_prompt", self.lang),
            style=discord.ButtonStyle.secondary,
            emoji="✏️",
            row=3
        )
        btn_prompt.callback = self._cb_edit_prompt
        self.add_item(btn_prompt)

        btn_reset = discord.ui.Button(
            label=t("settings.button.reset", self.lang),
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=3
        )
        btn_reset.callback = self._cb_reset
        self.add_item(btn_reset)

    async def _cb_edit_prompt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CustomPromptModal(self.user_id, self.cfg["custom_prompt"], self.lang))

    async def _cb_reset(self, interaction: discord.Interaction):
        settings_manager.reset_settings(self.user_id)
        lang = get_lang(self.user_id, settings_manager.get_settings(self.user_id))
        await interaction.response.send_message(t("settings.reset.done", lang), ephemeral=True)


def _settings_embed(cfg: dict, username: str, user_id: str, lang: str = DEFAULT_LANG) -> discord.Embed:
    # Mostra il piano corrente (Free / Starter / Pro + eventuale trial)
    plan_info = quota_manager.get_plan_info(user_id)
    plan = plan_info["plan"]

    if plan == "free":
        plan_label = t("settings.field.plan.free", lang)
    else:
        if plan_info["expires_at"]:
            try:
                expires  = datetime.fromisoformat(plan_info["expires_at"])
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                giorni   = (expires - datetime.now(timezone.utc)).days
                if giorni > 0:
                    scadenza = f"{giorni}d"
                else:
                    ore = max(0, (expires - datetime.now(timezone.utc)).seconds // 3600)
                    scadenza = f"{ore}h"
                emoji = "⚡" if plan == "starter" else "🚀"
                plan_name = plan.capitalize()
                date_str  = expires.strftime('%Y-%m-%d')
                if plan_info["is_trial"]:
                    plan_label = t("settings.field.plan.trial", lang, plan=plan_name, duration=scadenza, date=date_str)
                else:
                    plan_label = t("settings.field.plan.active", lang, emoji=emoji, plan=plan_name, duration=scadenza, date=date_str)
            except Exception:
                plan_label = f"{plan.capitalize()}"
        else:
            plan_label = f"{plan.capitalize()}"

    # Label della lingua corrente per visualizzarla nell'embed
    lang_label = next((l for v, l in settings_manager.LANGUAGE_OPTIONS if v == cfg.get("language", DEFAULT_LANG)), cfg.get("language", DEFAULT_LANG))

    embed = discord.Embed(title=t("settings.embed.title", lang), color=0x8000FF)
    embed.add_field(name=t("settings.field.plan", lang), value=plan_label, inline=False)
    embed.add_field(name=t("settings.field.temperature", lang), value=t("settings.field.temperature.value", lang, value=cfg["temperature"]), inline=False)
    embed.add_field(name=t("settings.field.image_size", lang),  value=t("settings.field.image_size.value",  lang, value=cfg["image_size"]),  inline=False)
    embed.add_field(name=t("settings.field.language", lang),    value=t("settings.field.language.value",    lang, value=lang_label),          inline=False)
    embed.add_field(name=t("settings.field.custom_prompt", lang), value=f"```{cfg['custom_prompt']}```" if cfg["custom_prompt"] else t("settings.field.custom_prompt.none", lang), inline=False)
    embed.set_footer(text=t("settings.footer", lang, username=username))
    return embed


@bot.tree.command(name="settings", description="Customize your purpleGPT settings - temperature, language, custom prompt")
async def settings_cmd(interaction: discord.Interaction):
    uid  = str(interaction.user.id)
    cfg  = settings_manager.get_settings(uid)
    lang = get_lang(uid, cfg)
    await interaction.response.send_message(
        embed=_settings_embed(cfg, interaction.user.name, uid, lang),
        view=SettingsView(uid, cfg),
        ephemeral=True
    )


# /delete_user_data

class ConfirmDeleteModal(discord.ui.Modal, title="🗑️ Delete data"):
    def __init__(self, user_id: str, lang: str = DEFAULT_LANG):
        super().__init__()
        self.user_id = user_id
        self.confirm_input = discord.ui.TextInput(
            label=t("delete.modal.label", lang),
            placeholder=t("delete.modal.placeholder", lang),
            required=True,
            max_length=20
        )
        self.add_item(self.confirm_input)

    async def on_submit(self, interaction: discord.Interaction):
        lang = get_lang(self.user_id, settings_manager.get_settings(self.user_id))
        if self.confirm_input.value.strip() != t("delete.confirm_word", lang):
            await interaction.response.send_message(t("delete.confirm_failed", lang), ephemeral=True)
            return
        history_manager.delete_user_data(self.user_id)
        settings_manager.reset_settings(self.user_id)
        await interaction.response.send_message(t("delete.success", lang), ephemeral=True)


@bot.tree.command(name="delete_user_data", description="Permanently delete all your personal data from purpleGPT")
async def delete_user_data_cmd(interaction: discord.Interaction):
    uid  = str(interaction.user.id)
    lang = get_lang(uid, settings_manager.get_settings(uid))
    await interaction.response.send_modal(ConfirmDeleteModal(uid, lang))


# /export_data

@bot.tree.command(name="export_data", description="Export all your personal data as a JSON file via DM")
async def export_data(interaction: discord.Interaction):
    user     = interaction.user
    uid      = str(user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)
    await interaction.response.send_message(t("export.preparing", lang), ephemeral=True)

    try:
        data        = history_manager.export_user_data(uid, user.name)
        json_string = json.dumps(data, indent=2, ensure_ascii=False)
        tmp_file    = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=f"_export_{user.id}.json",
            delete=False
        )
        filename    = tmp_file.name

        with tmp_file as f:
            f.write(json_string)
            f.flush()
            os.fsync(f.fileno())

        # Verifica integrita: se il JSON e troncato/corrotto json.loads lancia eccezione
        with open(filename, "r", encoding="utf-8") as f:
            json.loads(f.read())

        try:
            await user.send(content=t("export.dm_message", lang), file=File(filename))
        except discord.Forbidden:
            await interaction.followup.send(t("export.dm_closed", lang), ephemeral=True)

    except json.JSONDecodeError as e:
        log.error(f"[/export_data] JSON corrotto: {e}")
        await interaction.followup.send(t("export.error_corrupt", lang), ephemeral=True)
    except Exception as e:
        log.error(f"[/export_data] {traceback.format_exc()}")
        await interaction.followup.send(t("error.generic", lang), ephemeral=True)
    finally:
        if "filename" in locals() and os.path.exists(filename):
            os.remove(filename)


# /server_prompt

class AddBotView(discord.ui.View):
    def __init__(self, lang: str = DEFAULT_LANG):
        super().__init__(timeout=None)
        bot_id = os.getenv("DISCORD_CLIENT_ID", "YOUR_CLIENT_ID")
        self.add_item(discord.ui.Button(
            label=t("server_prompt.add_bot_button", lang),
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/oauth2/authorize?client_id={bot_id}&permissions=117760&scope=bot+applications.commands",
            emoji="🟣"
        ))


@bot.tree.command(name="server_prompt", description="[Admin] Set, remove or view the server's custom AI prompt")
@app_commands.describe(
    prompt="Instructions for purpleGPT - leave empty to remove the current prompt",
    show="Show the currently set prompt"
)
async def server_prompt_cmd(interaction: discord.Interaction, prompt: str | None = None, show: bool = False):
    uid  = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang = get_lang(uid, user_cfg)

    # In DM: mostra la view per aggiungere il bot prima di verificare i permessi
    if interaction.guild is None:
        embed = discord.Embed(
            title=t("server_prompt.dm_title", lang),
            description=t("server_prompt.dm_description", lang),
            color=0x8000FF
        )
        await interaction.response.send_message(embed=embed, view=AddBotView(lang), ephemeral=True)
        return

    # Verifica permessi utente (solo all'interno di un server)
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(t("server_prompt.no_permission", lang), ephemeral=True)
        return

    # Mostra il prompt attuale senza modificarlo
    if show:
        attuale = get_server_prompt(interaction.guild_id)
        if attuale:
            await interaction.response.send_message(
                t("server_prompt.show_current", lang, prompt=attuale[:1000]),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(t("server_prompt.show_none", lang), ephemeral=True)
        return

    guild_id     = str(interaction.guild_id)
    nuovo_prompt = prompt.strip() if prompt else ""

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO server_settings (guild_id, server_prompt) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET server_prompt = excluded.server_prompt",
            (guild_id, nuovo_prompt)
        )
        conn.commit()

    if nuovo_prompt:
        await interaction.response.send_message(
            t("server_prompt.updated", lang, prompt=nuovo_prompt[:200]),
            ephemeral=True
        )
    else:
        await interaction.response.send_message(t("server_prompt.removed", lang), ephemeral=True)


def get_server_prompt(guild_id: int | None) -> str:
    """Ritorna il prompt personalizzato del server, o stringa vuota se non impostato."""
    if guild_id is None:
        return ""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT server_prompt FROM server_settings WHERE guild_id = ?",
            (str(guild_id),)
        ).fetchone()
    return row["server_prompt"] if row and row["server_prompt"] else ""




# Utility: impostazioni broadcast server

def get_broadcast_settings(guild_id: int | None) -> dict:
    """Ritorna le impostazioni broadcast del server: enabled e channel_id."""
    if guild_id is None:
        return {"enabled": True, "channel_id": None}
    with get_conn() as conn:
        row = conn.execute(
            "SELECT broadcast_enabled, broadcast_channel_id "
            "FROM server_settings WHERE guild_id = ?",
            (str(guild_id),)
        ).fetchone()
    if not row:
        return {"enabled": True, "channel_id": None}
    return {
        "enabled":    bool(row["broadcast_enabled"]),
        "channel_id": row["broadcast_channel_id"],
    }


def set_broadcast_enabled(guild_id: int, enabled: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO server_settings (guild_id, broadcast_enabled) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET broadcast_enabled = excluded.broadcast_enabled",
            (str(guild_id), int(enabled))
        )
        conn.commit()


def set_broadcast_channel(guild_id: int, channel_id: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO server_settings (guild_id, broadcast_channel_id) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET broadcast_channel_id = excluded.broadcast_channel_id",
            (str(guild_id), channel_id)
        )
        conn.commit()

# /bugreport

class BugReportModal(discord.ui.Modal, title="🐛 Bug Report - purpleGPT"):
    def __init__(self, lang: str = DEFAULT_LANG):
        super().__init__()
        self.descrizione = discord.ui.TextInput(
            label=t("bugreport.modal.description.label",       lang),
            style=discord.TextStyle.paragraph,
            placeholder=t("bugreport.modal.description.placeholder", lang),
            required=True,
            max_length=1000
        )
        self.riproduzione = discord.ui.TextInput(
            label=t("bugreport.modal.steps.label",             lang),
            style=discord.TextStyle.paragraph,
            placeholder=t("bugreport.modal.steps.placeholder", lang),
            required=True,
            max_length=500
        )
        self.comando = discord.ui.TextInput(
            label=t("bugreport.modal.command.label",           lang),
            style=discord.TextStyle.short,
            placeholder=t("bugreport.modal.command.placeholder", lang),
            required=False,
            max_length=100
        )
        self.add_item(self.descrizione)
        self.add_item(self.riproduzione)
        self.add_item(self.comando)

    async def on_submit(self, interaction: discord.Interaction):
        uid      = str(interaction.user.id)
        username = interaction.user.name
        guild    = interaction.guild.name if interaction.guild else "DM"
        canale   = f"#{interaction.channel.name}" if interaction.guild else "DM"

        # Embed da inviare al webhook
        embed = discord.Embed(
            title="🐛 Nuovo Bug Report",
            color=0xFF4444,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="👤 Utente",         value=f"{username} (`{uid}`)",           inline=True)
        embed.add_field(name="🌐 Server",         value=f"{guild} - {canale}",             inline=True)
        embed.add_field(name="🔧 Comando",        value=self.comando.value or "*Non specificato*", inline=True)
        embed.add_field(name="📝 Descrizione",    value=self.descrizione.value,            inline=False)
        embed.add_field(name="🔁 Riproduzione",   value=self.riproduzione.value,           inline=False)
        embed.set_footer(text="purpleGPT Beta - Bug Tracker")

        # Invia al webhook se configurato
        if BUG_WEBHOOK_URL:
            try:
                webhook = discord.Webhook.from_url(BUG_WEBHOOK_URL, session=await get_session())
                await webhook.send(embed=embed, username="purpleGPT Bug Tracker")
            except Exception as e:
                log.warning(f"[/bugreport] Errore webhook: {e}")

        uid  = str(interaction.user.id)
        lang = get_lang(uid, settings_manager.get_settings(uid))
        await interaction.response.send_message(t("bugreport.success", lang), ephemeral=True)


@bot.tree.command(name="bugreport", description="🧪 Report a bug or issue - purpleGPT is in beta!")
async def bugreport_cmd(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)
    cd_ok, remaining = quota_manager.check_cooldown(uid, "bugreport")
    if not cd_ok:
        await interaction.response.send_message(t("cooldown.bugreport", lang, remaining=remaining), ephemeral=True)
        return
    quota_manager.set_cooldown(uid, "bugreport")
    await interaction.response.send_modal(BugReportModal(lang))



# /broadcast (server admin)

def _broadcast_embed(guild: discord.Guild, settings: dict, lang: str) -> discord.Embed:
    """Costruisce l'embed /broadcast con lo stato attuale delle impostazioni."""
    embed = discord.Embed(
        title=t("broadcast_cmd.embed.title", lang),
        description=t("broadcast_cmd.embed.description", lang),
        color=0x8000FF
    )
    status = t("broadcast_cmd.field.status.enabled", lang) if settings["enabled"]              else t("broadcast_cmd.field.status.disabled", lang)
    embed.add_field(name=t("broadcast_cmd.field.status", lang), value=status, inline=True)

    if settings["channel_id"]:
        ch = guild.get_channel(int(settings["channel_id"]))
        ch_value = ch.mention if ch else f"<#{settings['channel_id']}>"
    else:
        ch_value = t("broadcast_cmd.field.channel.none", lang)
    embed.add_field(name=t("broadcast_cmd.field.channel", lang), value=ch_value, inline=True)
    embed.set_footer(text=t("broadcast_cmd.footer", lang, guild=guild.name))
    return embed


class BroadcastChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: int, lang: str):
        self.guild_id = guild_id
        self.lang     = lang
        super().__init__(
            placeholder=t("broadcast_cmd.select.channel.placeholder", lang),
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        channel  = self.values[0]
        set_broadcast_channel(self.guild_id, str(channel.id))
        lang     = self.lang
        settings = get_broadcast_settings(self.guild_id)
        # edit_message sostituisce il messaggio effimero originale con l'embed aggiornato
        await interaction.response.edit_message(
            embed=_broadcast_embed(interaction.guild, settings, lang),
            view=BroadcastView(self.guild_id, settings, lang)
        )
        await interaction.followup.send(
            t("broadcast_cmd.channel.set", lang, channel=channel.mention),
            ephemeral=True
        )


class BroadcastView(discord.ui.View):
    def __init__(self, guild_id: int, settings: dict, lang: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.settings = settings
        self.lang     = lang
        self.add_item(BroadcastChannelSelect(guild_id, lang))

        btn_enable = discord.ui.Button(
            label=t("broadcast_cmd.button.enable", lang),
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=1,
            disabled=settings["enabled"]
        )
        btn_enable.callback = self._cb_enable
        self.add_item(btn_enable)

        btn_disable = discord.ui.Button(
            label=t("broadcast_cmd.button.disable", lang),
            style=discord.ButtonStyle.danger,
            emoji="🔕",
            row=1,
            disabled=not settings["enabled"]
        )
        btn_disable.callback = self._cb_disable
        self.add_item(btn_disable)

    async def _cb_enable(self, interaction: discord.Interaction):
        set_broadcast_enabled(self.guild_id, True)
        self.settings = get_broadcast_settings(self.guild_id)
        await interaction.response.edit_message(
            embed=_broadcast_embed(interaction.guild, self.settings, self.lang),
            view=BroadcastView(self.guild_id, self.settings, self.lang)
        )
        await interaction.followup.send(
            t("broadcast_cmd.enabled.ok", self.lang), ephemeral=True
        )

    async def _cb_disable(self, interaction: discord.Interaction):
        set_broadcast_enabled(self.guild_id, False)
        self.settings = get_broadcast_settings(self.guild_id)
        await interaction.response.edit_message(
            embed=_broadcast_embed(interaction.guild, self.settings, self.lang),
            view=BroadcastView(self.guild_id, self.settings, self.lang)
        )
        await interaction.followup.send(
            t("broadcast_cmd.disabled.ok", self.lang), ephemeral=True
        )


@bot.tree.command(name="broadcast", description="[Admin] Configure update broadcast notifications for this server")
async def broadcast_settings_cmd(interaction: discord.Interaction):
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)

    if interaction.guild is None:
        embed = discord.Embed(
            title=t("broadcast_cmd.dm_title", lang),
            description=t("broadcast_cmd.dm_description", lang),
            color=0x8000FF
        )
        await interaction.response.send_message(embed=embed, view=AddBotView(lang), ephemeral=True)
        return

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            t("broadcast_cmd.no_permission", lang), ephemeral=True
        )
        return

    settings = get_broadcast_settings(interaction.guild_id)
    embed    = _broadcast_embed(interaction.guild, settings, lang)
    view     = BroadcastView(interaction.guild_id, settings, lang)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



# /genserver

# Prompt di sistema per la generazione della struttura server
_GENSERVER_SYSTEM = """
You are a Discord server architect. The user will describe the type of server they want.
You must respond with ONLY a valid JSON object - no markdown, no explanation, no code fences.

The JSON must follow exactly this structure:
{
  "roles": [
    {
      "name": "Moderator",
      "color": "#7c3aed",
      "hoist": true,
      "mentionable": false,
      "permissions": ["view_channel", "send_messages", "manage_messages", "moderate_members"]
    }
  ],
  "categories": [
    {
      "name": "Category Name",
      "channels": [
        {"name": "channel-name", "topic": "Short channel description (max 1024 chars)"},
        {"name": "another-channel", "topic": "Another description"}
      ]
    }
  ]
}

Rules:
- Channel names must be lowercase, no spaces (use hyphens), max 100 chars, no special chars except hyphens
- Category names can have emoji and proper casing, max 100 chars
- Role names can have emoji and proper casing, max 100 chars
- Max 10 roles. If roles are disabled by the user, omit "roles" or return an empty roles array
- Role colors must be hex strings like "#7c3aed"; use tasteful colors that fit the server style
- Role permissions must be lowercase Discord permission names, never raw integers
- Basic member examples: view_channel, send_messages, read_message_history, add_reactions, use_application_commands
- Media/community examples: embed_links, attach_files, use_external_emojis
- Voice examples: connect, speak, stream, use_voice_activation
- Moderation examples: manage_messages, moderate_members, mute_members, deafen_members, move_members
- Admin-like example: administrator, only if the user explicitly wants admin/staff roles; the bot will decide if it is allowed
- Max 10 categories, max 10 channels per category
- Topics are optional but recommended, max 1024 chars
- Create a sensible, realistic structure for the described server
- The response must be ONLY the JSON object, nothing else
"""


_GENSERVER_PERMISSION_ALIASES = {
    "use_vad": "use_voice_activation",
    "voice_activity": "use_voice_activation",
    "manage_permissions": "manage_roles",
    "timeout_members": "moderate_members",
    "manage_emojis": "manage_expressions",
    "manage_emojis_and_stickers": "manage_expressions",
}


def _normalize_permission_name(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return _GENSERVER_PERMISSION_ALIASES.get(normalized, normalized)


def _sanitize_role_permissions(raw_permissions, user_perms: discord.Permissions, bot_perms: discord.Permissions) -> tuple[discord.Permissions, list[str]]:
    perms = discord.Permissions.none()
    names: list[str] = []
    seen: set[str] = set()
    valid_flags_raw = getattr(discord.Permissions, "VALID_FLAGS", {})
    valid_flags = set(valid_flags_raw.keys()) if hasattr(valid_flags_raw, "keys") else set(valid_flags_raw)

    if not isinstance(raw_permissions, list):
        return perms, names

    for raw_perm in raw_permissions[:25]:
        name = _normalize_permission_name(raw_perm)
        if not name or name in seen:
            continue
        if valid_flags and name not in valid_flags:
            continue
        if name == "administrator" and not user_perms.administrator:
            continue
        if not bot_perms.administrator and not bool(getattr(bot_perms, name, False)):
            continue

        try:
            setattr(perms, name, True)
        except Exception:
            continue
        seen.add(name)
        names.append(name)

    return perms, names


def _parse_role_color(value: object) -> discord.Colour:
    raw = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return discord.Colour(int(raw[1:], 16))
    return discord.Colour.default()


def _sanitize_genserver_roles(raw_roles, user_perms: discord.Permissions, bot_perms: discord.Permissions) -> list[dict]:
    if not isinstance(raw_roles, list):
        return []

    valid_roles = []
    for role_data in raw_roles[:10]:
        if not isinstance(role_data, dict):
            continue
        role_name = str(role_data.get("name", "")).strip()[:100]
        if not role_name:
            continue

        perms, permission_names = _sanitize_role_permissions(
            role_data.get("permissions", []),
            user_perms,
            bot_perms
        )
        valid_roles.append({
            "name": role_name,
            "color": str(role_data.get("color", "")).strip(),
            "hoist": bool(role_data.get("hoist", False)),
            "mentionable": bool(role_data.get("mentionable", False)),
            "permissions": permission_names,
            "_permissions_value": perms.value,
        })

    return valid_roles


def _build_genserver_prompt(description: str, include_roles: bool, allow_admin_roles: bool) -> str:
    role_instruction = (
        "Generate useful roles too. Include the top-level \"roles\" array with roles that fit the server style."
        if include_roles
        else "Do NOT generate roles. Omit the top-level \"roles\" array or return \"roles\": []."
    )
    admin_instruction = (
        "The requesting user has Administrator, so admin-like roles may include administrator only when it makes sense."
        if allow_admin_roles
        else "The requesting user does not have Administrator, so do not include administrator in any role."
    )
    return (
        f"{_GENSERVER_SYSTEM}\n\n"
        f"Role generation setting: {role_instruction}\n"
        f"Administrator permission setting: {admin_instruction}\n\n"
        f"Server description: {description[:500]}"
    )


class GenServerConfirmView(discord.ui.View):
    def __init__(self, uid: str, guild_id: int, structure: dict, lang: str):
        super().__init__(timeout=120)
        self.uid       = uid
        self.guild_id  = guild_id
        self.structure = structure
        self.lang      = lang
        self.quota_consumed = False

        btn_confirm = discord.ui.Button(
            label=t("genserver.button.confirm", lang),
            style=discord.ButtonStyle.success,
            row=0
        )
        btn_confirm.callback = self._cb_confirm
        self.add_item(btn_confirm)

        btn_cancel = discord.ui.Button(
            label=t("genserver.button.cancel", lang),
            style=discord.ButtonStyle.danger,
            row=0
        )
        btn_cancel.callback = self._cb_cancel
        self.add_item(btn_cancel)

    async def _cb_confirm(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                t("genserver.not_yours", self.lang), ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content=t("genserver.building", self.lang),
            embed=None, view=None
        )

        guild      = interaction.guild
        roles      = self.structure.get("roles", [])
        categories = self.structure.get("categories", [])
        role_count = 0
        cat_count  = 0
        ch_count   = 0
        errors     = 0

        for role_data in roles:
            role_name = str(role_data.get("name", "")).strip()[:100]
            if not role_name:
                continue
            try:
                perms_value = int(role_data.get("_permissions_value") or 0)
                await guild.create_role(
                    name=role_name,
                    permissions=discord.Permissions(perms_value),
                    colour=_parse_role_color(role_data.get("color", "")),
                    hoist=bool(role_data.get("hoist", False)),
                    mentionable=bool(role_data.get("mentionable", False)),
                    reason="Generated by purpleGPT /genserver"
                )
                role_count += 1
            except Exception as e:
                log.warning(f"[/genserver] Errore creazione ruolo {role_name!r}: {e}")
                errors += 1

        for cat_data in categories:
            cat_name = str(cat_data.get("name", "")).strip()[:100]
            if not cat_name:
                continue
            try:
                category = await guild.create_category(cat_name)
                cat_count += 1
            except Exception as e:
                log.warning(f"[/genserver] Errore creazione categoria {cat_name!r}: {e}")
                errors += 1
                continue

            for ch_data in cat_data.get("channels", []):
                ch_name  = str(ch_data.get("name", "")).strip()[:100]
                ch_topic = str(ch_data.get("topic", "")).strip()[:1024]
                if not ch_name:
                    continue
                try:
                    await guild.create_text_channel(
                        name=ch_name,
                        category=category,
                        topic=ch_topic or None
                    )
                    ch_count += 1
                except Exception as e:
                    log.warning(f"[/genserver] Errore creazione canale {ch_name!r}: {e}")
                    errors += 1

        if errors > 0 and role_count == 0 and cat_count == 0 and ch_count == 0:
            quota_manager.decrement_usage(self.uid, "genserver")
            self.quota_consumed = True
            await interaction.edit_original_response(
                content=t("genserver.error_create", self.lang)
            )
        else:
            # La quota era gia stata prenotata prima della chiamata AI.
            self.quota_consumed = True
            msg = t("genserver.done", self.lang, roles=role_count, categories=cat_count, channels=ch_count)
            if errors:
                msg += f"\n{t('genserver.error_create', self.lang)}"
            await interaction.edit_original_response(content=msg)

        log.info(f"[/genserver] {interaction.user.name} - {role_count} ruoli, {cat_count} categorie, {ch_count} canali, {errors} errori in {guild.name}")

    async def _cb_cancel(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                t("genserver.not_yours", self.lang), ephemeral=True
            )
            return
        quota_manager.decrement_usage(self.uid, "genserver")
        self.quota_consumed = True
        await interaction.response.edit_message(
            content=t("genserver.cancelled", self.lang),
            embed=None, view=None
        )

    async def on_timeout(self):
        if not self.quota_consumed:
            quota_manager.decrement_usage(self.uid, "genserver")
            self.quota_consumed = True


async def _show_genserver_progress(interaction: discord.Interaction, lang: str) -> None:
    """Mostra il messaggio di progresso sia da slash command sia da bottone."""
    if interaction.response.is_done():
        await interaction.edit_original_response(content=t("genserver.progress", lang), embed=None, view=None)
    elif interaction.type == discord.InteractionType.component:
        await interaction.response.edit_message(content=t("genserver.progress", lang), embed=None, view=None)
    else:
        await interaction.response.defer(thinking=True, ephemeral=True)
        await interaction.edit_original_response(content=t("genserver.progress", lang))


async def _send_genserver_message(
    interaction: discord.Interaction,
    content: str,
    *,
    ephemeral: bool = True,
) -> None:
    """Invia o aggiorna il messaggio corrente del flusso /genserver."""
    if interaction.response.is_done():
        await interaction.edit_original_response(content=content, embed=None, view=None)
    elif interaction.type == discord.InteractionType.component:
        await interaction.response.edit_message(content=content, embed=None, view=None)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)


async def _run_genserver_generation(
    interaction: discord.Interaction,
    uid: str,
    lang: str,
    descrizione: str,
    roles: bool,
) -> None:
    """Esegue quota, chiamata AI, sanitizzazione e anteprima finale di /genserver."""
    # Controllo quota mensile: /genserver e limitato per piano (Free=1, Starter=1, Pro=illimitato)
    ok_q, used, limit = quota_manager.check_and_increment(uid, "genserver")
    if not ok_q:
        plan = quota_manager.get_plan(uid)
        msg  = t("quota.genserver.exceeded", lang, limit=limit, plan=plan)
        if plan == "free":
            msg += f"\n\n{t('quota.hint.upgrade', lang)}"
        await _send_genserver_message(interaction, msg)
        return

    await _show_genserver_progress(interaction, lang)

    # Chiama Gemini per generare la struttura
    try:
        result = await asyncio.to_thread(
            client.models.generate_content,
            model=CHAT_MODEL,
            contents=_build_genserver_prompt(
                descrizione,
                include_roles=roles,
                allow_admin_roles=interaction.user.guild_permissions.administrator
            ),
            config=types.GenerateContentConfig(
                temperature=0.7,
                automatic_function_calling=NO_AFC,
            )
        )
        raw = (result.text or "").strip()
    except Exception as e:
        quota_manager.decrement_usage(uid, "genserver")
        log.error(f"[/genserver] Errore Gemini: {e}", exc_info=True)
        await interaction.edit_original_response(content=t("error.generic", lang), embed=None, view=None)
        return

    # Pulizia: rimuovi eventuali backtick/markdown che Gemini aggiunge
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw.strip())

    # Parsing del JSON
    try:
        structure = json.loads(raw)
    except Exception:
        quota_manager.decrement_usage(uid, "genserver")
        log.warning(f"[/genserver] JSON non valido da Gemini: {raw[:200]!r}")
        await interaction.edit_original_response(content=t("genserver.error_parse", lang), embed=None, view=None)
        return

    # Valida la struttura
    categories = structure.get("categories", [])
    if not categories or not isinstance(categories, list):
        quota_manager.decrement_usage(uid, "genserver")
        await interaction.edit_original_response(content=t("genserver.error_empty", lang), embed=None, view=None)
        return

    # Filtra ruoli, categorie e canali malformati.
    valid_roles = _sanitize_genserver_roles(
        structure.get("roles", []) if roles else [],
        interaction.user.guild_permissions,
        interaction.guild.me.guild_permissions
    )
    structure["roles"] = valid_roles

    valid_categories = []
    for cat in categories[:10]:
        if not isinstance(cat, dict) or not cat.get("name"):
            continue
        channels = [
            ch for ch in cat.get("channels", [])[:10]
            if isinstance(ch, dict) and ch.get("name")
        ]
        valid_categories.append({
            "name":     str(cat["name"])[:100],
            "channels": [{"name": str(c["name"])[:100], "topic": str(c.get("topic", ""))[:1024]} for c in channels]
        })
    structure["categories"] = valid_categories

    if not valid_categories:
        quota_manager.decrement_usage(uid, "genserver")
        await interaction.edit_original_response(content=t("genserver.error_empty", lang), embed=None, view=None)
        return

    # Costruisci embed di anteprima
    embed = discord.Embed(
        title=t("genserver.confirm.title", lang),
        description=t("genserver.confirm.description", lang),
        color=0x8000FF
    )
    if valid_roles:
        role_lines = []
        for role in valid_roles:
            perms = role.get("permissions") or []
            perm_text = ", ".join(perms[:5]) if perms else "base"
            role_lines.append(f"- @{role['name']} - {perm_text}")
        embed.add_field(
            name=t("genserver.confirm.roles", lang),
            value="\n".join(role_lines)[:1024],
            inline=False
        )
    for cat in valid_categories:
        ch_list = "\n".join(f"- #{c['name']}" + (f" - {c['topic'][:60]}" if c.get("topic") else "") for c in cat["channels"])
        embed.add_field(
            name=f"📁 {cat['name']}",
            value=ch_list if ch_list else "*nessun canale*",
            inline=False
        )
    embed.set_footer(text=t("genserver.confirm.footer", lang))

    history_manager.save_user_activity(
        uid,
        "/genserver",
        f"description={descrizione}; roles={roles}",
        "preview",
        guild_id=interaction.guild_id,
        channel_id=interaction.channel_id,
    )

    view = GenServerConfirmView(uid, interaction.guild_id, structure, lang)
    await interaction.edit_original_response(content=None, embed=embed, view=view)


class GenServerPreflightView(discord.ui.View):
    def __init__(self, uid: str, description: str, roles: bool, lang: str):
        super().__init__(timeout=120)
        self.uid = uid
        self.description = description
        self.roles = roles
        self.lang = lang

        btn_continue = discord.ui.Button(
            label=t("genserver.preflight.continue", lang),
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=0
        )
        btn_continue.callback = self._cb_continue
        self.add_item(btn_continue)

        btn_cancel = discord.ui.Button(
            label=t("genserver.preflight.cancel", lang),
            style=discord.ButtonStyle.secondary,
            emoji="❌",
            row=0
        )
        btn_cancel.callback = self._cb_cancel
        self.add_item(btn_cancel)

    async def _cb_continue(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                t("genserver.not_yours", self.lang), ephemeral=True
            )
            return
        await _run_genserver_generation(
            interaction,
            self.uid,
            self.lang,
            self.description,
            self.roles
        )

    async def _cb_cancel(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                t("genserver.not_yours", self.lang), ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content=t("genserver.cancelled", self.lang),
            embed=None,
            view=None
        )


@bot.tree.command(name="genserver", description="[Admin] Generate a full Discord server structure with AI")
@app_commands.describe(
    description="Describe the server you want to create (e.g. 'university study server')",
    roles="Also generate AI roles with permissions"
)
async def genserver_cmd(
    interaction: discord.Interaction,
    description: str,
    roles: bool = True
):
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)

    # Risposta di ripiego in DM
    if interaction.guild is None:
        embed = discord.Embed(
            title=t("genserver.dm_title", lang),
            description=t("genserver.dm_description", lang),
            color=0x8000FF
        )
        await interaction.response.send_message(embed=embed, view=AddBotView(lang), ephemeral=True)
        return

    # Verifica permessi utente: serve Gestisci Server per generare una struttura completa.
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            t("genserver.no_permission", lang), ephemeral=True
        )
        return

    # Se si generano ruoli, anche l'utente deve poter gestire i ruoli.
    if roles and not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            t("genserver.no_roles_permission", lang), ephemeral=True
        )
        return

    # Verifica permessi bot (manage_channels)
    if not interaction.guild.me.guild_permissions.manage_channels:
        await interaction.response.send_message(
            t("genserver.bot_no_permission", lang), ephemeral=True
        )
        return

    # Se si generano ruoli, il bot deve poterli creare.
    if roles and not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            t("genserver.bot_no_roles_permission", lang), ephemeral=True
        )
        return

    if roles:
        embed = discord.Embed(
            title=t("genserver.preflight.title", lang),
            description=t("genserver.preflight.description", lang),
            color=0xfbbf24
        )
        await interaction.response.send_message(
            embed=embed,
            view=GenServerPreflightView(uid, description, roles, lang),
            ephemeral=True
        )
        return

    await _run_genserver_generation(interaction, uid, lang, description, roles)


# Avvio

# /vote

TOP_GG_URL = os.getenv("TOP_GG_URL", "https://top.gg/bot/YOUR_BOT_ID/vote")


class VoteView(discord.ui.View):
    def __init__(self, uid: str, already_voted: bool, lang: str = DEFAULT_LANG):
        super().__init__(timeout=300)
        self.uid           = uid
        self.already_voted = already_voted
        self.lang          = lang

        # Bottone vota su top.gg (link diretto)
        self.add_item(discord.ui.Button(
            label=t("vote.button.vote", lang),
            style=discord.ButtonStyle.link,
            url=TOP_GG_URL,
            emoji="🗳️",
            row=0
        ))

        # Bottone "Ho votato!" - aggiunto dinamicamente per supportare i18n
        self._btn_voted = discord.ui.Button(
            label=t("vote.button.voted", lang),
            style=discord.ButtonStyle.primary,
            emoji="🟣",
            row=1
        )
        self._btn_voted.callback = self._cb_voted
        self.add_item(self._btn_voted)

    async def _cb_voted(self, interaction: discord.Interaction):
        button = self._btn_voted
        lang = self.lang
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(t("vote.button.not_yours", lang), ephemeral=True)
            return

        # Controlla se l'utente ha gia raggiunto il limite giornaliero di riscatti
        claimed = quota_manager.get_votes_claimed_today(self.uid)
        max_claims = quota_manager.VOTE_BONUS["max_votes_per_day"]
        if claimed >= max_claims:
            await interaction.response.send_message(
                t("vote.bonus.max_reached", lang),
                ephemeral=True
            )
            return

        button.disabled = True
        button.label    = t("vote.button.verifying", lang)
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(t("vote.waiting", lang), ephemeral=True)

        await asyncio.sleep(60)

        # Assegna il bonus voto giornaliero
        ok, err = quota_manager.claim_vote_bonus(self.uid)

        try:
            await interaction.edit_original_response(
                content=t("vote.confirmed", lang),
                embed=None,
                view=None
            )
        except Exception:
            pass

        if ok:
            img_bonus     = quota_manager.VOTE_BONUS["image_bonus"]
            compose_bonus = quota_manager.VOTE_BONUS["compose_bonus"]
            await interaction.followup.send(
                t("vote.bonus.granted", lang,
                  img=img_bonus, music=compose_bonus),
                ephemeral=True
            )
        else:
            # Caso limite: il riscatto e fallito tra il controllo e l'assegnazione (race condition)
            await interaction.followup.send(t("vote.thanks", lang), ephemeral=True)


@bot.tree.command(name="vote", description="Vote for purpleGPT on top.gg and get a daily image bonus!")
async def vote_cmd(interaction: discord.Interaction):
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)

    embed = discord.Embed(
        title=t("vote.embed.title", lang),
        description=t("vote.embed.description", lang),
        color=0x8000FF
    )

    await interaction.response.send_message(
        embed=embed,
        view=VoteView(uid, False, lang),
        ephemeral=True
    )


# /premium

@bot.tree.command(name="premium", description="View your current plan and upgrade options (Starter includes 7-day free trial)")
async def premium_cmd(interaction: discord.Interaction):
    """
    Mostra i piani disponibili con i pulsanti di pagamento Stripe.
    Starter include 7 giorni di prova configurati su Stripe; Pro non ha trial.
    """
    uid      = str(interaction.user.id)
    user_cfg = settings_manager.get_settings(uid)
    lang     = get_lang(uid, user_cfg)

    current_plan = quota_manager.get_plan(uid)
    plan_info    = quota_manager.get_plan_info(uid)

    # Costruisce la riga "piano attuale"
    if current_plan == "free":
        current_line = t("premium.current.free", lang)
        trial_hint   = None
    else:
        # Recupera la data di scadenza da mostrare all'utente
        expires_label = "-"
        if plan_info["expires_at"]:
            try:
                exp = datetime.fromisoformat(plan_info["expires_at"])
                expires_label = exp.strftime("%Y-%m-%d")
            except Exception:
                expires_label = plan_info["expires_at"][:10]

        # Sceglie la stringa corretta in base allo stato trial
        if plan_info["is_trial"]:
            key = f"premium.current.{current_plan}_trial"
            trial_hint = t("premium.trial.hint", lang)
        else:
            key = f"premium.current.{current_plan}"
            trial_hint = None
        current_line = t(key, lang, expires=expires_label)

    embed = discord.Embed(
        title=t("premium.cmd.title", lang),
        description=t("premium.cmd.desc", lang),
        color=0x8000FF
    )
    embed.add_field(
        name=t("premium.current.title", lang),
        value=current_line + (f"\n-# {trial_hint}" if trial_hint else ""),
        inline=False
    )
    embed.add_field(
        name=t("premium.plan.free.name", lang),
        value=t("premium.plan.free.benefits", lang),
        inline=False
    )
    embed.add_field(
        name=t("premium.plan.starter.name", lang),
        value=t("premium.plan.starter.benefits", lang),
        inline=False
    )
    embed.add_field(
        name=t("premium.plan.pro.name", lang),
        value=t("premium.plan.pro.benefits", lang),
        inline=False
    )
    embed.set_footer(text=t("premium.footer", lang))

    # Costruisce i pulsanti azione
    view = discord.ui.View(timeout=300)

    if current_plan == "free":
        # Mostra entrambi i pulsanti di passaggio piano agli utenti free
        view.add_item(discord.ui.Button(
            label=t("premium.btn.starter", lang),
            style=discord.ButtonStyle.link,
            url=quota_manager.PAYMENT_LINKS["starter"],
            emoji="⚡"
        ))
        view.add_item(discord.ui.Button(
            label=t("premium.btn.pro", lang),
            style=discord.ButtonStyle.link,
            url=quota_manager.PAYMENT_LINKS["pro"],
            emoji="🚀"
        ))
    elif current_plan == "starter":
        # Propone il passaggio al piano Pro
        view.add_item(discord.ui.Button(
            label=t("premium.btn.pro", lang),
            style=discord.ButtonStyle.link,
            url=quota_manager.PAYMENT_LINKS["pro"],
            emoji="🚀"
        ))
    # Utenti pro: nessun pulsante di passaggio piano, sono gia al piano massimo.

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


bot.run(TOKEN)
