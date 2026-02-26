"""FemtoBot CLI - Command line interface for managing the bot."""
import os
import sys
import signal
import subprocess
import time
import click
import tempfile

# Resolve project root from this file's location
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from src.constants import CONFIG_DIR, DATA_DIR

PID_FILE = os.path.join(CONFIG_DIR, "femtobot.pid")
LOG_FILE = os.path.join(CONFIG_DIR, "femtobot.log")
BOT_SCRIPT_NAME = "telegram_bot.py"

# Colors
GREEN = "green"
RED = "red"
YELLOW = "yellow"
CYAN = "cyan"


def _ensure_dir():
    """Ensure ~/.femtobot directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _read_pid():
    """Read PID from file, return None if not found or invalid."""
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid):
    """Check if a process with given PID is running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _ensure_psutil():
    """Ensure psutil is installed, install if missing."""
    try:
        import psutil
        return psutil
    except ImportError:
        click.secho("⚠ Installing required dependency: psutil...", fg=YELLOW)
        python = _get_python()
        result = subprocess.run(
            [python, "-m", "pip", "install", "psutil>=5.9.0", "--quiet"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            click.secho(f"✗ Failed to install psutil: {result.stderr}", fg=RED)
            click.secho("  Please install manually: pip install psutil>=5.9.0", fg=YELLOW)
            sys.exit(1)
        # Reimport after installation
        import psutil
        click.secho("✓ psutil installed successfully", fg=GREEN)
        return psutil


def _kill_all_bot_processes():
    """Kill all processes related to the bot including children."""
    psutil = _ensure_psutil()
    
    killed = []
    errors = []
    
    # Find all python processes running telegram_bot.py
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
            if pinfo['name'] and 'python' in pinfo['name'].lower():
                cmdline = ' '.join(pinfo['cmdline'] or [])
                if BOT_SCRIPT_NAME in cmdline or 'femtobot' in cmdline:
                    try:
                        # Kill the process tree
                        parent = psutil.Process(pinfo['pid'])
                        children = parent.children(recursive=True)
                        
                        # Kill children first
                        for child in children:
                            try:
                                child.terminate()
                            except psutil.NoSuchProcess:
                                pass
                        
                        # Wait for children
                        gone, alive = psutil.wait_procs(children, timeout=2)
                        
                        # Force kill if still alive
                        for child in alive:
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        
                        # Kill parent
                        parent.terminate()
                        try:
                            parent.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            parent.kill()
                        
                        killed.append(pinfo['pid'])
                    except Exception as e:
                        errors.append(f"PID {pinfo['pid']}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Also try to kill by PID file if exists
    pid = _read_pid()
    if pid and pid not in killed:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            if _is_running(pid):
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
        except ProcessLookupError:
            pass
        except Exception as e:
            errors.append(f"PID file {pid}: {e}")
    
    return killed, errors


def _get_python():
    """Get the Python executable path (prefer venv if available)."""
    venv_python = os.path.join(PROJECT_ROOT, "venv_bot", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def _check_ollama():
    """Check if Ollama is reachable."""
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


@click.group()
@click.version_option(version="1.0.0", prog_name="FemtoBot")
def cli():
    """ 🐰 FemtoBot - Smart personal assistant for local LLMs.

    Manage your FemtoBot instance from the command line.
    """
    pass


@cli.command()
def serve():
    """Start the Telegram bot in foreground (blocking)."""
    click.secho("🚀 Starting FemtoBot (foreground)...", fg=CYAN)

    # Check if daemon is running
    pid = _read_pid()
    if _is_running(pid):
        click.secho(f"⚠ FemtoBot daemon is already running (PID {pid})", fg=RED)
        click.secho("  Run 'femtobot stop' first, or 'femtobot logs -f' to monitor it.", fg=YELLOW)
        return

    # Ensure we're in the config directory for relative paths
    _ensure_dir()
    os.chdir(CONFIG_DIR)
    sys.path.insert(0, PROJECT_ROOT)

    # Check Ollama
    if _check_ollama():
        click.secho("✓ Ollama detected", fg=GREEN)
    else:
        click.secho("⚠ Ollama is not running. Start it with 'ollama serve'", fg=YELLOW)

    # Import and run the bot
    from src.telegram_bot import main
    main()


@cli.command()
def start():
    """Start the Telegram bot as a background daemon."""
    _ensure_dir()

    pid = _read_pid()
    if _is_running(pid):
        click.secho(f"⚠ FemtoBot is already running (PID {pid})", fg=YELLOW)
        return

    # Check Ollama
    if not _check_ollama():
        click.secho("⚠ Ollama is not running. Start it with 'ollama serve'", fg=YELLOW)

    click.secho("🚀 Starting FemtoBot daemon...", fg=CYAN)

    python = _get_python()
    bot_script = os.path.join(PROJECT_ROOT, "src", "telegram_bot.py")

    with open(LOG_FILE, "a") as log:
        proc = subprocess.Popen(
            [python, bot_script],
            cwd=CONFIG_DIR,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    # Brief wait to check if process started successfully
    time.sleep(1)
    if _is_running(proc.pid):
        click.secho(f"✓ FemtoBot started (PID {proc.pid})", fg=GREEN)
        click.echo(f"  Logs: {LOG_FILE}")
    else:
        click.secho("✗ FemtoBot failed to start. Check logs:", fg=RED)
        click.echo(f"  {LOG_FILE}")


@cli.command()
def stop():
    """Stop the running FemtoBot daemon (kills all processes)."""
    pid = _read_pid()
    
    # Ensure psutil is available
    psutil = _ensure_psutil()
    
    # Check if any bot processes are running
    bot_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
            if pinfo['name'] and 'python' in pinfo['name'].lower():
                cmdline = ' '.join(pinfo['cmdline'] or [])
                if BOT_SCRIPT_NAME in cmdline or 'femtobot' in cmdline:
                    bot_procs.append(pinfo['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not bot_procs and not _is_running(pid):
        click.secho("⚠ FemtoBot is not running", fg=YELLOW)
        # Clean stale PID file
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return

    if bot_procs:
        click.secho(f"Found {len(bot_procs)} bot process(es): {bot_procs}", fg=CYAN)
    elif pid:
        click.secho(f"Stopping FemtoBot (PID {pid})...", fg=CYAN)

    # Kill all bot processes
    killed, errors = _kill_all_bot_processes()
    
    if killed:
        click.secho(f"✓ Killed {len(killed)} process(es): {killed}", fg=GREEN)
    
    if errors:
        click.secho(f"⚠ Errors during kill: {errors}", fg=YELLOW)

    # Clean PID file
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    
    # Double check no processes remain
    time.sleep(0.5)
    remaining = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
            if pinfo['name'] and 'python' in pinfo['name'].lower():
                cmdline = ' '.join(pinfo['cmdline'] or [])
                if BOT_SCRIPT_NAME in cmdline or 'femtobot' in cmdline:
                    remaining.append(pinfo['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if remaining:
        click.secho(f"✗ Warning: {len(remaining)} process(es) still alive: {remaining}", fg=RED)
        click.secho("  You may need to kill them manually with: kill -9 " + " ".join(map(str, remaining)))
    else:
        click.secho("✓ FemtoBot stopped completely (0 processes remaining)", fg=GREEN)


@cli.command()
@click.pass_context
def restart(ctx):
    """Restart the FemtoBot daemon (stop all processes + start)."""
    # Ensure psutil is available
    psutil = _ensure_psutil()
    
    # Check for existing processes
    bot_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
            if pinfo['name'] and 'python' in pinfo['name'].lower():
                cmdline = ' '.join(pinfo['cmdline'] or [])
                if BOT_SCRIPT_NAME in cmdline or 'femtobot' in cmdline:
                    bot_procs.append(pinfo['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    pid = _read_pid()
    
    # Stop all processes
    if bot_procs or _is_running(pid):
        if bot_procs:
            click.secho(f"Stopping {len(bot_procs)} bot process(es): {bot_procs}...", fg=CYAN)
        else:
            click.secho(f"Stopping FemtoBot (PID {pid})...", fg=CYAN)
        
        killed, errors = _kill_all_bot_processes()
        
        if killed:
            click.secho(f"✓ Killed {len(killed)} process(es)", fg=GREEN)
        
        if errors:
            click.secho(f"⚠ Some errors occurred: {errors}", fg=YELLOW)
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        
        # Wait to ensure all processes are dead
        time.sleep(1)
        
        # Verify all processes are dead
        remaining = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pinfo = proc.info
                if pinfo['name'] and 'python' in pinfo['name'].lower():
                    cmdline = ' '.join(pinfo['cmdline'] or [])
                    if BOT_SCRIPT_NAME in cmdline or 'femtobot' in cmdline:
                        remaining.append(pinfo['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if remaining:
            click.secho(f"⚠ Warning: {len(remaining)} process(es) still alive, attempting force kill...", fg=YELLOW)
            for rpid in remaining:
                try:
                    os.kill(rpid, signal.SIGKILL)
                except:
                    pass
            time.sleep(0.5)
        
        click.secho("✓ All bot processes stopped", fg=GREEN)
    else:
        click.secho("⚠ No running bot processes found", fg=YELLOW)

    # Start
    click.echo()
    ctx.invoke(start)



@cli.command()
def status():
    """Show FemtoBot status (running, PID, Ollama, etc)."""
    click.secho("=== FemtoBot Status ===", fg=CYAN, bold=True)

    # Bot process
    pid = _read_pid()
    if _is_running(pid):
        click.secho(f"  Bot:    ✓ Running (PID {pid})", fg=GREEN)
        # Show uptime via /proc if available
        try:
            stat = os.stat(f"/proc/{pid}")
            import datetime
            started = datetime.datetime.fromtimestamp(stat.st_mtime)
            uptime = datetime.datetime.now() - started
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            click.echo(f"  Uptime: {hours}h {minutes}m {seconds}s")
        except (FileNotFoundError, OSError):
            pass
    else:
        click.secho("  Bot:    ✗ Stopped", fg=RED)

    # Ollama
    if _check_ollama():
        click.secho("  Ollama: ✓ Running", fg=GREEN)
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=3)
            models = r.json().get("models", [])
            if models:
                loaded = [m["name"] for m in models]
                click.echo(f"  Models: {', '.join(loaded)}")
        except Exception:
            pass
    else:
        click.secho("  Ollama: ✗ Not running", fg=RED)

    # Log file
    if os.path.exists(LOG_FILE):
        size = os.path.getsize(LOG_FILE)
        if size > 1024 * 1024:
            click.echo(f"  Log:    {LOG_FILE} ({size / 1024 / 1024:.1f} MB)")
        else:
            click.echo(f"  Log:    {LOG_FILE} ({size / 1024:.1f} KB)")
    else:
        click.echo("  Log:    (no logs yet)")


@cli.command()
@click.option("-f", "--follow", is_flag=True, help="Follow log output in real-time")
@click.option("-n", "--lines", default=50, help="Number of lines to show")
def logs(follow, lines):
    """Show FemtoBot logs."""
    if not os.path.exists(LOG_FILE):
        click.secho("No logs found yet. Start the bot first with 'femtobot start'", fg=YELLOW)
        return

    if follow:
        click.secho(f"Following {LOG_FILE} (Ctrl+C to stop)...\n", fg=CYAN)
        try:
            proc = subprocess.run(
                ["tail", "-f", "-n", str(lines), LOG_FILE],
            )
        except KeyboardInterrupt:
            click.echo("\n")
    else:
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), LOG_FILE],
                capture_output=True, text=True,
            )
            click.echo(result.stdout)
        except FileNotFoundError:
            # tail not available, read manually
            with open(LOG_FILE, "r") as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    click.echo(line, nl=False)


@cli.command()
def tui():
    """Launch the TUI (terminal) interface."""
    click.secho("🖥️  Starting FemtoBot TUI...", fg=CYAN)

    os.chdir(CONFIG_DIR)
    sys.path.insert(0, PROJECT_ROOT)

    from src.tui import FemtoBotApp
    app = FemtoBotApp()
    app.run()


@cli.command()
def config():
    """Show current configuration."""
    config_path = os.path.join(CONFIG_DIR, "config.yaml")

    if not os.path.exists(config_path):
        click.secho("✗ config.yaml not found", fg=RED)
        return

    click.secho("=== FemtoBot Configuration ===\n", fg=CYAN, bold=True)

    with open(config_path, "r") as f:
        content = f.read()

    # Colorize YAML output
    for line in content.splitlines():
        if line.strip().startswith("#"):
            click.secho(line, fg="bright_black")
        elif ":" in line and not line.strip().startswith("-"):
            key, _, value = line.partition(":")
            click.secho(key + ":", fg=CYAN, nl=False)
            click.echo(value)
        else:
            click.echo(line)


# ─── SETUP ────────────────────────────────────────────────────────────

@cli.command()
def setup():
    """Download required Ollama models from config.yaml."""
    import yaml

    # Check Python version
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 12):
        click.secho(f"⚠ Warning: You are running Python {v.major}.{v.minor}.{v.micro}", fg=YELLOW)
        click.secho("  FemtoBot is designed for Python 3.12+. Some features may not work.", fg=YELLOW)
        if not click.confirm("  Do you want to continue anyway?", default=False):
            return
    else:
        click.secho(f"✓ Python {v.major}.{v.minor}.{v.micro} detected", fg=GREEN)

    # Ensure config directory exists
    from src.constants import CONFIG_DIR, DATA_DIR
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    config_path = os.path.join(CONFIG_DIR, "config.yaml")

    # Create config if missing
    if not os.path.exists(config_path):
        click.secho(f"⚠ config.yaml not found at {config_path}", fg=YELLOW)
        click.secho("  Creating default configuration...", fg=CYAN)
        
        from utils.config_loader import DEFAULT_CONFIG
        # Update paths in default config to be absolute or relative to CONFIG_DIR correctly
        # Actually, DEFAULT_CONFIG uses relative paths like "data/instructions.md"
        # which will resolve relative to where the bot is run/configured.
        
        try:
            with open(config_path, "w") as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
            click.secho("  ✓ Created config.yaml", fg=GREEN)
        except Exception as e:
            click.secho(f"  ✗ Failed to create config.yaml: {e}", fg=RED)
            return

    # Check for .env
    env_path = os.path.join(CONFIG_DIR, ".env")
    if not os.path.exists(env_path):
        click.secho(f"⚠ .env not found at {env_path}", fg=YELLOW)
        click.secho("  Configuration required:", fg=CYAN)
        
        telegram_token = click.prompt("🐰 Telegram Bot Token", type=str)
        auth_users = click.prompt("👥 Authorized Users (comma-separated IDs)", type=str)
        notif_chat = click.prompt("📢 Notification Chat ID", default=auth_users.split(',')[0].strip(), show_default=True)
        
        click.echo("\n--- Optional Integrations (press Enter to skip) ---")
        brave_key = click.prompt("🔍 Brave Search API Key", default="", show_default=False)
        gmail_user = click.prompt("📧 Gmail User", default="", show_default=False)
        gmail_pass = ""
        if gmail_user:
            gmail_pass = click.prompt("🔑 Gmail App Password", default="", hide_input=True, show_default=False)
            
        try:
            with open(env_path, "w") as f:
                f.write(f"# Telegram\nTELEGRAM_TOKEN={telegram_token}\nAUTHORIZED_USERS={auth_users}\nNOTIFICATION_CHAT_ID={notif_chat}\n\n")
                if brave_key:
                    f.write(f"# Search\nBRAVE_API_KEY={brave_key}\n\n")
                if gmail_user:
                    f.write(f"# Email\nGMAIL_USER={gmail_user}\nGMAIL_APP_PASSWORD={gmail_pass}\n")
                    
            click.secho("  ✓ Created .env", fg=GREEN)
        except Exception as e:
            click.secho(f"  ✗ Failed to create .env: {e}", fg=RED)
    else:
        click.secho("✓ .env found", fg=GREEN)

    # --- Feature Selection ---
    click.echo("\n--- Optional Features ---")
    click.secho("  Enable or disable optional features (press Enter for default):\n", fg=CYAN)
    
    features = {}
    feature_prompts = [
        ("WIZ_LIGHTS", "💡 WIZ Smart Lights control", False),
        ("EMAIL_DIGEST", "📧 Daily email digest (requires Gmail)", False),
        ("MATH_SOLVER", "🧮 Math solver (requires extra model)", True),
        ("DEEP_RESEARCH", "🧠 Deep research mode", True),
        ("YOUTUBE", "🎥 YouTube summaries & downloads", True),
        ("TWITTER", "🐦 Twitter/X media downloads", True),
    ]
    
    for key, label, default in feature_prompts:
        features[key] = click.confirm(f"  {label}?", default=default)
    
    # WIZ Lights configuration
    wiz_lights = {}
    if features.get("WIZ_LIGHTS"):
        click.echo("\n--- WIZ Light Configuration ---")
        click.secho("  Add your WIZ light bulbs (name + IP address).\n", fg=CYAN)
        while True:
            name = click.prompt("  Light name (or 'done' to finish)", default="done", show_default=True)
            if name.lower() == "done":
                break
            ip = click.prompt(f"  IP address for '{name}'")
            wiz_lights[name] = ip
            click.secho(f"  ✓ Added {name} → {ip}", fg=GREEN)
    
    # --- Auto-detect Language ---
    detected_lang = "en"
    try:
        import locale
        system_locale = locale.getdefaultlocale()[0] or ""
        locale_map = {
            "es": "es", "en": "en", "pt": "pt", "fr": "fr", "de": "de",
            "it": "it", "ja": "ja", "ko": "ko", "zh": "zh", "ru": "ru",
            "ar": "ar", "nl": "nl", "pl": "pl", "tr": "tr", "sv": "sv",
        }
        lang_prefix = system_locale.split("_")[0].lower() if system_locale else ""
        detected_lang = locale_map.get(lang_prefix, "en")
    except Exception:
        pass
    
    whisper_lang = click.prompt(
        f"\n🌐 Whisper language (auto-detected: {detected_lang})",
        default=detected_lang, show_default=True
    )

    # --- Write features + language to config.yaml ---
    try:
        with open(config_path, "r") as f:
            cfg_content = yaml.safe_load(f) or {}
        
        cfg_content["FEATURES"] = features
        cfg_content["WHISPER_LANGUAGE"] = whisper_lang
        
        if wiz_lights:
            cfg_content["WIZ_LIGHTS"] = wiz_lights
        elif not features.get("WIZ_LIGHTS"):
            cfg_content.pop("WIZ_LIGHTS", None)
        
        with open(config_path, "w") as f:
            yaml.dump(cfg_content, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        click.secho("\n  ✓ Features and language saved to config.yaml", fg=GREEN)
    except Exception as e:
        click.secho(f"  ⚠ Failed to save features: {e}", fg=YELLOW)

    # Reload config now that it exists
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    # Ensure default data files exist
    try:
        # Instructions
        instr_file = cfg.get("INSTRUCTIONS_FILE", "data/instructions.md")
        instr_path = os.path.join(CONFIG_DIR, instr_file)
        os.makedirs(os.path.dirname(instr_path), exist_ok=True)
        
        if not os.path.exists(instr_path):
            click.secho(f"  Creating default instructions at {instr_file}...", fg=CYAN)
            try:
                import importlib.resources
                content = importlib.resources.read_text("data", "instructions.md")
            except (ImportError, FileNotFoundError):
                fallback_path = os.path.join(PROJECT_ROOT, "data", "instructions.md")
                if os.path.exists(fallback_path):
                     with open(fallback_path, "r", encoding="utf-8") as f:
                        content = f.read()
                else:
                    content = "You are a helpful assistant."

            with open(instr_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            click.secho(f"  ✓ Created {instr_file}", fg=GREEN)

        # Events
        events_file = cfg.get("EVENTS_FILE", "data/events.txt")
        events_path = os.path.join(CONFIG_DIR, events_file)
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        
        if not os.path.exists(events_path):
            with open(events_path, "w", encoding="utf-8") as f:
                f.write("")
            click.secho(f"  ✓ Created empty {events_file}", fg=GREEN)

        # Memory
        memory_file = cfg.get("MEMORY_FILE", "data/memory.md")
        if memory_file:
            memory_path = os.path.join(CONFIG_DIR, memory_file)
            os.makedirs(os.path.dirname(memory_path), exist_ok=True)
            if not os.path.exists(memory_path):
                with open(memory_path, "w", encoding="utf-8") as f:
                    f.write("# Memory Store\n")
                click.secho(f"  ✓ Created {memory_file}", fg=GREEN)

    except Exception as e:
        click.secho(f"  ⚠ Failed to ensure data files: {e}", fg=YELLOW)

    # Detect backend provider
    backend_cfg = cfg.get("BACKEND", {})
    provider = (backend_cfg.get("PROVIDER", "ollama") if isinstance(backend_cfg, dict) else "ollama").lower()

    # Collect model names from config
    model_keys = ["MODEL", "VISION_MODEL", "MATH_MODEL", "OCR_MODEL"]
    rag_config = cfg.get("RAG", {})
    
    # Chat/vision/math/OCR models
    chat_models = []
    for key in model_keys:
        val = cfg.get(key)
        if val:
            chat_models.append((key, val))

    # Embedding model (always Ollama)
    embed_model = rag_config.get("EMBEDDING_MODEL")

    if provider == "lmstudio":
        # ── LM Studio mode ──
        click.secho("\n=== Backend: LM Studio ===\n", fg=CYAN, bold=True)
        
        all_models = chat_models[:]
        if embed_model:
            all_models.append(("EMBEDDING_MODEL", embed_model))
        
        if all_models:
            click.secho("  ℹ The following models must be downloaded from the LM Studio GUI:", fg=YELLOW)
            for key, model_name in all_models:
                click.secho(f"    • {key}: {model_name}", fg=YELLOW)
            click.echo()
    else:
        # ── Ollama mode (original logic) ──
        models = chat_models[:]
        if embed_model:
            models.append(("EMBEDDING_MODEL", embed_model))

        if not models:
            click.secho("No models found in config.yaml", fg=YELLOW)
            return

        if not _check_ollama():
            click.secho("✗ Ollama is not running.", fg=RED)
            click.secho("  Please start Ollama (e.g. 'ollama serve') and RUN 'femtobot setup' AGAIN to download models.", fg=YELLOW)
            return

        # Get already-downloaded models
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=5)
            existing = {m["name"] for m in r.json().get("models", [])}
        except Exception:
            existing = set()

        click.secho("\n=== Downloading Models ===\n", fg=CYAN, bold=True)

        for key, model_name in models:
            if model_name in existing:
                click.secho(f"  ✓ {key}: {model_name} (already downloaded)", fg=GREEN)
            else:
                click.secho(f"  ⬇ {key}: {model_name} — pulling...", fg=CYAN)
                result = subprocess.run(
                    ["ollama", "pull", model_name],
                    capture_output=False,
                )
                if result.returncode == 0:
                    click.secho(f"  ✓ {model_name} downloaded", fg=GREEN)
                else:
                    click.secho(f"  ✗ Failed to pull {model_name}", fg=RED)

    click.echo()
    click.secho("✓ Setup complete! Run 'femtobot start' to launch the bot.", fg=GREEN, bold=True)


# ─── UPDATE ───────────────────────────────────────────────────────────

@cli.command()
def update():
    """Update FemtoBot (git pull OR install latest release)."""
    click.secho("=== FemtoBot Update ===\n", fg=CYAN, bold=True)

    git_dir = os.path.join(PROJECT_ROOT, ".git")
    python = _get_python()

    if os.path.isdir(git_dir):
        # --- GIT UPDATE STRATEGY ---
        click.secho("  Pulling latest changes (git)...", fg=CYAN)
        result = subprocess.run(
            ["git", "pull"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if "Already up to date" in output:
                click.secho("  ✓ Already up to date", fg=GREEN)
            else:
                click.secho(f"  ✓ Updated:\n{output}", fg=GREEN)
        else:
            click.secho(f"  ✗ Git pull failed: {result.stderr.strip()}", fg=RED)
            return

        # Install deps
        click.secho("  Installing dependencies...", fg=CYAN)
        result = subprocess.run(
            [python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            click.secho("  ✓ Dependencies updated", fg=GREEN)
        else:
            click.secho(f"  ✗ pip install failed: {result.stderr.strip()}", fg=RED)
            return

        # Re-install package editable
        result = subprocess.run(
            [python, "-m", "pip", "install", "-e", ".", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            click.secho("  ✓ CLI re-installed", fg=GREEN)

    else:
        # --- GITHUB RELEASE STRATEGY ---
        click.secho("  Git not found. Checking latest release on GitHub...", fg=CYAN)
        try:
            import httpx
            resp = httpx.get("https://api.github.com/repos/rocopolas/FemtoBot/releases/latest", timeout=10.0)
            
            if resp.status_code == 404:
                click.secho("  ✗ No releases found on GitHub repo.", fg=RED)
                return
            
            if resp.status_code != 200:
                click.secho(f"  ✗ Failed to fetch releases: HTTP {resp.status_code}", fg=RED)
                return

            data = resp.json()
            tag_name = data.get("tag_name", "unknown")
            assets = data.get("assets", [])
            
            whl_url = None
            for asset in assets:
                if asset["name"].endswith(".whl"):
                    whl_url = asset["browser_download_url"]
                    break
            
            if not whl_url:
                click.secho(f"  ✗ No .whl file found in release {tag_name}", fg=RED)
                return

            click.secho(f"  Found release: {tag_name}", fg=GREEN)
            click.secho("  Upgrading package via pip...", fg=CYAN)
            
            # Install the wheel
            install_cmd = [python, "-m", "pip", "install", "--upgrade", whl_url]
            
            # Show output for transparency
            proc = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0:
                click.secho(f"  ✓ Successfully upgraded to {tag_name}", fg=GREEN)
            else:
                click.secho(f"  ✗ Upgrade failed:\n{stderr}", fg=RED)
                return

        except ImportError:
            click.secho("  ✗ 'httpx' library missing (required for updates).", fg=RED)
            return
        except Exception as e:
            click.secho(f"  ✗ Error during update: {e}", fg=RED)
            return

    click.echo()
    click.secho("✓ Update complete!", fg=GREEN)


# ─── WIZARD ──────────────────────────────────────────────────────────

@cli.command()
def wizard():
    """Interactive configurator for FemtoBot (edit config without touching files)."""
    import yaml
    from dotenv import dotenv_values

    config_path = os.path.join(CONFIG_DIR, "config.yaml")
    env_path = os.path.join(CONFIG_DIR, ".env")

    # Load current config
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    # Load current .env
    env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}

    modified = False

    while True:
        click.echo()
        click.secho("=== FemtoBot Wizard ===\n", fg=CYAN, bold=True)
        click.echo("  1. 🐰 Edit Models")
        click.echo("  2. ⚡ Toggle Features")
        click.echo("  3. 📱 Edit Telegram Settings")
        click.echo("  4. 🔌 Edit Integrations (Brave, Gmail)")
        click.echo("  5. 💡 Edit WIZ Lights")
        click.echo("  6. 🧪 Test Services")
        click.echo("  7. 💾 Save & Exit")
        click.echo("  8. ❌ Exit without saving")
        click.echo()

        choice = click.prompt("Choose an option", type=int, default=7)

        if choice == 1:
            # Edit Models
            click.secho("\n--- Edit Models ---\n", fg=CYAN)

            # Try to list available Ollama models
            available = []
            if _check_ollama():
                try:
                    import httpx
                    r = httpx.get("http://localhost:11434/api/tags", timeout=3)
                    available = [m["name"] for m in r.json().get("models", [])]
                    if available:
                        click.secho("  Available Ollama models:", fg=GREEN)
                        for m in available:
                            click.echo(f"    • {m}")
                        click.echo()
                except Exception:
                    pass

            model_keys = [
                ("MODEL", "Chat model", cfg.get("MODEL", "qwen3:8b")),
                ("VISION_MODEL", "Vision model", cfg.get("VISION_MODEL", "qwen3-vl:2b")),
                ("MATH_MODEL", "Math model", cfg.get("MATH_MODEL", "qwen2-math:7b")),
                ("OCR_MODEL", "OCR model", cfg.get("OCR_MODEL", "glm-ocr:latest")),
            ]

            for key, label, current in model_keys:
                new_val = click.prompt(f"  {label}", default=current, show_default=True)
                if new_val != current:
                    cfg[key] = new_val
                    modified = True

            # RAG embedding model
            rag = cfg.get("RAG", {})
            embed = click.prompt("  Embedding model", default=rag.get("EMBEDDING_MODEL", "qwen3-embedding:0.6b"), show_default=True)
            if embed != rag.get("EMBEDDING_MODEL"):
                rag["EMBEDDING_MODEL"] = embed
                cfg["RAG"] = rag
                modified = True

        elif choice == 2:
            # Toggle Features
            click.secho("\n--- Toggle Features ---\n", fg=CYAN)
            features = cfg.get("FEATURES", {})

            feature_labels = {
                "WIZ_LIGHTS": "💡 WIZ Smart Lights",
                "EMAIL_DIGEST": "📧 Email Digest",
                "MATH_SOLVER": "🧮 Math Solver",
                "DEEP_RESEARCH": "🧠 Deep Research",
                "YOUTUBE": "🎥 YouTube",
                "TWITTER": "🐦 Twitter/X",
            }

            for key, label in feature_labels.items():
                current = features.get(key, True)
                status = click.style("ON", fg=GREEN) if current else click.style("OFF", fg=RED)
                new_val = click.confirm(f"  {label} [{status}]", default=current)
                if new_val != current:
                    features[key] = new_val
                    modified = True

            cfg["FEATURES"] = features

        elif choice == 3:
            # Edit Telegram Settings
            click.secho("\n--- Telegram Settings ---\n", fg=CYAN)

            token = click.prompt("  Bot Token", default=env_vars.get("TELEGRAM_TOKEN", ""), show_default=False)
            users = click.prompt("  Authorized Users (comma-separated)", default=env_vars.get("AUTHORIZED_USERS", ""), show_default=True)
            chat_id = click.prompt("  Notification Chat ID", default=env_vars.get("NOTIFICATION_CHAT_ID", ""), show_default=True)

            env_vars["TELEGRAM_TOKEN"] = token
            env_vars["AUTHORIZED_USERS"] = users
            env_vars["NOTIFICATION_CHAT_ID"] = chat_id
            modified = True

        elif choice == 4:
            # Edit Integrations
            click.secho("\n--- Integrations ---\n", fg=CYAN)

            brave = click.prompt("  Brave Search API Key", default=env_vars.get("BRAVE_API_KEY", ""), show_default=False)
            if brave:
                env_vars["BRAVE_API_KEY"] = brave
                modified = True

            gmail = click.prompt("  Gmail User", default=env_vars.get("GMAIL_USER", ""), show_default=False)
            if gmail:
                env_vars["GMAIL_USER"] = gmail
                gmail_pass = click.prompt("  Gmail App Password", default="", hide_input=True, show_default=False)
                if gmail_pass:
                    env_vars["GMAIL_APP_PASSWORD"] = gmail_pass
                modified = True

            # Whisper language
            lang = click.prompt("  Whisper Language", default=cfg.get("WHISPER_LANGUAGE", "en"), show_default=True)
            if lang != cfg.get("WHISPER_LANGUAGE"):
                cfg["WHISPER_LANGUAGE"] = lang
                modified = True

            # Timezone
            tz = click.prompt("  Timezone offset (hours)", default=cfg.get("TIMEZONE_OFFSET_HOURS", -3), type=int, show_default=True)
            if tz != cfg.get("TIMEZONE_OFFSET_HOURS"):
                cfg["TIMEZONE_OFFSET_HOURS"] = tz
                modified = True

        elif choice == 5:
            # Edit WIZ Lights
            click.secho("\n--- WIZ Lights ---\n", fg=CYAN)
            lights = cfg.get("WIZ_LIGHTS", {})

            if lights:
                click.secho("  Current lights:", fg=GREEN)
                for name, ip in lights.items():
                    if isinstance(ip, list):
                        click.echo(f"    • {name} (group): {', '.join(ip)}")
                    else:
                        click.echo(f"    • {name}: {ip}")
                click.echo()

            action = click.prompt("  [a]dd / [r]emove / [d]one", default="d", show_default=True)

            while action.lower() != "d":
                if action.lower() == "a":
                    name = click.prompt("  Light name")
                    ip = click.prompt(f"  IP address for '{name}'")
                    lights[name] = ip
                    click.secho(f"  ✓ Added {name} → {ip}", fg=GREEN)
                    modified = True
                elif action.lower() == "r":
                    name = click.prompt("  Light name to remove")
                    if name in lights:
                        del lights[name]
                        click.secho(f"  ✓ Removed {name}", fg=GREEN)
                        modified = True
                    else:
                        click.secho(f"  ✗ '{name}' not found", fg=RED)

                action = click.prompt("  [a]dd / [r]emove / [d]one", default="d", show_default=True)

            cfg["WIZ_LIGHTS"] = lights

        elif choice == 6:
            # Test Services
            click.secho("\n--- Testing Services ---\n", fg=CYAN)

            # Ollama
            if _check_ollama():
                click.secho("  ✓ Ollama: connected", fg=GREEN)
                try:
                    import httpx
                    r = httpx.get("http://localhost:11434/api/tags", timeout=3)
                    models = [m["name"] for m in r.json().get("models", [])]
                    click.echo(f"    Models: {', '.join(models) if models else 'none downloaded'}")
                except Exception:
                    pass
            else:
                click.secho("  ✗ Ollama: not running", fg=RED)

            # Telegram token
            token = env_vars.get("TELEGRAM_TOKEN", "")
            if token and token != "your_telegram_token_here":
                click.secho("  ✓ Telegram token: set", fg=GREEN)
            else:
                click.secho("  ✗ Telegram token: not set", fg=RED)

            # Gmail
            gmail_user = env_vars.get("GMAIL_USER", "")
            if gmail_user:
                click.secho(f"  ✓ Gmail: configured ({gmail_user})", fg=GREEN)
            else:
                click.secho("  ⚠ Gmail: not configured (optional)", fg=YELLOW)

            # Brave
            brave_key = env_vars.get("BRAVE_API_KEY", "")
            if brave_key:
                click.secho("  ✓ Brave Search: configured", fg=GREEN)
            else:
                click.secho("  ⚠ Brave Search: not configured (optional)", fg=YELLOW)

            # FFmpeg
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
                click.secho("  ✓ FFmpeg: installed", fg=GREEN)
            except (FileNotFoundError, subprocess.CalledProcessError):
                click.secho("  ✗ FFmpeg: not found (needed for audio)", fg=RED)

        elif choice == 7:
            # Save & Exit
            if modified:
                click.secho("\n💾 Saving configuration...", fg=CYAN)

                # Save config.yaml
                try:
                    with open(config_path, "w") as f:
                        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    click.secho("  ✓ config.yaml saved", fg=GREEN)
                except Exception as e:
                    click.secho(f"  ✗ Failed to save config.yaml: {e}", fg=RED)

                # Save .env
                try:
                    with open(env_path, "w") as f:
                        for k, v in env_vars.items():
                            f.write(f"{k}={v}\n")
                    click.secho("  ✓ .env saved", fg=GREEN)
                except Exception as e:
                    click.secho(f"  ✗ Failed to save .env: {e}", fg=RED)

                click.secho("\n✓ Configuration saved! Restart the bot to apply changes.", fg=GREEN, bold=True)
            else:
                click.secho("\nNo changes made.", fg=YELLOW)
            break

        elif choice == 8:
            if modified:
                if not click.confirm("  You have unsaved changes. Exit anyway?", default=False):
                    continue
            click.secho("Exiting without saving.", fg=YELLOW)
            break


# ─── MEMORY ───────────────────────────────────────────────────────────

@cli.group()
def memory():
    """Manage FemtoBot's vector memory (RAG)."""
    pass


@memory.command("search")
@click.argument("query")
@click.option("-n", "--limit", default=5, help="Max results to show")
@click.option("-t", "--type", "collection_type", default="memory",
              type=click.Choice(["memory", "documents"]),
              help="Collection to search")
def memory_search(query, limit, collection_type):
    """Search the vector memory for a query."""
    import asyncio

    sys.path.insert(0, PROJECT_ROOT)

    click.secho(f"🔍 Searching '{query}' in {collection_type}...\n", fg=CYAN)

    async def _search():
        from utils.config_loader import get_all_config
        from src.client import OllamaClient
        from src.memory.vector_store import VectorManager

        vm = VectorManager(get_all_config(), OllamaClient())

        # Use raw ChromaDB query for broader results (ignore threshold)
        query_embedding = await vm._get_embedding(query)
        if not query_embedding:
            click.secho("✗ Failed to generate embedding (is Ollama running?)", fg=RED)
            return

        collection = vm.memory_collection if collection_type == "memory" else vm.documents_collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )

        if not results["documents"] or not results["documents"][0]:
            click.secho("No results found.", fg=YELLOW)
            return

        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0
            similarity = 1 - distance
            # Color based on similarity
            if similarity >= 0.6:
                color = GREEN
            elif similarity >= 0.4:
                color = YELLOW
            else:
                color = RED

            click.secho(f"  [{i+1}] ", fg=CYAN, nl=False)
            click.secho(f"({similarity:.1%}) ", fg=color, nl=False)
            # Truncate long docs
            preview = doc[:120].replace("\n", " ")
            if len(doc) > 120:
                preview += "..."
            click.echo(preview)

    asyncio.run(_search())


@memory.command("status")
def memory_status():
    """Show vector memory statistics."""
    sys.path.insert(0, PROJECT_ROOT)

    click.secho("=== Memory Status ===\n", fg=CYAN, bold=True)

    try:
        import chromadb
        from src.constants import DATA_DIR

        db_path = os.path.join(DATA_DIR, "chroma_db")

        if not os.path.exists(db_path):
            click.secho("  No vector database found yet.", fg=YELLOW)
            return

        client = chromadb.PersistentClient(path=db_path)

        # Memory collection
        try:
            mem = client.get_collection("memory")
            mem_count = mem.count()
            click.secho(f"  🧠 Memories:  {mem_count} entries", fg=GREEN)
        except Exception:
            click.echo("  🧠 Memories:  (collection not created)")

        # Documents collection
        try:
            docs = client.get_collection("documents")
            docs_count = docs.count()
            click.secho(f"  📄 Documents: {docs_count} chunks", fg=GREEN)
        except Exception:
            click.echo("  📄 Documents: (collection not created)")

        # DB size on disk
        total_size = 0
        for dirpath, _, filenames in os.walk(db_path):
            for f in filenames:
                total_size += os.path.getsize(os.path.join(dirpath, f))

        if total_size > 1024 * 1024:
            click.echo(f"  💾 DB size:   {total_size / 1024 / 1024:.1f} MB")
        else:
            click.echo(f"  💾 DB size:   {total_size / 1024:.1f} KB")

        click.echo(f"  📂 Path:      {db_path}")

    except Exception as e:
        click.secho(f"  ✗ Error reading database: {e}", fg=RED)


@memory.command("list")
@click.option("-n", "--limit", default=20, help="Max entries to show")
@click.option("-t", "--type", "collection_type", default="memory",
              type=click.Choice(["memory", "documents"]),
              help="Collection to list")
def memory_list(limit, collection_type):
    """List all stored memories with their IDs."""
    sys.path.insert(0, PROJECT_ROOT)

    click.secho(f"=== {collection_type.title()} Entries ===\n", fg=CYAN, bold=True)

    try:
        import chromadb
        from src.constants import DATA_DIR

        db_path = os.path.join(DATA_DIR, "chroma_db")
        if not os.path.exists(db_path):
            click.secho("  No vector database found.", fg=YELLOW)
            return

        client = chromadb.PersistentClient(path=db_path)

        try:
            collection = client.get_collection(collection_type)
        except Exception:
            click.secho(f"  Collection '{collection_type}' not found.", fg=YELLOW)
            return

        total = collection.count()
        if total == 0:
            click.secho("  No entries found.", fg=YELLOW)
            return

        results = collection.get(limit=limit, include=["documents", "metadatas"])

        for i, (doc_id, doc) in enumerate(zip(results["ids"], results["documents"])):
            preview = doc[:150].replace("\n", " ")
            if len(doc) > 150:
                preview += "..."
            click.secho(f"  [{i+1}] ", fg=CYAN, nl=False)
            click.secho(f"ID: {doc_id}", fg=YELLOW)
            click.echo(f"      {preview}")
            click.echo()

        if total > limit:
            click.secho(f"  ... showing {limit}/{total}. Use -n to show more.", fg=YELLOW)

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg=RED)


@memory.command("delete")
@click.argument("target")
@click.option("--by-id", is_flag=True, help="Delete by exact ID instead of search")
@click.option("-t", "--type", "collection_type", default="memory",
              type=click.Choice(["memory", "documents"]),
              help="Collection to delete from")
def memory_delete(target, by_id, collection_type):
    """Delete a memory by ID or search term.

    Examples:

      femtobot memory delete --by-id "mem_abc123"

      femtobot memory delete "rocopolas creador"
    """
    import asyncio
    sys.path.insert(0, PROJECT_ROOT)

    if by_id:
        # Direct delete by ID
        try:
            import chromadb
            from src.constants import DATA_DIR

            db_path = os.path.join(DATA_DIR, "chroma_db")
            client = chromadb.PersistentClient(path=db_path)
            collection = client.get_collection(collection_type)

            # Check it exists
            existing = collection.get(ids=[target])
            if not existing["ids"]:
                click.secho(f"  ✗ ID '{target}' not found.", fg=RED)
                return

            preview = existing["documents"][0][:100].replace("\n", " ")
            click.secho(f"  Deleting: {preview}...", fg=YELLOW)

            if click.confirm("  Are you sure?"):
                collection.delete(ids=[target])
                click.secho("  ✓ Deleted.", fg=GREEN)
            else:
                click.secho("  Cancelled.", fg=YELLOW)

        except Exception as e:
            click.secho(f"  ✗ Error: {e}", fg=RED)
    else:
        # Search and delete
        async def _search_delete():
            from utils.config_loader import get_all_config
            from src.client import OllamaClient
            from src.memory.vector_store import VectorManager

            vm = VectorManager(get_all_config(), OllamaClient())
            query_embedding = await vm._get_embedding(target)
            if not query_embedding:
                click.secho("  ✗ Failed to generate embedding.", fg=RED)
                return

            collection = vm.memory_collection if collection_type == "memory" else vm.documents_collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
            )

            if not results["documents"] or not results["documents"][0]:
                click.secho("  No matching entries found.", fg=YELLOW)
                return

            click.secho(f"\n  Found {len(results['documents'][0])} matches:\n", fg=CYAN)
            for i, (doc_id, doc) in enumerate(zip(results["ids"][0], results["documents"][0])):
                distance = results["distances"][0][i]
                similarity = 1 - distance
                preview = doc[:120].replace("\n", " ")
                if len(doc) > 120:
                    preview += "..."
                color = GREEN if similarity >= 0.6 else YELLOW if similarity >= 0.4 else RED
                click.secho(f"  [{i+1}] ", fg=CYAN, nl=False)
                click.secho(f"({similarity:.1%}) ", fg=color, nl=False)
                click.echo(preview)
                click.secho(f"      ID: {doc_id}", fg=YELLOW)
                click.echo()

            choice = click.prompt(
                "  Enter number to delete (or 'q' to cancel)",
                default="q"
            )

            if choice.lower() == "q":
                click.secho("  Cancelled.", fg=YELLOW)
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results["ids"][0]):
                    doc_id = results["ids"][0][idx]
                    collection.delete(ids=[doc_id])
                    click.secho(f"  ✓ Deleted entry {doc_id}", fg=GREEN)
                else:
                    click.secho("  ✗ Invalid number.", fg=RED)
            except ValueError:
                click.secho("  ✗ Invalid input.", fg=RED)

        asyncio.run(_search_delete())


# ─── BACKUP / RESTORE ────────────────────────────────────────────────

@cli.command()
@click.option("-o", "--output", default=None, help="Output file path")
def backup(output):
    """Backup data directory (memory, events, instructions)."""
    import tarfile
    from datetime import datetime

    data_dir = DATA_DIR
    config_file = os.path.join(CONFIG_DIR, "config.yaml")
    env_file = os.path.join(CONFIG_DIR, ".env")

    if not os.path.exists(data_dir):
        click.secho("✗ data/ directory not found", fg=RED)
        return

    _ensure_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output or os.path.join(CONFIG_DIR, f"backup_{timestamp}.tar.gz")

    click.secho(f"📦 Creating backup...", fg=CYAN)

    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(data_dir, arcname="data")
        if os.path.exists(config_file):
            tar.add(config_file, arcname="config.yaml")
        if os.path.exists(env_file):
            tar.add(env_file, arcname=".env")

    size = os.path.getsize(backup_path)
    if size > 1024 * 1024:
        size_str = f"{size / 1024 / 1024:.1f} MB"
    else:
        size_str = f"{size / 1024:.1f} KB"

    click.secho(f"✓ Backup created: {backup_path} ({size_str})", fg=GREEN)


@cli.command()
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Overwrite existing files without asking")
def restore(backup_file, force):
    """Restore data from a backup file."""
    import tarfile

    if not tarfile.is_tarfile(backup_file):
        click.secho("✗ Not a valid backup file", fg=RED)
        return

    if not force:
        click.confirm(
            "⚠ This will overwrite current data. Continue?",
            abort=True,
        )

    click.secho(f"📦 Restoring from {backup_file}...", fg=CYAN)

    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=CONFIG_DIR)

    click.secho("✓ Restore complete!", fg=GREEN)
    click.echo("  Restart FemtoBot to apply changes: femtobot restart")


# ─── DOCTOR ───────────────────────────────────────────────────────────

@cli.command()
def doctor():
    """Run diagnostic checks on FemtoBot."""
    import yaml

    click.secho("=== FemtoBot Doctor ===\n", fg=CYAN, bold=True)
    issues = 0

    # 1. Python version
    v = sys.version_info
    if v.major == 3 and v.minor == 12:
        click.secho(f"  ✓ Python {v.major}.{v.minor}.{v.micro}", fg=GREEN)
    else:
        click.secho(f"  ✗ Python {v.major}.{v.minor} (3.12 required)", fg=RED)
        issues += 1
        
        # Auto-install offer
        if click.confirm("  Would you like to try installing Python 3.12 automatically? (Linux only)", default=True):
            try:
                import importlib.resources
                import stat
                
                # Extract script to temp file
                try:
                    # Python 3.9+
                    import src.scripts
                    script_content = importlib.resources.read_text("src.scripts", "install_python.sh")
                except ImportError:
                    # Fallback for older python or dev mode
                    script_path = os.path.join(PROJECT_ROOT, "src", "scripts", "install_python.sh")
                    if os.path.exists(script_path):
                        with open(script_path, "r") as f:
                            script_content = f.read()
                    else:
                        raise FileNotFoundError("Scripts package not found")

                tmp_script = os.path.join(tempfile.gettempdir(), "femtobot_install_python.sh")
                with open(tmp_script, "w") as f:
                    f.write(script_content)
                
                # Make executable
                os.chmod(tmp_script, os.stat(tmp_script).st_mode | stat.S_IEXEC)
                
                click.secho("  Running installer... (requires sudo)", fg=CYAN)
                ret_code = subprocess.call([tmp_script])
                
                if ret_code == 0:
                    click.secho("  ✓ Python 3.12 installed & Environment created!", fg=GREEN)
                    click.secho("  ⚠ To switch to the new version, just run:", fg=YELLOW)
                    click.secho("    source venv_bot/bin/activate", fg=CYAN)
                    click.secho("    femtobot setup", fg=CYAN)
                    return # Exit to force user to switch
                else:
                    click.secho("  ✗ Installation failed.", fg=RED)
                
                # Cleanup
                if os.path.exists(tmp_script):
                    os.remove(tmp_script)
                    
            except Exception as e:
                click.secho(f"  ✗ Failed to run installer: {e}", fg=RED)


    # 2. Venv (Dev mode only)
    from src.constants import IS_DEV_MODE
    if IS_DEV_MODE:
        venv_path = os.path.join(PROJECT_ROOT, "venv_bot")
        if os.path.exists(venv_path):
            click.secho("  ✓ venv_bot exists", fg=GREEN)
        else:
            click.secho("  ✗ venv_bot not found (run ./run.sh first)", fg=RED)
            issues += 1
    else:
         if sys.prefix != sys.base_prefix:
            click.secho("  ✓ Running in venv (pip installed)", fg=GREEN)
         else:
            click.secho("  ⚠ Not running in a virtual environment (recommended)", fg=YELLOW)

    # 3. Config files
    config_path = os.path.join(CONFIG_DIR, "config.yaml")
    env_path = os.path.join(CONFIG_DIR, ".env")

    # 3.1 config.yaml
    if os.path.exists(config_path):
        click.secho("  ✓ config.yaml found", fg=GREEN)
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        click.secho("  ✗ config.yaml missing", fg=RED)
        issues += 1
        cfg = {} # Ensure cfg is defined even if file is missing

    # 3.2 .env
    if os.path.exists(env_path):
        click.secho("  ✓ .env found", fg=GREEN)
        
        # Check specific vars
        from dotenv import dotenv_values
        config = dotenv_values(env_path)
        
        if config.get("TELEGRAM_TOKEN"):
             click.secho("  ✓ TELEGRAM_TOKEN set", fg=GREEN)
        else:
             click.secho("  ✗ TELEGRAM_TOKEN missing", fg=RED)
             issues += 1
             
        if config.get("AUTHORIZED_USERS"):
             click.secho("  ✓ AUTHORIZED_USERS set", fg=GREEN)
        else:
             click.secho("  ✗ AUTHORIZED_USERS missing", fg=RED)
             issues += 1
             
        # Optional warnings
        if config.get("BRAVE_API_KEY"): click.secho("  ✓ BRAVE_API_KEY set", fg=GREEN)
        if config.get("GMAIL_USER"): click.secho("  ✓ GMAIL_USER set", fg=GREEN)
        if config.get("NOTIFICATION_CHAT_ID"): click.secho("  ✓ NOTIFICATION_CHAT_ID set", fg=GREEN)

    else:
        click.secho("  ✗ .env missing", fg=RED)
        issues += 1

    # 4. Data directory
    data_dir = DATA_DIR
    if os.path.exists(data_dir) and os.access(data_dir, os.W_OK):
        click.secho(f"  ✓ data/ writable ({data_dir})", fg=GREEN)
    else:
        click.secho(f"  ✗ data/ missing or not writable ({data_dir})", fg=RED)
        issues += 1

    # 5. Backend connectivity
    backend_cfg = cfg.get("BACKEND", {})
    provider = backend_cfg.get("PROVIDER", "ollama").lower() if isinstance(backend_cfg, dict) else "ollama"
    ollama_url = backend_cfg.get("OLLAMA_URL", "http://localhost:11434") if isinstance(backend_cfg, dict) else "http://localhost:11434"
    lmstudio_url = backend_cfg.get("LMSTUDIO_URL", "http://localhost:1234") if isinstance(backend_cfg, dict) else "http://localhost:1234"
    
    click.secho(f"\n  Backend: {provider}", fg=CYAN, bold=True)
    
    if provider == "lmstudio":
        # Check LM Studio
        try:
            import httpx
            r = httpx.get(f"{lmstudio_url}/v1/models", timeout=3)
            if r.status_code == 200:
                click.secho(f"  ✓ LM Studio running at {lmstudio_url}", fg=GREEN)
                models_data = r.json().get("data", [])
                if models_data:
                    for m in models_data:
                        click.secho(f"    • {m.get('id', 'unknown')}", fg=GREEN)
                else:
                    click.secho("    ⚠ No models loaded in LM Studio", fg=YELLOW)
            else:
                click.secho(f"  ✗ LM Studio returned status {r.status_code}", fg=RED)
                issues += 1
        except Exception:
            click.secho(f"  ✗ LM Studio not reachable at {lmstudio_url}", fg=RED)
            issues += 1
    else:
        # Ollama mode (original logic)
        if _check_ollama():
            click.secho(f"  ✓ Ollama running at {ollama_url}", fg=GREEN)
            
            # Check models
            models = [
                ("MODEL", cfg.get("MODEL")),
                ("VISION_MODEL", cfg.get("VISION_MODEL")),
                ("MATH_MODEL", cfg.get("MATH_MODEL")),
                ("OCR_MODEL", cfg.get("OCR_MODEL")),
                ("EMBEDDING", cfg.get("RAG", {}).get("EMBEDDING_MODEL"))
            ]
            
            available_models = []
            try:
                import httpx
                resp = httpx.get(f"{ollama_url}/api/tags", timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    available_models = [m["name"] for m in data.get("models", [])]
            except:
                 pass
                
            for name, model_name in models:
                if not model_name: continue
                
                found = any(model_name in avail for avail in available_models)
                
                if found:
                    click.secho(f"  ✓ {name}: {model_name} found", fg=GREEN)
                else:
                    click.secho(f"  ✗ {name}: {model_name} (not downloaded — run 'femtobot setup')", fg=RED)
                    issues += 1
        else:
            click.secho(f"  ✗ Ollama not running at {ollama_url}", fg=RED)
            issues += 1

    # 7. FFmpeg
    click.echo()
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        click.secho("  ✓ FFmpeg installed", fg=GREEN)
    except (FileNotFoundError, subprocess.CalledProcessError):
        click.secho("  ✗ FFmpeg not found (needed for audio)", fg=RED)
        issues += 1

    # 8. ChromaDB
    try:
        import chromadb
        click.secho(f"  ✓ ChromaDB {chromadb.__version__}", fg=GREEN)
    except ImportError:
        click.secho("  ✗ ChromaDB not installed", fg=RED)
        issues += 1

    # 9. Crawl4AI + Playwright
    try:
        import crawl4ai
        click.secho(f"  ✓ Crawl4AI {crawl4ai.__version__}", fg=GREEN)
    except (ImportError, AttributeError):
        try:
            import crawl4ai
            click.secho("  ✓ Crawl4AI installed", fg=GREEN)
        except ImportError:
            click.secho("  ✗ Crawl4AI not installed (pip install crawl4ai)", fg=RED)
            issues += 1

    # Check Playwright Chromium browser
    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True, timeout=5
        )
        # Fallback: just check if the binary exists
        import glob
        chromium_paths = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium*/chrome-linux*/chrome"))
        if chromium_paths:
            click.secho("  ✓ Playwright Chromium browser installed", fg=GREEN)
        else:
            click.secho("  ✗ Playwright Chromium not found (run: playwright install chromium)", fg=YELLOW)
            issues += 1
    except Exception:
        click.secho("  ⚠ Could not verify Playwright browser", fg=YELLOW)

    # Summary
    click.echo()
    if issues == 0:
        click.secho("  🎉 All checks passed!", fg=GREEN, bold=True)
    else:
        click.secho(f"  ⚠ {issues} issue(s) found", fg=YELLOW, bold=True)


if __name__ == "__main__":
    cli()

