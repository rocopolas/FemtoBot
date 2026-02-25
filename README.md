
![FemtoBot Logo](https://files.catbox.moe/zhkn08.jpg)

A smart personal assistant designed for small local models, recommended for GPUs with at least 8GB of VRAM. Runs locally using [Ollama](https://ollama.ai) or [LM Studio](https://lmstudio.ai/). Available as a Telegram bot and TUI interface.

## ✨ Features

- 💬 **Local LLM chat** - No external API dependencies
- 🧠 **Vector Memory (RAG)** - Remembers facts and conversations using embeddings
- 📚 **Document Store** - Indexed PDF/TXT search for context awareness
- 📷 **Image analysis** - Describe and understand images with vision model
- 🎙️ **Audio transcription** - Convert voice messages to text with Whisper
- 🎥 **YouTube summaries** - Send a link and get a summary
- 🐦 **Twitter/X downloader** - Download videos/images directly
- 🔍 **Web search** - Brave Search integration
- 🖼️ **Image search** - Search for images on the web
- 📄 **Document reading** - Analyze and chat with PDF or text files
- 📧 **Email digest** - Read and summarize emails from Gmail
- 🧠 **Deep Research** - Perform iterative research on a topic
- ⏰ **Reminders** - Schedule cron tasks that notify you in chat
- 💡 **Smart lights** - Control WIZ lights via chat
- 🧮 **Math solver** - Solve complex equations and symbolic math problems
- 📤 **File upload** - Upload files to Catbox.moe

**Catbox.moe**
![FemtoBot in action](https://files.catbox.moe/rpkd1y.jpg)
**Math solver**
![FemtoBot in action](https://files.catbox.moe/ltdliq.jpg)
**Youtube summary**
![FemtoBot in action](https://files.catbox.moe/c9b2ct.jpg)


## 🚀 Installation & Setup

FemtoBot is designed to be easy to install and runs entirely locally. You can use the automated setup script or install it manually.

### ⚡ Automated Installation

This is the fastest way to get started. Just copy and run this command:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/rocopolas/FemtoBot/main/install.sh)"
```

This single command will:
1.  Download the installation script.
2.  Clone the repository automatically (if not present).
3.  Install all system dependnecies (Python, FFmpeg, etc).
4.  Set up the environment completely.

Alternatively, you can clone manually:
```bash
git clone https://github.com/rocopolas/FemtoBot.git
cd FemtoBot
chmod +x install.sh
./install.sh
```

### 📋 Prerequisites

- **Python 3.12+** (Will be installed automatically if missing on Ubuntu/Debian)
- **Git**
- **[Ollama](https://ollama.ai)** (Script will attempt to install)
- **FFmpeg**

---

### ⚙️ Initial Configuration

After installation, run the setup command to initialize your environment:

```bash
femtobot setup
```

This interactive command will:
1.  **Configure Environment**: Prompt you for your Telegram Token, Authorized Users, and other settings to create your `.env` file.
2.  **Select Features**: Choose which optional features to enable (lights, email, YouTube, etc.).
3.  **Auto-detect Language**: Detect your system locale and set Whisper language automatically.
4.  **Download Models**: Pull the necessary Ollama models defined in `config.yaml`.
5.  **Create Data Files**: Initialize default instructions and memory files.

*Note: Ensure [Ollama](https://ollama.com/) is running (`ollama serve`) before running setup.*

### 🏥 System Check

After setup, it is highly recommended to run the doctor command to verify your installation:

```bash
femtobot doctor
```

This will check for:
- Correct Python version
- Virtual environment activation (if applicable)
- Configuration file validity
- Ollama connectivity and model availability

---

### 🧙 Configuration Wizard

For a more visual and interactive way to manage your settings after the initial setup, use the built-in wizard:

```bash
femtobot wizard
```

This tool provides a terminal-based menu system to:
- **Toggle Features**: Enable or disable specific utility services (WIZ, Gmail, etc.).
- **Update Credentials**: Securely update API keys and tokens.
- **Model Selection**: Switch between different Ollama models for chat and vision.


### 🖥️ CLI Commands

Once installed, you can manage FemtoBot using the CLI:

```bash
# Core Commands
femtobot start      # Start the bot daemon
femtobot stop       # Stop the daemon
femtobot status     # Check bot and Ollama connection
femtobot logs -f    # View real-time logs

# Tools
femtobot tui        # Open the Terminal User Interface
femtobot config     # View current configuration
femtobot setup      # Guided setup (features, models, tokens)
femtobot wizard     # Interactive configurator (edit config via menus)
femtobot doctor     # Diagnose issues
femtobot update     # Pull setup updates
```


## ⚙️ Configuration

### `.env`
```env
TELEGRAM_TOKEN=your_botfather_token
AUTHORIZED_USERS=123456789  # Your Telegram ID
NOTIFICATION_CHAT_ID=123456789
BRAVE_API_KEY=your_api_key  # Optional, for searches
GMAIL_USER=your_email@gmail.com  # Optional, for email digest
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### `config.yaml`
```yaml
# Backend Configuration
BACKEND:
  PROVIDER: "ollama"           # Use "ollama" or "lmstudio"
  OLLAMA_URL: "http://localhost:11434"
  LMSTUDIO_URL: "http://localhost:1234"

# Models
MODEL: "llama3.1:latest"
VISION_MODEL: "qwen3-vl:2b"    # Leave blank to use main model
MATH_MODEL: "qwen2-math:7b"
OCR_MODEL: "glm-ocr:latest"    # Leave blank to use vision/main model
CONTEXT_LIMIT: 200000
WHISPER_LANGUAGE: "en"
WHISPER_MODEL_VOICE: "base"
WHISPER_MODEL_EXTERNAL: "medium"
INACTIVITY_TIMEOUT_MINUTES: 5

# RAG / Memory Configuration
RAG:
  EMBEDDING_MODEL: "nomic-embed-text"
  CHUNK_SIZE: 1000
  SIMILARITY_THRESHOLD: 0.4
  MAX_RESULTS: 3

# Optional features (set to false to disable)
FEATURES:
  WIZ_LIGHTS: true
  EMAIL_DIGEST: true
  MATH_SOLVER: true
  DEEP_RESEARCH: true
  YOUTUBE: true
  TWITTER: true
```

## 🎮 Usage

### Telegram Bot
```bash
femtobot start
```
(Or use `./run.sh` if you prefer the script)

### TUI Interface
```bash
femtobot tui
```

**TUI Features:**
- 💾 **Persistent History**: Conversations saved automatically
- 📂 **Session Management**: Save/load multiple sessions
- 📄 **Export**: Export conversations to markdown
- 🔔 **Notifications**: Receive cron notifications in TUI
- ⌨️ **Slash Commands**: Quick access to functions

**TUI Commands:**
```
/status         - View token usage and model status
/deep           - Start deep research
/new, /clear    - Start new conversation
/save [name]    - Save current session
/load [name]    - Load saved session
/sessions       - List all saved sessions
/export [file]  - Export to markdown file
/unload         - Unload models from RAM
/help           - Show all commands
```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Start conversation |
| `/new` | New conversation (clears history) |
| `/status` | View context and token usage |
| `/unload` | Unload all models from RAM |

## 📁 Project Structure
```
FemtoBot/
├── config.yaml              # Main configuration
├── .env                     # Environment variables (tokens)
├── requirements.txt         # Python dependencies
├── run.sh                   # Run script (setup + run)
│
├── src/                     # Source code
│   ├── telegram_bot.py      # Main Telegram bot (Entry Point)
│   ├── tui.py              # TUI interface
│   ├── client.py           # Ollama client
│   ├── constants.py        # Global constants
│   ├── services/           # Business Logic Services
│   │   ├── rag_service.py      # RAG & Context Management
│   │   ├── media_service.py    # Twitter/YouTube handling
│   │   └── command_service.py  # Internal bot commands
│   ├── handlers/           # Message handlers
│   │   ├── commands.py     # Bot slash commands
│   │   ├── voice.py        # Voice messages
│   │   ├── audio.py        # Audio files
│   │   ├── photo.py        # Images
│   │   └── document.py     # Documents
│   ├── jobs/               # Background jobs
│   │   ├── events.py       # Event notifications
│   │   ├── inactivity.py   # Auto-unload models
│   │   ├── cleanup.py      # Cleanup old data
│   │   └── email_digest.py # Email summary
│   ├── middleware/         # Middleware
│   │   └── rate_limiter.py # Rate limiting
│   ├── state/              # State management
│   │   └── chat_manager.py # Chat history
│   └── memory/             # Long-term Memory
│       └── vector_store.py # ChromaDB wrapper
│
├── utils/                   # Utility modules
│   ├── audio_utils.py       # Whisper transcription
│   ├── youtube_utils.py     # YouTube audio download
│   ├── twitter_utils.py     # Twitter/X downloads
│   ├── search_utils.py      # Brave search
│   ├── cron_utils.py        # Crontab management
│   ├── document_utils.py    # PDF/DOCX extraction
│   ├── email_utils.py       # Gmail integration
│   ├── wiz_utils.py         # WIZ smart lights
│   ├── telegram_utils.py    # Telegram helpers
│   └── config_loader.py     # YAML config loader
│
├── tests/                   # Test suite
│   ├── conftest.py
│   └── unit/
│
├── docs/                    # Documentation
│   ├── architecture.md
│   └── troubleshooting.md
│
├── data/                    # Data files
│   ├── instructions.md      # LLM instructions
│   ├── memory.md            # User memory
│   └── events.txt           # Notification queue
│
└── assets/                  # Resources
    └── styles.tcss          # TUI styles
```
## System Architecture

```
┌─────────────────────────────────────────────┐
│         User Interfaces                     │
│  ┌──────────────┐    ┌─────────────────┐    │
│  │   Telegram   │    │   TUI (Textual) │    │
│  │    Bot       │    │   (Terminal)    │    │
│  └──────┬───────┘    └────────┬──────── ┘   │
└─────────┼─────────────────────┼─────────────┘
          │                     │
          └──────────┬──────────┘
                     │
┌────────────────────┴────────────────────────┐
│          Message Processing Layer           │
│  - Queue-based sequential processing        │
│  - Command parsing (:::command:::)          │
│  - Media handling (voice, photo, docs)      │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│          LLM Integration (Ollama)           │
│  - Streaming chat API                       │
│  - Vision model for image analysis          │
│  - Context management with pruning          │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│           Utility Services                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │ Whisper │ │  Brave  │ │  YouTube    │    │
│  │(Speech) │ │ Search  │ │  Download   │    │
│  └─────────┘ └─────────┘ └─────────────┘    │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │  WIZ    │ │  Cron   │ │  Gmail      │    │
│  │ Lights  │ │ Jobs    │ │  IMAP       │    │
│  └─────────┘ └─────────┘ └─────────────┘    │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │   OCR   │ │  Math   │ │  Catbox     │    │
│  │ Service │ │ Solver  │ │  Uploads    │    │
│  └─────────┘ └─────────┘ └─────────────┘    │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │   RAG   │ │  Docs   │ │  Calendar   │    │
│  │ System  │ │ Reader  │ │   Events    │    │
│  └─────────┘ └─────────┘ └─────────────┘    │
└─────────────────────────────────────────────┘
```


## 🐛 Troubleshooting

See `docs/troubleshooting.md` for common issues and solutions.

Common problems:
- **Ollama connection refused** → Check if `ollama serve` is running
- **Whisper not installed** → Run `pip install faster-whisper`
- **Rate limit exceeded** → Wait 60 seconds between messages
- **Model not found** → Download with `ollama pull model-name`

## 📄 License

MIT License 
Copyright 2026 Rocopolas

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

Hecho con 🧉 en Argentina
