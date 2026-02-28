"""
Message Processor Service.
Encapsulates the logic for processing user messages, including:
- Intent detection
- RAG retrieval
- LLM generation
- Media handling
- Command execution
"""
import os
import re
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.client import OllamaClient
from src.state.chat_manager import ChatManager
from src.services.rag_service import RagService
from src.services.media_service import MediaService
from src.services.command_service import CommandService
from src.services.upload_service import UploadService

from utils.cron_utils import CronUtils
from utils.config_loader import get_config, is_feature_enabled
from utils.telegram_utils import split_message, format_bot_response, prune_history, telegramify_content, send_telegramify_results, stream_to_telegram
from utils.search_utils import WebSearch

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(
        self, 
        chat_manager: ChatManager, 
        rag_service: RagService,
        media_service: MediaService,
        command_service: CommandService,
        command_patterns: Dict[str, re.Pattern]
    ):
        self.chat_manager = chat_manager
        self.rag_service = rag_service
        self.media_service = media_service
        self.command_service = command_service
        self.command_patterns = command_patterns
        self.upload_service = UploadService()
        
        # We initialize OllamaClient here or per request? 
        # Client handles its own connection pooling, so it's fine to instantiate text processing here.
        self.ollama_client = OllamaClient()

    async def process_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_text: str, 
        use_reply: bool = True # Kept for compatibility but default True effectively
    ):
        """
        Main entry point for processing a message.
        Always replies to the user message unless impossible.
        """
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        
        if not user_text or not user_text.strip():
            await context.bot.send_message(chat_id, "⚠️ No text detected.")
            return

        # 1. Initialize chat history if needed
        history = await self.chat_manager.get_history(chat_id)
        if not history:
            # We need a way to get system prompt. passing it in init or fetching?
            # Ideally passed in init, but it might change? 
            # Let's assume initialized externally or we fetch it.
            # For now, let's skip re-init here or assume it's done by caller/ChatManager handle it.
            # But ChatManager needs it.
            pass 

        placeholder_msg = None

        # 2. Check for Upload Intent (Reply)
        if update.message.reply_to_message:
            processed = await self._handle_reply_upload(update, context, user_text)
            if processed:
                return

        # 3. Check for Media Intent (Twitter/YouTube)
        if self.media_service.is_media_url(user_text):
            processed, transcription_request = await self._handle_media_intent(update, context, user_text, chat_id)
            if processed and not transcription_request:
                return
            if transcription_request:
                # If transcription happened, we proceed to LLM with the transcription result
                user_text = transcription_request
                # And we likely have a status msg we can reuse? 
                # For simplicity, _handle_media_intent returns (processed: bool, new_text: str|None)

        # 4. LLM Generation
        
        # Send typing action
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        if not placeholder_msg: 
             # Only reply to the message if use_reply is True (queue backlog)
             # Otherwise behave like normal (no quote)
             try:
                if use_reply:
                    placeholder_msg = await context.bot.send_message(
                         chat_id=chat_id, 
                         text="🧠 RAG...", 
                         reply_to_message_id=message_id
                    )
                else:
                    placeholder_msg = await context.bot.send_message(
                         chat_id=chat_id, 
                         text="🧠 RAG..."
                    )
             except Exception:
                # Fallback
                placeholder_msg = await context.bot.send_message(chat_id=chat_id, text="🧠 RAG...")

        # Prepare RAG context
        current_time = datetime.now().strftime("%H:%M del %d/%m/%Y")
        crontab_str = CronUtils.get_readable_agenda()
        rag_context = await self.rag_service.get_context(user_text)
        
        context_message = f"{user_text} [System: Current time is {current_time}. Schedule: {crontab_str}.{rag_context}]"
        await self.chat_manager.append_message(chat_id, {"role": "user", "content": context_message})

        try:
            await placeholder_msg.edit_text("🧠 LLM...")
            
            # Streaming LLM
            history = await self.chat_manager.get_history(chat_id)
            model = get_config("MODEL")
            context_limit = get_config("CONTEXT_LIMIT", 30000)
            
            # Ensure model is strictly loaded with our parameters
            await self.ollama_client.load_model(model)
            
            pruned_history = prune_history(history, context_limit)
            
            full_response = await stream_to_telegram(
                self.ollama_client.stream_chat(model, pruned_history),
                placeholder_msg
            )
            
            # 5. Handle Specialized Commands (Math / Search) within LLM response
            full_response = await self._post_process_llm_response(
                full_response, chat_id, context, placeholder_msg, user_text, pruned_history
            )
            
            # 6. Final Response Sending
            # Clean text (remove internal commands tokens like :::search...:::)
            cleaned_text = format_bot_response(full_response)
            
            # Determine if we should force reply in final message as well
            final_reply_id = message_id if use_reply else None

            if not cleaned_text:
                # If only commands were executed and no text remains
                await placeholder_msg.delete()
            else:
                chunks = await telegramify_content(cleaned_text)
                # Pass reply_to_message_id only if use_reply is True
                await send_telegramify_results(context, chat_id, chunks, placeholder_msg, reply_to_message_id=final_reply_id)
            
            await self.chat_manager.append_message(chat_id, {"role": "assistant", "content": full_response})
            
            # 7. Process System Commands (Cron, Memory, etc)
            commands_processed = await self.command_service.process_commands(full_response, chat_id, context)
            
            if not cleaned_text and commands_processed:
                try:
                     # Send confirmation
                     await context.bot.send_message(
                         chat_id, 
                         "✅ Commands executed successfully.", 
                         reply_to_message_id=final_reply_id
                     )
                except Exception:
                     pass

        except Exception as e:
            logger.error(f"Error in LLM processing: {e}", exc_info=True)
            try:
                await placeholder_msg.edit_text(f"❌ Error: {str(e)}")
            except:
                await context.bot.send_message(chat_id, f"❌ Error: {str(e)}")

    async def _handle_reply_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
        """Handle reply to upload file to Catbox."""
        replied_msg = update.message.reply_to_message
        if not replied_msg:
            return False
            
        if self.upload_service.is_upload_intent(user_text):
            media_file = None
            media_type = None
            ext = ".tmp"
            
            if replied_msg.photo:
                media_file = await context.bot.get_file(replied_msg.photo[-1].file_id)
                media_type = "image"
                ext = ".jpg"
            elif replied_msg.video:
                media_file = await context.bot.get_file(replied_msg.video.file_id)
                media_type = "video"
                ext = ".mp4"
            elif replied_msg.document:
                 media_file = await context.bot.get_file(replied_msg.document.file_id)
                 media_type = "document"
                 ext = os.path.splitext(replied_msg.document.file_name)[1] or ".tmp"

            if media_file:
                 status_msg = await update.message.reply_text(f"📤 Preparing {media_type} for upload...")
                 import tempfile
                 
                 try:
                     # Create temp file asynchronously? No, get_file usage needs path or simple download
                     # download_to_drive is awaitable
                     
                     # Create temp file
                     def create_temp():
                         return tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                     
                     tmp = await asyncio.to_thread(create_temp)
                     tmp_path = tmp.name
                     tmp.close()

                     await media_file.download_to_drive(tmp_path)
                     
                     await status_msg.edit_text("📤 Uploading to Catbox.moe...")
                     url = await asyncio.to_thread(self.upload_service.upload_to_catbox, tmp_path)
                     
                     if url:
                         await status_msg.edit_text(f"✅ Upload complete:\n{url}", disable_web_page_preview=True)
                     else:
                         await status_msg.edit_text("❌ Error uploading to Catbox.")
                         
                     # Clean up
                     await asyncio.to_thread(lambda: os.unlink(tmp_path) if os.path.exists(tmp_path) else None)
                     return True
                     
                 except Exception as e:
                     logger.error(f"Error handling reply upload: {e}")
                     await status_msg.edit_text(f"❌ Error: {str(e)}")
                     return True # Processed, even if error
        return False

    async def _handle_media_intent(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, chat_id: int) -> tuple[bool, str | None]:
        """
        Handle media intents (Twitter/YouTube).
        Returns (processed: bool, transcription_text: str | None)
        """
        media_action = self.media_service.identify_action(user_text)
        if not media_action:
             return False, None
             
        platform, action_type, url = media_action
        status_msg = await context.bot.send_message(chat_id, f"🎬 Processing {platform}...")
        
        try:
            if platform == 'twitter':
                await status_msg.edit_text("📤 Downloading Twitter media...")
                media_path, media_type = await self.media_service.process_twitter(url)
                await status_msg.edit_text("📤 Uploading...")
                
                with open(media_path, 'rb') as f:
                    if media_type == 'photo':
                        await context.bot.send_photo(chat_id, photo=f)
                    else:
                        await context.bot.send_video(chat_id, video=f)
                
                await asyncio.to_thread(os.unlink, media_path)
                await status_msg.delete()
                return True, None
                
            elif platform == 'youtube':
                if action_type == 'download_video':
                    await status_msg.edit_text("⬇️ Downloading YouTube video...")
                    video_path = await self.media_service.download_youtube(url)
                    await status_msg.edit_text("📤 Uploading...")
                    
                    with open(video_path, 'rb') as f:
                        await context.bot.send_video(chat_id, video=f)
                        
                    await asyncio.to_thread(os.unlink, video_path)
                    await status_msg.delete()
                    return True, None
                    
                elif action_type == 'transcribe':
                    await status_msg.edit_text("🎙️ Analyzing video for transcription...")
                    transcription, video_title = await self.media_service.transcribe_youtube(url)
                    
                    await status_msg.edit_text(f"✅ Transcription of '_{video_title}_' complete. Analyzing...")
                    
                    new_text = (
                        f"Analyze this YouTube transcription of '{video_title}':\n\n"
                        f"\"\"\"\n{transcription}\n\"\"\"\n\n"
                        f"Provide a detailed summary."
                    )
                    # We return this text so the main processor can feed it to LLM
                    # We should probably delete status msg or let it be reused?
                    # The main processor creates a new "RAG..." message usually.
                    # Let's delete this status msg to avoid clutter or return it?
                    await status_msg.delete()
                    return True, new_text

        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
            return True, None # Error handled
            
        return False, None

    async def _post_process_llm_response(
        self, 
        full_response: str, 
        chat_id: int, 
        context: ContextTypes.DEFAULT_TYPE, 
        placeholder_msg, 
        original_user_text: str,
        message_history: List[Dict]
    ) -> str:
        """
        Handle post-processing of LLM response (Math, Search).
        Returns the (possibly updated) full response.
        """
        
        # 1. Math Command
        if self.command_patterns['matematicas'].search(full_response):
            await placeholder_msg.edit_text("🧮 Solving math...")
            
            if is_feature_enabled("MATH_SOLVER"):
                math_model = get_config("MATH_MODEL")
            else:
                math_model = get_config("MODEL")
                
            logger.info(f"Math command detected, querying {math_model}")
            
            # Prepare messages without RAG system prompt
            math_messages = [msg for msg in message_history if msg.get("role") != "system"]
            if math_messages and math_messages[-1].get("role") == "user":
                 math_messages[-1] = {"role": "user", "content": original_user_text}
            else:
                 math_messages.append({"role": "user", "content": original_user_text})
            
            await self.ollama_client.load_model(math_model)
            
            math_response = await stream_to_telegram(
                self.ollama_client.stream_chat(math_model, math_messages),
                placeholder_msg
            )
            
            if math_model != get_config("MODEL"):
                await self.ollama_client.unload_model(math_model)
                
            return math_response
            
        # 2. Search Command
        search_match = self.command_patterns['search'].search(full_response)
        if search_match:
            search_query = search_match.group(1).strip()
            await placeholder_msg.edit_text(f"🔍 Searching & scraping: {search_query}...")
            
            search_results = await WebSearch.search_with_scrape(search_query)
            
            # Add intermediate exchange to history
            await self.chat_manager.append_message(chat_id, {"role": "assistant", "content": full_response})
            await self.chat_manager.append_message(chat_id, {
                "role": "user",
                "content": f"[Search results for '{search_query}']:\n{search_results}"
            })
            
            # Re-query LLM with search results
            history = await self.chat_manager.get_history(chat_id)
            model = get_config("MODEL")
            context_limit = get_config("CONTEXT_LIMIT", 30000)
            
            await self.ollama_client.load_model(model)
            
            final_response = await stream_to_telegram(
                self.ollama_client.stream_chat(model, prune_history(history, context_limit)),
                placeholder_msg
            )
                
            return final_response
            
        return full_response
