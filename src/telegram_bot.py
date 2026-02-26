"""Main Telegram bot for FemtoBot - Refactored modular version."""
import os
import re
import sys
import asyncio
import logging
import signal
import atexit
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)
from telegram.error import BadRequest, Conflict

# Add parent directory to path
_ABS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ABS_ROOT)

# Absolute project root (works from any working directory)
PROJECT_ROOT = _ABS_ROOT
from src.constants import CONFIG_DIR

# Import modular components
from src.state.chat_manager import ChatManager
from src.client import OllamaClient
from src.memory.vector_store import VectorManager
from src.handlers.commands import CommandHandlers
from src.handlers.voice import VoiceHandler
from src.handlers.audio import AudioHandler
from src.handlers.photo import PhotoHandler
from src.handlers.video import VideoHandler
from src.handlers.document import DocumentHandler
from src.jobs.events import EventsJob
from src.jobs.inactivity import InactivityJob
from src.jobs.cleanup import CleanupJob
from src.jobs.email_digest import EmailDigestJob
from src.middleware.rate_limiter import rate_limit

# Import Services
from src.services.rag_service import RagService
from src.services.media_service import MediaService
from src.services.command_service import CommandService
from src.services.message_processor import MessageProcessor

from utils.config_loader import get_config, get_all_config, is_feature_enabled
from utils.logger import setup_logging

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Authorization
AUTHORIZED_USERS_RAW = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS = [int(uid.strip()) for uid in AUTHORIZED_USERS_RAW.split(",") if uid.strip().isdigit()]

NOTIFICATION_CHAT_ID_RAW = os.getenv("NOTIFICATION_CHAT_ID", "")
NOTIFICATION_CHAT_ID = int(NOTIFICATION_CHAT_ID_RAW) if NOTIFICATION_CHAT_ID_RAW.strip().isdigit() else None

# Setup logging
logger = setup_logging(TOKEN)

# Global instances (State)
chat_manager = ChatManager(max_inactive_hours=24)
vector_manager = VectorManager(get_all_config(), OllamaClient())
message_queue = asyncio.Queue()
queue_worker_running = False
last_activity = datetime.now()

# Initialize Services
rag_service = RagService(vector_manager)
media_service = MediaService()

# Initialize email digest job (only if feature enabled)
email_digest_job = EmailDigestJob(notification_chat_id=NOTIFICATION_CHAT_ID) if is_feature_enabled("EMAIL_DIGEST") else None

# Config values
MODEL = get_config("MODEL")
COMMAND_PATTERNS = {
    'memory': re.compile(r':::memory(?!_delete):*\s*(.+?):::', re.DOTALL),
    'memory_delete': re.compile(r':::memory_delete:*\s*(.+?):::', re.DOTALL),
    'cron': re.compile(r':::cron(?!_delete):*\s*(.+?):::', re.DOTALL),
    'cron_delete': re.compile(r':::cron_delete:*\s*(.+?):::'),
    'search': re.compile(r':::search:*\s*(.+?):::', re.DOTALL),
    'foto': re.compile(r':::foto:*\s*(.+?):::', re.IGNORECASE),
    'luz': re.compile(r':::luz:*\s+(\S+)\s+(\S+)(?:\s+(\S+))?:::'),
    'camara': re.compile(r':::camara:*(?:\s+\S+)?:::'),
    'matematicas': re.compile(r':::matematicas:::'),
}

# Initialize Command Service
command_service = CommandService(vector_manager, COMMAND_PATTERNS, CONFIG_DIR)

# Initialize Message Processor
message_processor = MessageProcessor(
    chat_manager=chat_manager,
    rag_service=rag_service,
    media_service=media_service,
    command_service=command_service,
    command_patterns=COMMAND_PATTERNS
)

# System instructions
system_instructions = ""

# PID file handling
PID_FILE = os.path.join(PROJECT_ROOT, ".bot.pid")

def cleanup_pid():
    """Remove PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info("PID file cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up PID file: {e}")

def kill_existing_bot():
    """Kill existing bot instance if running."""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, signal.SIGTERM)
                logger.info(f"Killed existing bot process (PID: {old_pid})")
                import time
                time.sleep(2)
            except ProcessLookupError:
                logger.info(f"No process found with PID {old_pid}")
            except (PermissionError, Exception) as e:
                logger.warning(f"Error killing process {old_pid}: {e}")
    except (ValueError, FileNotFoundError):
        pass

def write_pid():
    """Write current PID to file."""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(cleanup_pid)
        logger.info(f"PID file created: {os.getpid()}")
    except Exception as e:
        logger.error(f"Error writing PID file: {e}")

def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized."""
    if not AUTHORIZED_USERS:
        return False
    return user_id in AUTHORIZED_USERS

def load_instructions():
    """Load system instructions from file."""
    global system_instructions
    try:
        from src.constants import CONFIG_DIR
        instructions_path = os.path.join(CONFIG_DIR, get_config("INSTRUCTIONS_FILE"))
        with open(instructions_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                system_instructions = content
                logger.info("Instructions loaded successfully")
    except FileNotFoundError:
        logger.warning("Instructions file not found")
    except Exception as e:
        logger.error(f"Error loading instructions: {e}")

def get_system_prompt():
    """Get system instructions."""
    return system_instructions if system_instructions else ""

def update_activity():
    """Update last activity timestamp."""
    global last_activity
    last_activity = datetime.now()

# Initialize handlers
command_handlers = CommandHandlers(
    chat_manager=chat_manager,
    is_authorized_func=is_authorized,
    get_system_prompt_func=get_system_prompt,
    email_digest_job=email_digest_job,
    update_activity_func=update_activity
)

voice_handler = VoiceHandler(
    is_authorized_func=is_authorized,
    message_queue=message_queue,
    start_worker_func=None  # Will be set later
)

audio_handler = AudioHandler(is_authorized_func=is_authorized)

photo_handler = PhotoHandler(
    chat_manager=chat_manager,
    is_authorized_func=is_authorized,
    get_system_prompt_func=get_system_prompt,
    command_patterns=COMMAND_PATTERNS
)

video_handler = VideoHandler(
    chat_manager=chat_manager,
    is_authorized_func=is_authorized,
    get_system_prompt_func=get_system_prompt,
    command_patterns=COMMAND_PATTERNS
)

document_handler = DocumentHandler(
    chat_manager=chat_manager,
    vector_manager=vector_manager,
    is_authorized_func=is_authorized,
    get_system_prompt_func=get_system_prompt,
    command_patterns=COMMAND_PATTERNS
)

async def queue_worker():
    """Process messages from queue."""
    global queue_worker_running, last_activity
    
    try:
        while True:
            try:
                item = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                update, context, needs_reply = item[0], item[1], item[2]
                text_override = item[3] if len(item) > 3 else None
            except asyncio.TimeoutError:
                return
            
            last_activity = datetime.now()
            try:
                # Initialize chat in ChatManager if needed (redundant check but safe)
                chat_id = update.effective_chat.id
                history = await chat_manager.get_history(chat_id)
                if not history:
                     await chat_manager.initialize_chat(chat_id, get_system_prompt())
                
                # Determine text
                text = text_override or update.message.text
                
                # Process with MessageProcessor
                await message_processor.process_message(update, context, text, use_reply=needs_reply)
                
            except Exception as e:
                logger.error(f"Error processing text message in queue: {e}", exc_info=True)
                try:
                    chat_id = update.effective_chat.id
                    await context.bot.send_message(chat_id, f"❌ Error processing message: {e}")
                except Exception:
                    pass
            
            message_queue.task_done()
    finally:
        queue_worker_running = False

def start_worker_if_needed():
    global queue_worker_running
    if not queue_worker_running:
        queue_worker_running = True
        asyncio.create_task(queue_worker())

voice_handler.start_worker = start_worker_if_needed

@rate_limit(max_messages=10, window_seconds=60)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text(
            f"⛔ Access denied. Your ID: `{user_id}`",
            parse_mode="Markdown"
        )
        return
    
    needs_reply = not message_queue.empty()
    await message_queue.put((update, context, needs_reply, None))
    start_worker_if_needed()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for unhandled exceptions."""
    error = context.error
    if isinstance(error, Conflict):
        logger.warning("Conflict detected - another bot instance is running. Retrying...")
        return
    
    logger.error(f"Unhandled exception: {error}", exc_info=error)
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                f"❌ Unexpected error: {error}"
            )
        except Exception:
            pass

def _validate_startup():
    """Pre-flight checks before starting the bot."""
    errors = []
    
    if not TOKEN or TOKEN == "your_telegram_token_here":
        errors.append("TELEGRAM_TOKEN is not set or is still the placeholder value")
    
    if not AUTHORIZED_USERS:
        errors.append("AUTHORIZED_USERS is empty — no one will be able to use the bot")
    
    # Check backend connectivity
    backend_cfg = get_config("BACKEND") or {}
    provider = (backend_cfg.get("PROVIDER", "ollama") if isinstance(backend_cfg, dict) else "ollama").lower()
    ollama_url = backend_cfg.get("OLLAMA_URL", "http://localhost:11434") if isinstance(backend_cfg, dict) else "http://localhost:11434"
    lmstudio_url = backend_cfg.get("LMSTUDIO_URL", "http://localhost:1234") if isinstance(backend_cfg, dict) else "http://localhost:1234"
    
    try:
        import httpx
        if provider == "lmstudio":
            # Check LM Studio
            r = httpx.get(f"{lmstudio_url}/v1/models", timeout=3)
            if r.status_code != 200:
                errors.append(f"LM Studio returned non-200 status at {lmstudio_url}")
        else:
            r = httpx.get(f"{ollama_url}/api/tags", timeout=3)
            if r.status_code != 200:
                errors.append("Ollama returned non-200 status")
    except Exception:
        if provider == "lmstudio":
            errors.append(f"LM Studio is not reachable at {lmstudio_url} — make sure it is running")
        else:
            errors.append(f"Ollama is not reachable at {ollama_url} — run 'ollama serve'")
    
    if errors:
        print("\n❌ FemtoBot startup failed:\n")
        for err in errors:
            print(f"  • {err}")
        print("\n💡 Run 'femtobot doctor' for a full diagnostic.\n")
        sys.exit(1)
    else:
        logger.info(f"Backend: {provider} ({lmstudio_url if provider == 'lmstudio' else ollama_url})")


def main():
    """Main entry point."""
    _validate_startup()
    kill_existing_bot()
    write_pid()
    load_instructions()
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_error_handler(error_handler)
    
    # Command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("new", command_handlers.new_conversation))
    application.add_handler(CommandHandler("status", command_handlers.status))
    application.add_handler(CommandHandler("unload", command_handlers.unload_models))
    application.add_handler(CommandHandler("restart", command_handlers.restart_bot))
    application.add_handler(CommandHandler("stop", command_handlers.stop_bot))
    if is_feature_enabled("EMAIL_DIGEST") and email_digest_job:
        application.add_handler(CommandHandler("digest", command_handlers.email_digest))
    if is_feature_enabled("DEEP_RESEARCH"):
        application.add_handler(CommandHandler("deep", command_handlers.deep_research))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.VOICE, voice_handler.handle))
    application.add_handler(MessageHandler(filters.AUDIO, audio_handler.handle))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler.handle))
    application.add_handler(MessageHandler(filters.VIDEO, video_handler.handle))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler.handle))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Background jobs
    if NOTIFICATION_CHAT_ID:
        events_job = EventsJob(
            notification_chat_id=NOTIFICATION_CHAT_ID,
            authorized_users=AUTHORIZED_USERS
        )
        application.job_queue.run_repeating(
            events_job.run,
            interval=events_job.interval_seconds,
            first=1,
            name=events_job.name
        )
    
    inactivity_job = InactivityJob(
        get_last_activity_func=lambda: last_activity,
        model=MODEL
    )
    application.job_queue.run_repeating(
        inactivity_job.run,
        interval=inactivity_job.interval_seconds,
        first=300,
        name=inactivity_job.name
    )
    
    cleanup_job = CleanupJob(chat_manager=chat_manager)
    application.job_queue.run_repeating(
        cleanup_job.run,
        interval=cleanup_job.interval_seconds,
        first=3600,
        name=cleanup_job.name
    )
    
    if NOTIFICATION_CHAT_ID and is_feature_enabled("EMAIL_DIGEST") and email_digest_job:
        application.job_queue.run_repeating(
            email_digest_job.run,
            interval=email_digest_job.interval_seconds,
            first=60,
            name=email_digest_job.name
        )
        logger.info("Email digest job scheduled")
    
    logger.info("FemtoBot started successfully!")
    
    # Run with conflict retry logic
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            application.run_polling()
            break
        except Conflict as e:
            if attempt < max_retries - 1:
                logger.warning(f"Conflict on attempt {attempt + 1}, retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached, could not start bot")
                raise

if __name__ == "__main__":
    main()
