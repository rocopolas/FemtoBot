"""
Command Service for handling internal bot commands (Cron, Memory, Lights).
"""
import re
import os
import logging
from typing import List, Dict, Any, Pattern

from utils.cron_utils import CronUtils
from utils.wiz_utils import control_light
from utils.config_loader import get_config, is_feature_enabled
from utils.telegram_utils import escape_code

logger = logging.getLogger(__name__)

class CommandService:
    def __init__(self, vector_manager, command_patterns: Dict[str, Pattern], config_dir: str):
        self.vector_manager = vector_manager
        self.patterns = command_patterns
        self.config_dir = config_dir
        self.events_file = os.path.join(config_dir, get_config("EVENTS_FILE"))

    async def process_commands(self, response_text: str, chat_id: int, context) -> bool:
        """
        Process commands embedded in LLM response.
        Returns True if any commands were processed.
        """
        # Strip thinking tags to prevent executing commands from within <think> blocks
        response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
        response_text = re.sub(r'<think>.*', '', response_text, flags=re.DOTALL)
        
        commands_processed = False
        
        # 1. Cron Delete
        if await self._handle_cron_delete(response_text, chat_id, context):
            commands_processed = True
            
        # 2. Cron Add
        if await self._handle_cron_add(response_text, chat_id, context):
            commands_processed = True
            
        # 3. Memory Delete
        if await self._handle_memory_delete(response_text, chat_id, context):
            commands_processed = True
            
        # 4. Memory Add
        if await self._handle_memory_add(response_text, chat_id, context):
            commands_processed = True
            
        # 5. Light Control
        if is_feature_enabled("WIZ_LIGHTS"):
            if await self._handle_light_control(response_text, chat_id, context):
                commands_processed = True
            
        return commands_processed

    async def _handle_cron_delete(self, text: str, chat_id: int, context) -> bool:
        processed = False
        for match in self.patterns['cron_delete'].finditer(text):
            processed = True
            target = match.group(1).strip()
            target_esc = escape_code(target)
            await context.bot.send_message(
                chat_id,
                f"🗑️ Removing: `{target_esc}`",
                parse_mode="Markdown"
            )
            if CronUtils.delete_job(target):
                await context.bot.send_message(chat_id, "✅ Task removed.")
            else:
                await context.bot.send_message(chat_id, "⚠️ No matching tasks found.")
        return processed

    def _unescape_telegram_markdown(self, text: str) -> str:
        """Unescape Telegram Markdown characters."""
        # Unescape characters preceded by backslash
        return re.sub(r'\\(.)', lambda m: m.group(1), text)

    async def _handle_cron_add(self, text: str, chat_id: int, context) -> bool:
        processed = False
        for match in self.patterns['cron'].finditer(text):
            processed = True
            cron_content = match.group(1).strip()
            
            # Unescape first
            cron_content = self._unescape_telegram_markdown(cron_content)
            logger.info(f"[CRON] Raw content: '{cron_content}'")
            
            # New simplified format: tipo minuto hora dia mes nombre
            parts = cron_content.split(None, 5)
            if len(parts) < 6:
                logger.error(f"[CRON] Invalid cron format: {cron_content}")
                await context.bot.send_message(chat_id, "❌ Error: Invalid cron format (expected: type min hour day month name).")
                continue
            
            tipo = parts[0].lower()  # "unico" or "recurrente"
            min_f, hour_f, day_f, month_f = parts[1:5]
            nombre = parts[5].strip().rstrip(":")
            
            if tipo not in ("unico", "recurrente"):
                logger.error(f"[CRON] Invalid type: {tipo}")
                await context.bot.send_message(chat_id, f"❌ Error: Invalid type '{tipo}'. Use 'unico' or 'recurrente'.")
                continue
            
            schedule = f"{min_f} {hour_f} {day_f} {month_f} *"
            
            # Build command automatically from nombre
            import shlex
            import sys
            
            # Use the current python executable to run the script
            python_exe = sys.executable
            script_module = "src.scripts.trigger_notification"
            
            # Quote the message to be safe for shell
            safe_nombre = shlex.quote(nombre)
            
            # The command that cron will execute
            # We use the module execution properly
            # We must ensure we are in the project root, so we cd there first? 
            # Or we use absolute path.
            # Let's assume the cron runs from user home or we provide full path.
            # Safest is to use the full path to python and project root.
            
            # However, simpler if we just assume standard environment or RELATIVE if run from root.
            # But cron runs from home usually.
            # Let's use the PROJECT_ROOT we can infer or pass.
            
            # Actually, let's just use the absolute path to the project if possible.
            # CommandService doesn't have PROJECT_ROOT handy unless we pass it.
            # We can use os.getcwd() if we assume the bot is running from root when adding,
            # but cron runs later.
            
            cwd = os.getcwd()
            
            base_command = f'cd {cwd} && {python_exe} -m {script_module} {safe_nombre}'
            
            if tipo == "unico":
                from datetime import datetime
                year = datetime.now().year
                # Keep the date check for year safety
                command = (
                    f'[ "$(date +\\%Y)" = "{year}" ] && '
                    f'{base_command}'
                )
            else:
                command = base_command
            
            sched_esc = escape_code(schedule)
            nombre_esc = escape_code(nombre)
            
            await context.bot.send_message(
                chat_id,
                f"⚠️ Adding ({tipo}): `{sched_esc}` — {nombre_esc}",
                parse_mode="Markdown"
            )
            
            success = CronUtils.add_job(schedule, command)
            if success:
                await context.bot.send_message(chat_id, "✅ Task added.")
            else:
                await context.bot.send_message(chat_id, "❌ Error adding task.")
        return processed

    async def _handle_memory_delete(self, text: str, chat_id: int, context) -> bool:
        processed = False
        for match in self.patterns['memory_delete'].finditer(text):
            processed = True
            target = match.group(1).strip()
            if target:
                try:
                    if await self.vector_manager.delete_memory(target):
                        await context.bot.send_message(chat_id, f"🗑️ Memory deleted: _{target}_", parse_mode="Markdown")
                    else:
                        await context.bot.send_message(chat_id, f"⚠️ No similar memories found for: _{target}_", parse_mode="Markdown")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"⚠️ Error deleting memory: {str(e)}")
        return processed

    async def _handle_memory_add(self, text: str, chat_id: int, context) -> bool:
        processed = False
        for match in self.patterns['memory'].finditer(text):
            processed = True
            content = match.group(1).strip()
            if content:
                try:
                    if await self.vector_manager.add_memory(content):
                        await context.bot.send_message(chat_id, f"💾 Saved (DB): _{content}_", parse_mode="Markdown")
                    else:
                        await context.bot.send_message(chat_id, "❌ Error saving to DB.")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"⚠️ Error: {str(e)}")
        return processed

    async def _handle_light_control(self, text: str, chat_id: int, context) -> bool:
        processed = False
        for match in self.patterns['luz'].finditer(text):
            processed = True
            name = match.group(1).strip()
            action = match.group(2).strip()
            value = match.group(3).strip() if match.group(3) else None
            
            result = await control_light(name, action, value)
            await context.bot.send_message(chat_id, result)
        return processed
