from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Input, Header, Footer, Static, Markdown
import re
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import OllamaClient
from utils.cron_utils import CronUtils
from utils.search_utils import BraveSearch
from utils.config_loader import get_config

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MessageWidget(Markdown):
    def __init__(self, content, is_user=False, timestamp=None, extra_classes=None):
        # User messages get timestamp immediately. Bot messages wait until finish.
        if is_user and timestamp is None:
            self.timestamp = datetime.now().strftime("%H:%M")
        else:
            self.timestamp = timestamp
            
        super().__init__(content) # Pass raw content to avoid duplication in update
        self.is_user = is_user
        self.add_class("message")
        if is_user:
            self.add_class("user-message")
        else:
            self.add_class("bot-message")
            
        if extra_classes:
            self.add_class(extra_classes)
            
    def format_content(self, content):
        """Formats special tags effectively for TUI."""
        # Strip ANSI escape codes
        content = re.sub(r'\x1b\[[0-9;]*m', '', content)
        
        # Replace <think> blocks with blockquotes
        content = content.replace("<think>", "> 🧠 **Pensando:**\n> ")
        content = content.replace("</think>", "\n\n")
        
        # Append timestamp if it exists
        if self.timestamp:
            content += f"  \n_{self.timestamp}_"
        return content

    async def update(self, content):
        await super().update(self.format_content(content))

class LocalBotApp(App):
    CSS_PATH = os.path.join(PROJECT_ROOT, "assets", "styles.tcss")
    TITLE = "LocalBot TUI"
    SUB_TITLE = "Powered by Ollama"
    
    def __init__(self):
        super().__init__()
        self.client = OllamaClient()
        self.chat_history = []
        self.model = get_config("MODEL")
        
        # File watcher state
        self.events_file = os.path.join(PROJECT_ROOT, get_config("EVENTS_FILE"))
        
        # Ensure file exists
        if not os.path.exists(self.events_file):
            open(self.events_file, 'w').close()

        # Load system instructions
        try:
            instructions_path = os.path.join(PROJECT_ROOT, get_config("INSTRUCTIONS_FILE"))
            with open(instructions_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    self.chat_history.append({"role": "system", "content": content})
        except FileNotFoundError:
            pass 

    def on_mount(self):
        """Called when app starts."""
        self.set_interval(2.0, self.check_events)

    async def check_events(self):
        """Checks for new lines in events.txt and clears them."""
        try:
            if os.path.getsize(self.events_file) > 0:
                with open(self.events_file, 'r+', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        # Display messages
                        for line in content.strip().split('\n'):
                            if line.strip():
                                container = self.query_one("#chat-container")
                                event_msg = Vertical(classes="message-container bot-container")
                                await container.mount(event_msg)
                                # Events get immediate timestamp
                                now_str = datetime.now().strftime("%H:%M")
                                await event_msg.mount(MessageWidget(f"🔔 {line.strip()}", is_user=False, timestamp=now_str))
                        
                        # Clear file
                        f.seek(0)
                        f.truncate()
                        container = self.query_one("#chat-container")
                        container.scroll_end(animate=True)
        except Exception:
            pass

    async def on_unmount(self):
        """Called when the app is exiting."""
        if self.model:
            await self.client.unload_model(self.model)

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="chat-container")
        yield Input(placeholder="Escribe tu mensaje... (Escribe 'salir' para cerrar)", id="chat-input")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted):
        message = event.value.strip()
        if not message:
            return

        if message.lower() in ["salir", "exit", "quit"]:
            self.exit()
            return
            
        event.input.value = ""
        container = self.query_one("#chat-container")
        
        # User message
        user_container = Vertical(classes="message-container user-container")
        await container.mount(user_container)
        await user_container.mount(MessageWidget(message, is_user=True))
        
        # Update history with timestamp and schedule context for the LLM
        current_time_str = datetime.now().strftime("%H:%M del %d/%m/%Y")
        crontab_lines = CronUtils.get_crontab()
        crontab_str = "\n".join(crontab_lines) if crontab_lines else "(vacío)"
        context_message = f"{message} [Sistema: La hora actual es {current_time_str}. Agenda actual (crontab):\n{crontab_str}]"
        self.chat_history.append({"role": "user", "content": context_message})
        
        # Bot placeholder
        bot_container = Vertical(classes="message-container bot-container")
        await container.mount(bot_container)
        bot_widget = MessageWidget("...", is_user=False) # No timestamp initially
        await bot_container.mount(bot_widget)
        
        # Scroll to bottom
        container.scroll_end(animate=True)
        
        # Stream response
        self.run_worker(self.stream_response(bot_widget, self.chat_history))
        
    async def stream_response(self, widget, history):
        full_response = ""
        
        first_chunk = True
        async for chunk in self.client.stream_chat(self.model, history):
            if first_chunk:
                full_response = "" # Clear "..."
                first_chunk = False
            full_response += chunk
            await widget.update(full_response)
            self.query_one("#chat-container").scroll_end(animate=False)
            
        # Finish response - Set timestamp NOW
        widget.timestamp = datetime.now().strftime("%H:%M")
        await widget.update(full_response)
        
        # --- Search Command Handling ---
        search_match = re.search(r":::search\s+(.+?):::", full_response)
        if search_match:
            search_query = search_match.group(1).strip()
            
            # Show search message
            search_msg = Vertical(classes="message-container bot-container")
            await self.query_one("#chat-container").mount(search_msg)
            now_str = datetime.now().strftime("%H:%M")
            await search_msg.mount(MessageWidget(f"🔍 Buscando: `{search_query}`...", is_user=False, timestamp=now_str))
            
            # Execute search
            search_results = await BraveSearch.search(search_query)
            
            # Inject results into history
            self.chat_history.append({"role": "assistant", "content": full_response})
            self.chat_history.append({"role": "user", "content": f"[Sistema: Resultados de búsqueda para '{search_query}']:\n{search_results}\n\nAhora responde al usuario con esta información."})
            
            # Get final response from LLM
            final_widget = MessageWidget("...", is_user=False)
            result_container = Vertical(classes="message-container bot-container")
            await self.query_one("#chat-container").mount(result_container)
            await result_container.mount(final_widget)
            
            final_response = ""
            async for chunk in self.client.stream_chat(self.model, self.chat_history):
                final_response += chunk
                await final_widget.update(final_response)
            
            final_widget.timestamp = datetime.now().strftime("%H:%M")
            await final_widget.update(final_response)
            self.chat_history.append({"role": "assistant", "content": final_response})
            self.query_one("#chat-container").scroll_end(animate=True)
            return  # Skip normal cron parsing
        
        # Append to history for context
        self.chat_history.append({"role": "assistant", "content": full_response})

        # Check for delete commands
        for delete_match in re.finditer(r":::cron_delete\s+(.+?):::", full_response):
            target = delete_match.group(1).strip()
            
            # Notify user
            system_msg = Vertical(classes="message-container bot-container")
            await self.query_one("#chat-container").mount(system_msg)
            now_str = datetime.now().strftime("%H:%M")
            await system_msg.mount(MessageWidget(f"🗑️  Eliminando tarea que contenga: `{target}`", is_user=False, timestamp=now_str))
            
            if CronUtils.delete_job(target):
                success_msg = Vertical(classes="message-container bot-container")
                await self.query_one("#chat-container").mount(success_msg)
                await success_msg.mount(MessageWidget(f"✅ Tarea eliminada con éxito.", is_user=False, timestamp=now_str, extra_classes="success-message"))
            else:
                fail_msg = Vertical(classes="message-container bot-container")
                await self.query_one("#chat-container").mount(fail_msg)
                await fail_msg.mount(MessageWidget(f"⚠️ No se encontraron tareas coincidentes.", is_user=False, timestamp=now_str, extra_classes="error-message"))
                
            self.query_one("#chat-container").scroll_end(animate=True)

        # Check for adding commands
        for cron_match in re.finditer(r":::cron\s+(.+?)\s+(.+?):::", full_response):
            schedule = cron_match.group(1).strip()
            command = cron_match.group(2).strip()
            
            # Robustness: Remove trailing colon if accidentally included by LLM
            if command.endswith(":"):
               command = command[:-1].strip()
            
            # Notify user
            system_msg = Vertical(classes="message-container bot-container")
            await self.query_one("#chat-container").mount(system_msg)
            now_str = datetime.now().strftime("%H:%M")
            await system_msg.mount(MessageWidget(f"⚠️  Agregando tarea Cron: `{schedule} {command}`", is_user=False, timestamp=now_str))
            
            if CronUtils.add_job(schedule, command):
                success_msg = Vertical(classes="message-container bot-container")
                await self.query_one("#chat-container").mount(success_msg)
                await success_msg.mount(MessageWidget(f"✅ Tarea agregada con éxito.", is_user=False, timestamp=now_str, extra_classes="success-message"))
            else:
                fail_msg = Vertical(classes="message-container bot-container")
                await self.query_one("#chat-container").mount(fail_msg)
                await fail_msg.mount(MessageWidget(f"❌ Error al agregar tarea.", is_user=False, timestamp=now_str, extra_classes="error-message"))
                
                
            self.query_one("#chat-container").scroll_end(animate=True)
