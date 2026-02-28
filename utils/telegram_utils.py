import re
import time
import logging
from typing import List, AsyncGenerator

logger = logging.getLogger(__name__)

# ── Regex patterns for live preview cleanup ─────────────────────────
_THINK_CLOSED_RE = re.compile(r'<think>.*?</think>', re.DOTALL)
_THINK_OPEN_RE = re.compile(r'<think>.*', re.DOTALL)
_COMMAND_RE = re.compile(r':::\w+(?::)?\s*.*?:::', re.DOTALL)

# Telegram message char limit
_TG_MAX_LEN = 4000


def strip_think_tags(text: str) -> str:
    """Remove all <think>...</think> blocks (closed and unclosed) from text."""
    text = _THINK_CLOSED_RE.sub('', text)
    text = _THINK_OPEN_RE.sub('', text)
    return text


def _clean_preview(text: str) -> str:
    """Strip command tokens for live preview (thinking tags are shown)."""
    text = _COMMAND_RE.sub('', text)
    return text.strip()


async def stream_to_telegram(
    stream: AsyncGenerator[str, None],
    message,
    interval: float = 5.0,
) -> str:
    """
    Consume an LLM streaming generator while updating a Telegram message
    with a live preview every `interval` seconds.

    Args:
        stream: async generator yielding text chunks (from OllamaClient.stream_chat)
        message: Telegram Message object to edit in-place
        interval: seconds between edits (default 1.0)

    Returns:
        The response string with thinking tags stripped
        (safe for command processing).
    """
    full_response = ""
    last_edit = 0.0
    last_preview = ""

    async for chunk in stream:
        full_response += chunk
        now = time.monotonic()

        if now - last_edit >= interval:
            preview = _clean_preview(full_response)
            if preview and preview != last_preview:
                # Truncate for Telegram limit, add cursor
                display = preview[:_TG_MAX_LEN] + " ▌"
                try:
                    await message.edit_text(display)
                except Exception:
                    pass  # Rate limit, same content, or bot shutting down
                last_preview = preview
                last_edit = now

    # Strip thinking tags before returning so commands inside
    # <think> blocks are never processed
    full_response = _THINK_CLOSED_RE.sub('', full_response)
    full_response = _THINK_OPEN_RE.sub('', full_response)

    return full_response


async def telegramify_content(text: str, max_length: int = 4090):
    """
    Uses telegramify-markdown v1.0.0+ to convert and split the message.
    Returns telegramify objects with different content types (TEXT, PHOTO, FILE).
    """
    try:
        from telegramify_markdown import telegramify
        
        results = await telegramify(text, max_message_length=max_length)
        return results
        
    except ImportError:
        logger.warning("telegramify_markdown module not installed. Using fallback.")
        return split_message(text)
    except Exception as e:
        logger.error(f"Error en telegramify: {e}", exc_info=True)
        return split_message(text)


def escape_markdown(text: str) -> str:
    """Escapes Markdown special characters for Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', lambda m: '\\' + m.group(1), text)


def escape_code(text: str) -> str:
    """Escapes only backticks and backslashes for code blocks."""
    return re.sub(r'([`\\])', lambda m: '\\' + m.group(1), text)


async def send_telegramify_results(context, chat_id, results, placeholder_msg=None, reply_to_message_id=None):
    """
    Sends telegramify_markdown v1.0.0+ results handling different content types.
    Uses entities instead of parse_mode.
    
    Args:
        context: Telegram bot context
        chat_id: Chat ID
        results: List of telegramify objects (Text, File, Photo)
        placeholder_msg: Optional placeholder message to edit
        reply_to_message_id: Optional message ID to reply to (if sending new messages)
    
    Returns:
        List of sent messages
    """
    from telegramify_markdown import ContentType
    import io
    
    sent_messages = []
    first_item_sent = False
    
    for item in results:
        try:
            # Check if it's a string (split_message fallback)
            if isinstance(item, str):
                if not first_item_sent and placeholder_msg:
                    await placeholder_msg.edit_text(item)
                    sent_messages.append(placeholder_msg)
                    first_item_sent = True
                else:
                    msg = await context.bot.send_message(chat_id, item, reply_to_message_id=reply_to_message_id)
                    sent_messages.append(msg)
                continue
            
            # Handle telegramify v1.0.0+ objects
            if item.content_type == ContentType.TEXT:
                # Convert entities to dictionaries
                entities = [e.to_dict() for e in item.entities] if item.entities else None
                
                if not first_item_sent and placeholder_msg:
                    await placeholder_msg.edit_text(item.text, entities=entities)
                    sent_messages.append(placeholder_msg)
                    first_item_sent = True
                else:
                    msg = await context.bot.send_message(
                        chat_id, 
                        item.text,
                        entities=entities,
                        reply_to_message_id=reply_to_message_id
                    )
                    sent_messages.append(msg)
                    
            elif item.content_type == ContentType.PHOTO:
                photo_file = io.BytesIO(item.file_data)
                photo_file.name = item.file_name
                
                # Convert caption entities if they exist
                caption_entities = None
                if hasattr(item, 'caption_entities') and item.caption_entities:
                    caption_entities = [e.to_dict() for e in item.caption_entities]
                
                caption = item.caption_text if hasattr(item, 'caption_text') else None
                
                if not first_item_sent and placeholder_msg:
                    await placeholder_msg.delete()
                    msg = await context.bot.send_photo(
                        chat_id,
                        photo=photo_file,
                        caption=caption,
                        caption_entities=caption_entities,
                        reply_to_message_id=reply_to_message_id
                    )
                    sent_messages.append(msg)
                    first_item_sent = True
                else:
                    msg = await context.bot.send_photo(
                        chat_id,
                        photo=photo_file,
                        caption=caption,
                        caption_entities=caption_entities,
                        reply_to_message_id=reply_to_message_id
                    )
                    sent_messages.append(msg)
                    
            elif item.content_type == ContentType.FILE:
                file_content = item.file_data
                
                # Check if file is small enough to send as text (e.g. < 2KB)
                # and if it looks like a text file (based on extension or content)
                is_small = len(file_content) < 2000
                
                if is_small:
                    try:
                        # Try to decode as text
                        text_content = file_content.decode('utf-8')
                        # Wrap in code block
                        formatted_text = f"```\n{text_content}\n```"
                        
                        caption = getattr(item, 'caption_text', None)
                        if caption:
                            formatted_text = f"{caption}\n{formatted_text}"
                            
                        if not first_item_sent and placeholder_msg:
                            await placeholder_msg.edit_text(formatted_text, parse_mode="Markdown")
                            sent_messages.append(placeholder_msg)
                            first_item_sent = True
                        else:
                            msg = await context.bot.send_message(
                                chat_id,
                                formatted_text,
                                parse_mode="Markdown",
                                reply_to_message_id=reply_to_message_id
                            )
                            sent_messages.append(msg)
                        continue # Skip sending as file
                    except UnicodeDecodeError:
                        # Not a text file, proceed to send as document
                        pass

                doc_file = io.BytesIO(item.file_data)
                doc_file.name = item.file_name
                
                # Convert caption entities if they exist
                caption_entities = None
                if hasattr(item, 'caption_entities') and item.caption_entities:
                    caption_entities = [e.to_dict() for e in item.caption_entities]
                
                caption = item.caption_text if hasattr(item, 'caption_text') else None
                
                if not first_item_sent and placeholder_msg:
                    await placeholder_msg.delete()
                    msg = await context.bot.send_document(
                        chat_id,
                        document=doc_file,
                        caption=caption,
                        caption_entities=caption_entities,
                        reply_to_message_id=reply_to_message_id
                    )
                    sent_messages.append(msg)
                    first_item_sent = True
                else:
                    msg = await context.bot.send_document(
                        chat_id,
                        document=doc_file,
                        caption=caption,
                        caption_entities=caption_entities,
                        reply_to_message_id=reply_to_message_id
                    )
                    sent_messages.append(msg)
                    
        except Exception as e:
            logger.error(f"Error sending telegramify item: {e}", exc_info=True)
            # Fallback: try to send as plain text
            if hasattr(item, 'text'):
                msg = await context.bot.send_message(chat_id, item.text, reply_to_message_id=reply_to_message_id)
                sent_messages.append(msg)
            elif hasattr(item, 'content'):
                msg = await context.bot.send_message(chat_id, item.content, reply_to_message_id=reply_to_message_id)
                sent_messages.append(msg)
            elif hasattr(item, 'file_data'):
                try:
                    text_fallback = item.file_data.decode('utf-8', errors='replace')
                    caption = getattr(item, 'caption_text', '')
                    if caption:
                        text_fallback = f"{caption}\n\n{text_fallback}"
                    for chunk in split_message(text_fallback):
                        msg = await context.bot.send_message(chat_id, chunk, reply_to_message_id=reply_to_message_id)
                        sent_messages.append(msg)
                except Exception:
                    pass
    
    return sent_messages


def split_message(text, limit=4096):
    """
    Splits a message into chunks that fit within the Telegram character limit.
    Tries to split at newlines to preserve readability.
    Handles code blocks to ensure they are closed in one chunk and reopened in the next.
    """
    if len(text) <= limit:
        return [text]

    parts = []
    while len(text) > limit:
        split_index = -1
        
        last_newline = text.rfind('\n', 0, limit)
        if last_newline != -1:
            split_index = last_newline
        else:
            split_index = limit

        chunk = text[:split_index]
        
        # Handle code blocks
        code_starts = chunk.count('```') % 2
        if code_starts:
            last_code = chunk.rfind('```')
            # If we found a code block start and it's not at the very beginning (or if it is but we can't skip it)
            if last_code != -1 and last_code > 0:
                chunk = chunk[:last_code]
                text = text[last_code:]
            else:
                # If last_code == 0, it means the entire chunk is inside a code block (or starts with one)
                # We can't backtrack, so we must close the block and reopen in next chunk
                # Reduce chunk size to make room for closing ```
                if len(chunk) > limit - 4:
                    chunk = chunk[:limit - 4]
                    # Also update text to consume only what we took
                    text = text[len(chunk):]
                else:
                    text = text[len(chunk):]
                
                chunk += "\n```"
                text = "```\n" + text
        else:
            text = text[split_index:]
            if text.startswith('\n'):
                text = text[1:]

        parts.append(chunk)

    if text:
        parts.append(text)

    return parts


def format_bot_response(response: str) -> str:
    """Format bot response for Telegram, handling various Markdown elements."""
    if not response:
        return ""
    
    formatted = response
    
    # Strip thinking tags completely (e.g. Qwen3 <think>...</think>)
    formatted = re.sub(r'<think>.*?</think>', '', formatted, flags=re.DOTALL)
    # Handle unclosed <think> tag (model still thinking at end of response)
    formatted = re.sub(r'<think>.*', '', formatted, flags=re.DOTALL)
    
    # Remove ANSI color codes
    formatted = re.sub(r'\x1b\[[0-9;]*m', '', formatted)
    
    # Handle memory commands - remove them from visible output
    formatted = re.sub(r':::memory(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    formatted = re.sub(r':::memory_delete(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    
    # Handle cron commands
    formatted = re.sub(r':::cron(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    formatted = re.sub(r':::cron_delete(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    
    # Handle search commands
    formatted = re.sub(r':::search(?::)?\s*.+?:::', '', formatted)
    formatted = re.sub(r':::foto(?::)?\s*.+?:::', '', formatted, flags=re.IGNORECASE)
    
    # Handle light/camera commands
    formatted = re.sub(r':::luz(?::)?\s*.+?:::', '', formatted, flags=re.IGNORECASE)
    formatted = re.sub(r':::camara(?::)?(?:\s+\S+)?:::', '', formatted)
    
    # Handle terminal commands
    formatted = re.sub(r':::terminal(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    
    # Handle matematicas commands (when disabled, shouldn't show)
    formatted = re.sub(r':::matematicas(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
    
    # LaTeX math is now handled automatically by telegramify-markdown
    
    # Strip wrapping quotes the LLM sometimes adds
    formatted = formatted.strip()
    if len(formatted) >= 2 and formatted.startswith('"') and formatted.endswith('"'):
        formatted = formatted[1:-1].strip()
    
    return formatted


def prune_history(history: list, limit: int = 30000) -> list:
    """Prune chat history to fit within token limit while keeping system prompt."""
    if not history:
        return []
    
    # Always keep system prompt (first message if it's system)
    if history and history[0].get("role") == "system":
        system_msg = history[0]
        messages = history[1:]
    else:
        system_msg = None
        messages = history
    
    # Calculate total length
    total_length = sum(len(str(msg.get("content", ""))) for msg in history)
    
    # If under limit, return all
    if total_length <= limit:
        return history
    
    # Remove oldest messages until under limit
    while len(messages) > 1 and total_length > limit:
        removed = messages.pop(0)
        total_length -= len(str(removed.get("content", "")))
    
    # Reconstruct history
    result = []
    if system_msg:
        result.append(system_msg)
    result.extend(messages)
    
    return result
