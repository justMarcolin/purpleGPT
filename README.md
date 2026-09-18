# purpleGPT

> Progetto candidato al **Premio G.F. Marilli** di **Hackersgen**.

purpleGPT è un chatbot avanzato per Discord pensato per rendere l'intelligenza artificiale più accessibile, immediata e utile dentro gli spazi digitali che studenti, sviluppatori e community frequentano ogni giorno.

Il progetto nasce da **jLabs**, un team di studenti di terza (e adesso quarta) superiore nato tra i banchi di scuola con un obiettivo concreto: trasformare Discord da semplice piattaforma di chat a un ambiente di lavoro e studio in cui chiedere chiarimenti, generare idee, riassumere informazioni complesse, analizzare immagini e comporre musica con l'AI.

Questa repository contiene il **codice sorgente completo** del bot Discord e della relativa dashboard di amministrazione web, predisposto e documentato per la valutazione del concorso **Hackersgen**.

---

## Indice / Table of Contents
- [Italiano (ITA)](#italiano-ita)
  - [Cosa fa purpleGPT](#cosa-fa-purplegpt)
  - [Architettura e Stack Tecnico](#architettura-e-stack-tecnico)
  - [Struttura della Repository](#struttura-della-repository)
  - [Guida all'Installazione e Avvio](#guida-allinstallazione-e-avvio)
  - [Competenze Acquisite](#competenze-acquisite)
  - [Uso Costruttivo dell'AI](#uso-costruttivo-dellai)
- [English (ENG)](#english-eng)
  - [What purpleGPT Does](#what-purplegpt-does)
  - [Architecture and Technical Stack](#architecture-and-technical-stack)
  - [Repository Structure](#repository-structure)
  - [Quickstart Guide](#quickstart-guide)
  - [Skills Acquired](#skills-acquired)
  - [Constructive Use of AI](#constructive-use-of-ai)

---

# Italiano (ITA)

## Cosa fa purpleGPT

purpleGPT porta un assistente multimodale direttamente nei server Discord. Gli utenti possono interagire tramite comandi slash (`/`) o menzioni dirette per:

- **Assistenza allo studio e risposte immediate**: spiegazioni su programmazione, scienze, testi scolastici e quesiti tecnici.
- **Multimodalità (Visione)**: analisi, interpretazione e spiegazione di immagini, schemi, screenshot e grafici allegati.
- **Generazione e manipolazione multimediale**: creazione di tracce musicali d'atmosfera con Google Lyria e generazione video con transizioni.
- **Supporto community e server**: generazione automatica della struttura di un server Discord (`/genserver`), canali tematici, ruoli e permessi.
- **Gestione quote e piani**: sistema a livelli (Free, Starter, Pro) con tracciamento giornaliero e mensile atomico su SQLite.
- **Internazionalizzazione nativa**: supporto multilingua (Italiano, Inglese, Spagnolo, Portoghese, Francese, Tedesco) con rilevamento automatico della lingua dell'utente.

## Architettura e Stack Tecnico

Il sistema è strutturato in modo modulare per garantire affidabilità, separazione delle responsabilità e scalabilità:

### Bot Discord (`main.py`)
- **Python 3.11+** con **discord.py**: gestione asincrona degli eventi, comandi slash interattivi, bottoni, modali e viste UI.
- **Google GenAI SDK (Vertex AI)**: integrazione con i modelli `gemini-3.8-flash` per chat/visione e `lyria` per la generazione musicale.
- **Server HTTP interno (aiohttp)**: API locale protetta da Bearer token per consentire alla dashboard di eseguire comunicazioni sicure e broadcast globali senza esporre porte aperte all'esterno.
- **Elaborazione Multimediale**: integrazione FFmpeg per il trim audio ad alta precisione e montaggio video con loop di immagini.

### Moduli di Supporto (`bot_managers/`)
- `db.py`: connessione centralizzata thread-safe a SQLite con schema automatico e supporto WAL.
- `quota_manager.py`: calcolo e applicazione dei limiti di utilizzo giornalieri e mensili, gestione cooldown anti-spam e integrazione checkout.
- `history_manager.py`: persistenza e recupero della cronologia conversazionale per utente per mantenere il contesto delle chat.
- `settings_manager.py`: memorizzazione delle preferenze utente (es. lingua personalizzata, modelli preferiti).
- `strings.py`: dizionario localizzato con centinaia di stringhe e messaggi tradotti per tutte le lingue supportate.
- `tos_manager.py`: gestione del consenso esplicito ai Termini di Servizio al primo utilizzo del bot.

### Dashboard di Amministrazione Web (`dashboard.py`)
- **Flask**: web application per monitoraggio e controllo del bot.
- **Statistiche in tempo reale**: utenti attivi, server raggiunti, interazioni giornaliere/settimanali e distribuzione comandi.
- **Gestione Piani**: abilitazione, estensione e gestione manuale delle licenze con scadenze temporali.
- **Broadcast System**: invio di annunci formattati verso tutti i canali annunci dei server configurati.
- **Interfaccia moderna**: design dark-mode reattivo con glassmorphism e tipografia curata.

---

## Struttura della Repository

```text
├── bot_managers/             # Moduli architetturali del bot
│   ├── db.py                 # Gestione database SQLite e migrazioni
│   ├── history_manager.py    # Memoria e contesto conversazioni
│   ├── quota_manager.py      # Gestione limiti, quote e piani
│   ├── settings_manager.py   # Preferenze e impostazioni utente
│   ├── strings.py            # Dizionario i18n multilingua
│   └── tos_manager.py        # Gestione Termini di Servizio
├── .env.example              # Modello delle variabili d'ambiente necessarie
├── .gitignore                # Regole di esclusione file sensibili e temporanei
├── dashboard.py              # Dashboard web Flask per amministrazione
├── LICENSE                   # Licenza CC BY-NC 4.0
├── main.py                   # Entrypoint principale del bot Discord
├── NOTICE.md                 # Nota informativa sulla sicurezza e sul concorso
├── README.md                 # Documentazione completa del progetto
├── requirements.txt          # Dipendenze Python del progetto
└── transition.webm           # Asset video per le transizioni multimediali
```

---

## Guida all'Installazione e Avvio

### 1. Prerequisiti
- **Python 3.11** o superiore
- **FFmpeg** installato e presente nel PATH di sistema (necessario per comandi multimediali audio/video)
- Un account **Google Cloud** con un progetto abilitato alle API di **Vertex AI** (per i test in locale è sufficiente autenticarsi con ADC: `gcloud auth application-default login`)
- Un'applicazione bot creata sul **Discord Developer Portal** con i **Privileged Gateway Intents** abilitati nella sezione *Bot* (*Message Content Intent* e *Server Members Intent*, necessari per il corretto funzionamento di `discord.py`)

### 2. Configurazione dell'Ambiente

Clonare la repository ed entrare nella cartella di progetto:
```bash
git clone https://github.com/justMarcolin/purpleGPT.git
cd purpleGPT
```

Creare e attivare un ambiente virtuale:
```bash
# Su Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Su Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Installare le dipendenze:
```bash
pip install -r requirements.txt
```

### 3. Variabili d'Ambiente

Creare il file `.env` a partire dal modello di esempio:
```bash
cp .env.example .env
```

Compilare i parametri all'interno di `.env` (ID progetto GCP, token bot Discord, credenziali dashboard).

### 4. Avvio dei Servizi

**Avvio del bot Discord:**
```bash
python main.py
```

**Avvio della Dashboard Web (in un terminale separato):**
```bash
python dashboard.py
```
La dashboard sarà accessibile localmente su `http://127.0.0.1:5000`.


> **Nota per il testing locale e avvio da zero (Cold Start):**
> - **Inizializzazione automatica Database**: Il database SQLite (`purplegpt.db`) e l'intero schema (tabelle utenti, quote, piani, cooldown e impostazioni) vengono inizializzati automaticamente in modalità WAL al primo avvio, sia che venga eseguito prima `main.py` o `dashboard.py`.
> - **Cookie di sessione HTTPS (`Secure`)**: Per rispettare le best practice di sicurezza web in produzione (dietro reverse proxy Nginx con certificato SSL), la dashboard invia cookie di autenticazione con il flag `Secure`. Se si desidera testare il login in un ambiente locale non-HTTPS (`http://127.0.0.1:5000`), è sufficiente impostare `SESSION_COOKIE_SECURE='false'` nel file `.env`.
> - **Integrazione IPC in tempo reale**: La dashboard e il bot sono progettati come servizi cooperanti. Per visualizzare le statistiche dei server in tempo reale e testare i broadcast, avviare sia `main.py` che `dashboard.py` con lo stesso token `BROADCAST_SECRET`.

---

## Competenze Acquisite

Durante lo sviluppo di purpleGPT abbiamo consolidato competenze tecniche e metodologiche che vanno oltre la semplice codifica:

- **Progettazione Asincrona**: gestione della concorrenza con `asyncio` e `aiohttp` per prevenire blocchi durante chiamate ad API lente.
- **Ingegneria dei Prompt e Multimodalità**: integrazione efficace delle API Vertex AI con parametri di temperatura, system instruction e streaming.
- **Sicurezza e Isolamento**: separazione rigorosa di credenziali, database di produzione e chiavi d'ambiente; autenticazione sicura su dashboard Flask e API interna con token Bearer.
- **Database e Persistenza**: modellazione di tabelle SQLite per cronologia, quote e piani con transazioni atomiche.
- **Lavoro di Squadra e Problem Solving**: suddivisione dei ruoli all'interno del team jLabs, testing e debugging collaborativo.

## Uso Costruttivo dell'AI

Nel pieno spirito del concorso Hackersgen, l'intelligenza artificiale non è stata utilizzata come scorciatoia, ma come **strumento di accelerazione dell'apprendimento**:
- per esplorare la documentazione delle API Vertex AI e Discord;
- per effettuare code review e individuare casi limite (*edge cases*);
- per confrontare pattern architetturali per la gestione delle quote e della persistenza.

L'architettura, la logica di business, le scelte implementative e la piena responsabilità del codice appartengono interamente al team di studenti.

---

# English (ENG)

## What purpleGPT Does

purpleGPT brings a multimodal AI assistant directly into Discord servers. Users can interact via slash commands (`/`) or direct mentions to:

- **Study Support & Instant Answers**: Explanations on coding, science, school subjects and technical topics.
- **Vision & Multimodality**: Analyze, explain and discuss attached images, diagrams, screenshots and charts.
- **Multimedia Composition**: Generate background ambient music tracks using Google Lyria and produce videos with transitions.
- **Server & Community Tooling**: Automatically generate complete Discord server structures (`/genserver`), channels, roles and permissions.
- **Quotas & Subscription Tiers**: Multi-tier architecture (Free, Starter, Pro) with atomic daily and monthly quota tracking in SQLite.
- **Native Localization**: Full multi-language support (Italian, English, Spanish, Portuguese, French, German) with user language auto-detection.

## Architecture and Technical Stack

### Discord Bot (`main.py`)
- **Python 3.11+** & **discord.py**: Asynchronous event loop, interactive slash commands, buttons, modals, and views.
- **Google GenAI SDK (Vertex AI)**: Integrated with `gemini-3.8-flash` for chat/vision and `lyria` for music generation.
- **Internal HTTP Server (aiohttp)**: Local REST API protected by Bearer token authentication, allowing the dashboard to communicate with the bot securely without public network exposure.
- **Multimedia Engine**: High-precision FFmpeg integration for audio trimming and image-to-video rendering.

### Support Managers (`bot_managers/`)
- `db.py`: Thread-safe SQLite connection manager with automated migrations and WAL mode.
- `quota_manager.py`: Usage limits calculation, anti-spam cooldowns, and subscription tiers.
- `history_manager.py`: Multi-turn conversational history management per user.
- `settings_manager.py`: User configuration and preference persistence.
- `strings.py`: Comprehensive localized string catalog for all supported languages.
- `tos_manager.py`: Explicit Terms of Service consent tracking upon first user interaction.

### Web Administration Dashboard (`dashboard.py`)
- **Flask**: Web dashboard for real-time monitoring and administrative tasks.
- **Metrics & Telemetry**: Active users, server count, daily command breakdown, and weekly trends.
- **Subscription Management**: Manual grant, extension, and tracking of user tiers.
- **Broadcast System**: Formatted global announcements dispatched to all configured server news channels.

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- FFmpeg installed in system PATH
- Google Cloud project with **Vertex AI API** enabled (for local testing, authenticating with ADC via `gcloud auth application-default login` is sufficient)
- Discord Bot application created on the **Discord Developer Portal** with **Privileged Gateway Intents** toggled ON under the *Bot* tab (*Message Content Intent* and *Server Members Intent*)

### 2. Setup
```bash
git clone https://github.com/justMarcolin/purpleGPT.git
cd purpleGPT

python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Fill in your `.env` file with your credentials.

### 3. Run
```bash
# Terminal 1: Run the Discord Bot
python main.py

# Terminal 2: Run the Dashboard
python dashboard.py
```
Open `http://127.0.0.1:5000` to view the admin dashboard.

> **Local Testing Notice:**
> - **Automatic Database Initialization**: The SQLite database (`purplegpt.db`) and all required tables (users, quotas, tiers, cooldowns, and settings) are initialized automatically in WAL mode on first launch, regardless of whether `main.py` or `dashboard.py` is started first.
> - **HTTPS Session Cookies (`Secure`)**: To adhere to production web security best practices (behind an Nginx reverse proxy with SSL), the dashboard issues authentication cookies with the `Secure` attribute. If testing the dashboard login in a local HTTP environment (`http://127.0.0.1:5000`), set `SESSION_COOKIE_SECURE='false'` in your `.env` file.
> - **Real-time IPC Integration**: The dashboard and the bot are designed as cooperating microservices. To inspect real-time server statistics and test announcements, ensure both `main.py` and `dashboard.py` are running with matching `BROADCAST_SECRET` tokens.

---

## Skills Acquired
- **Asynchronous Python**: Non-blocking concurrency with `asyncio` and `aiohttp`.
- **AI & Multimodal API Integration**: Vertex AI prompt engineering, temperature tuning, and media handling.
- **System Security & Isolation**: Environment variable management, token protection, and private internal server design.
- **Database Architecture**: Atomic queries, schema normalization, and persistent state management.
- **Team Collaboration**: High-school student teamwork, modular architecture, and project presentation.

## Constructive Use of AI
AI was used as a learning companion and development accelerator — exploring documentation, investigating edge cases, and assisting with code review. All system decisions, architecture, integration, and final code responsibility remain entirely with the student team.
