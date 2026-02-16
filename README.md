
![FemtoBot Logo](https://files.catbox.moe/zhkn08.jpg)

A smart personal assistant designed for small local models, recommended for GPUs with at least 8GB of VRAM. Runs locally using [Ollama](https://ollama.ai). Available as a Telegram bot and TUI interface.

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

## 🤔 Why FemtoBot?

| | FemtoBot | Cloud Bots (Claude, GPT) |
|---|---|---|
| 💰 **Cost** | **Free** | $20+/month or pay per use |
| 🔒 **Privacy** | Your data never leaves your PC | Your chats go to external servers |
| ⚡ **Speed** | Small models = instant responses | Depends on API and your plan |
| 🌐 **Internet** | Works offline | Requires constant connection |
| 🎛️ **Control** | You choose model, context, everything | Limited to what they offer |
| 🏠 **Smart Home** | Control your lights, all local | Not available |

**Ideal for:**
- Using small and fast models (7B-14B params)
- Keeping your privacy at 100%
- Not paying monthly subscriptions
- Having a personal assistant that runs on YOUR hardware

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

## 🚀 Installation & Setup

FemtoBot is designed to be easy to install and runs entirely locally. You can use the automated setup script or install it manually.

### 📋 Prerequisites

- **Python 3.12** (Strictly required)
- **Git** needed to clone the repository
- **[Ollama](https://ollama.ai)** installed and running (`ollama serve`)
- **FFmpeg** required for audio transcription features

---

### ⚡ Option 1: Automated Installation (Recommended)

This is the fastest way to get started. The `run.sh` script handles environment creation and dependencies.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rocopolas/FemtoBot.git
    cd FemtoBot
    ```

2.  **Run the setup script:**
    ```bash
    chmod +x run.sh
    ./run.sh
    ```
    This script will:
    - Check for Python 3.12
    - Create a virtual environment (`venv_bot`)
    - Install all required dependencies
    - specificy `femtobot` command installation

3.  **Install the System-wide CLI (Optional):**
    To use the `femtobot` command from any terminal:
    ```bash
    chmod +x scripts/install_cli.sh
    sudo ./scripts/install_cli.sh # requires sudo
    ```

---

### 🛠️ Option 2: Manual Installation

If you prefer to configure the environment yourself:

1.  **Clone and enter the directory:**
    ```bash
    git clone https://github.com/rocopolas/FemtoBot.git
    cd FemtoBot
    ```

2.  **Create and activate virtual environment:**
    ```bash
    python3.12 -m venv venv_bot
    source venv_bot/bin/activate
    # On Windows: venv_bot\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

### 🐳 Option 3: Docker

Run FemtoBot and Ollama together using Docker Compose:

```bash
git clone https://github.com/rocopolas/FemtoBot.git
cd FemtoBot
cp .env.example .env
# Edit .env with your tokens
docker compose up -d
```

> **Note:** GPU passthrough is configured for NVIDIA GPUs. Edit `docker-compose.yml` if you use a different GPU or CPU-only.

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
MODEL: "llama3.1:latest"
VISION_MODEL: "qwen3-vl:2b"
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
./run.sh
```

### TUI Interface
```bash
source venv_bot/bin/activate
python src/main.py
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

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov=utils
```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Start conversation |
| `/new` | New conversation (clears history) |
| `/status` | View context and token usage |
| `/unload` | Unload all models from RAM |

## 🎤 Special Features

### 👁️ Image Analysis
- Send a photo → Vision model describes it, text model responds
- Send photo + caption → Bot considers both for response

### 🎙️ Audio Transcription
- Send a voice message → Transcribed and answered
- Send an audio file → Transcription only (larger model)

### 🎥 YouTube Summary & Download
- Send a YouTube link → Bot downloads, transcribes and summarizes (Default)
- Send link + "download" → Bot sends you the video file

### 🐦 Twitter/X Media Download
- Send a Twitter/X link and ask to "download" or "bajar"
- The bot will download the video/image and send the file to you

### 📦 File Upload (Catbox.moe)
- **Direct Upload**: Send a photo or video with the message "upload to catbox" or "give me the link".
- **Reply**: Reply to any image or video (yours or the bot's) with "upload this" and the bot will return a permanent direct link.

### 🔍 Smart Image Search
- Ask: "Give me a photo of [something]" or "Search for an image of [something]"
- The **LLM decides** to search for an image and uses the command `:::foto...:::`.
- The bot searches Brave Images, then uses its **Vision Model** to look at the candidates.
- It only sends the image if the AI confirms it matches your request!

### 🧮 Math Solver
- **Automatic Detection**: Ask any math problem (algebra, calculus, matrices, etc.).
- The bot detects the intent and automatically switches to a **Specialized Math Model** (configured in `config.yaml`).
- **Formatted Response**: You receive a step-by-step solution with perfect **LaTeX** rendering in Telegram.
- **Examples:**
  - "Solve the integral of x^2 dx"
  - "Find the roots of 2x^2 + 5x - 3 = 0"
  - "Calculate the eigenvalues of the matrix..."

### 📄 Document Reading & OCR
- Send a PDF, DOCX, or TXT file → Bot extracts text and responds.
- **Automatic OCR**: If the document is scanned (text density < 15 words/page), the bot automatically:
  1. Converts pages to high-res images.
  2. Uses the Vision Model (`glm-4v` by default) to read the content.
  3. Formats **Mathematical Formulas** (LaTeX) into readable text (e.g., converts `$x^2$` to `x²`).
- **Math Support**: Detects and beautifully renders complex math formulas from academic papers.
- Send document + caption → Bot considers both for response.

### ⏰ Reminders
Ask the bot things like:
- "Remind me to drink water every hour"
- "Notify me tomorrow at 9am about my meeting"

### 🧠 Vector Memory (RAG)
The bot uses a local vector database (ChromaDB) to remember facts and conversations.

**To learn new things:**
- Just tell it: *"My mom is Jessica"* → Auto-saved if deemed important.
- Force save: `:::memory Data to save:::`

**To forget:**
- `:::memory_delete Data to forget:::`
- Detects the most similar memory (>85% match) and deletes it.

**To view usage:**
- Look for **"🧠 RAG..."** status when the bot is searching its memory.


### 📧 Email Digest (Optional)
If Gmail is configured, the bot will:
- Run at 4:00 AM daily
- Read emails from the last 24 hours
- Use LLM to identify important emails
- Send you a summary on Telegram

### 💡 Smart Lights (Optional)
Control WIZ lights via natural language:
- "Turn off the bedroom lights"
- "Set brightness to 50%"
- "Change color to red"
- "Turn off all lights"

**Configuration** in `config.yaml`:
```yaml
WIZ_LIGHTS:
  bedroom:  # Single light
    - "192.168.0.121"
  living:   # Multiple lights (group)
    - "192.168.0.63"
    - "192.168.0.115"
```

**Requires**: `pip install pywizlight`

### 🧠 Deep Research
- **Command**: `/deep <topic>`
- **Function**: Performs an iterative research process on the given topic.
- **Process**:
  1.  Analyzes the topic and decides on search queries.
  2.  Uses **Brave Search** to gather information.
  3.  Summarizes findings and repeats the process (up to 5 iterations).
  4.  Generates a comprehensive **ODT Report** (OpenDocument Text).
  5.  Sends the report to you via Telegram.

## 🔧 Development

### Architecture
The project uses a modular architecture:
- **Handlers**: Separate modules for different message types
- **Jobs**: Background tasks (cleanup, notifications)
- **State**: Thread-safe chat history management
- **Middleware**: Rate limiting and other cross-cutting concerns

See `docs/architecture.md` for detailed information.

### Adding new features
1. Create the module in `utils/`
2. Import it in appropriate handler
3. Add instructions in `data/instructions.md`

### Changing model
Edit `config.yaml`:
```yaml
MODEL: "your-model:tag"
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
