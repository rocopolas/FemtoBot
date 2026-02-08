import re
from typing import Optional


def format_bot_response(
    response: str,
    include_thinking: bool = True,
    remove_commands: bool = True,
    escape_ansi: bool = True
) -> str:
    """
    Formatea la respuesta del bot eliminando comandos internos y procesando tags.
    
    Args:
        response: Respuesta cruda del LLM
        include_thinking: Si True, convierte <think> en formato markdown
        remove_commands: Si True, elimina comandos :::xxx:::
        escape_ansi: Si True, elimina códigos de color ANSI
    
    Returns:
        Texto formateado listo para enviar al usuario
    """
    formatted = response
    
    # Procesar tags de pensamiento
    if include_thinking:
        formatted = formatted.replace("<think>", "> 🧠 **Pensando:**\n> ")
        formatted = formatted.replace("</think>", "\n\n")
    else:
        # Eliminar completamente los bloques de pensamiento
        formatted = re.sub(r'<think>.*?</think>', '', formatted, flags=re.DOTALL)
    
    # Eliminar códigos ANSI
    if escape_ansi:
        formatted = re.sub(r'\x1b\[[0-9;]*m', '', formatted)
    
    # Eliminar comandos internos
    if remove_commands:
        # Comandos de memoria - Allow :::memory::: or :::memory space
        formatted = re.sub(r':::memory(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
        formatted = re.sub(r':::memory_delete(?::)?\s*.+?:::', '', formatted, flags=re.DOTALL)
        
        # Comandos de cron
        formatted = re.sub(r':::cron(?::)?\s*.+?:::', '', formatted)
        formatted = re.sub(r':::cron_delete(?::)?\s*.+?:::', '', formatted)
        
        # Comandos de búsqueda
        formatted = re.sub(r':::search(?::)?\s*.+?:::', '', formatted)
        formatted = re.sub(r':::foto(?::)?\s*.+?:::', '', formatted, flags=re.IGNORECASE)
        
    # Comandos de dispositivos
        formatted = re.sub(r':::luz(?::)?\s*.+?:::', '', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r':::camara(?::)?(?:\s+\S+)?:::', '', formatted)
    
    # Formatear matemáticas (LaTeX -> Unicode/Markdown)
    # Esto maneja tanto bloques $$...$$ como inline $...$ de forma segura
    formatted = format_math_for_telegram(formatted)
    
    return formatted.strip()


async def telegramify_content(text: str, max_length: int = 4090):
    """
    Usa telegramify-markdown para convertir y dividir el mensaje.
    Retorna objetos de telegramify con diferentes tipos de contenido (TEXT, PHOTO, FILE).
    """
    try:
        from telegramify_markdown import telegramify, ContentTypes
        
        results = await telegramify(text, max_line_length=max_length)
        return results
        
    except ImportError:
        print("Módulo telegramify_markdown no instalado. Usando fallback.")
        # Devolver lista de strings como fallback
        return split_message(text)
    except Exception as e:
        # Fallback a split simple si falla
        print(f"Error en telegramify: {e}")
        return split_message(text)


def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales de Markdown para Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def escape_code(text: str) -> str:
    """Escapa solo backticks y backslashes para bloques de código."""
    return re.sub(r'([`\\])', r'\\\1', text)


async def send_telegramify_results(context, chat_id, results, placeholder_msg=None):
    """
    Envía resultados de telegramify_markdown manejando diferentes tipos de contenido.
    
    Args:
        context: Contexto del bot de Telegram
        chat_id: ID del chat
        results: Lista de objetos de telegramify
        placeholder_msg: Mensaje placeholder opcional para editar (solo para el primer mensaje de texto)
    
    Returns:
        Lista de mensajes enviados
    """
    from telegramify_markdown import ContentTypes
    from telegram import InputMediaPhoto, InputFile
    import io
    
    sent_messages = []
    first_text_sent = False
    
    for item in results:
        try:
            # Verificar si es string (fallback de split_message)
            if isinstance(item, str):
                if not first_text_sent and placeholder_msg:
                    await placeholder_msg.edit_text(item)
                    sent_messages.append(placeholder_msg)
                    first_text_sent = True
                else:
                    msg = await context.bot.send_message(chat_id, item)
                    sent_messages.append(msg)
                continue
            
            # Manejar objetos de telegramify
            # El contenido ya viene formateado para MarkdownV2
            if item.content_type == ContentTypes.TEXT:
                if not first_text_sent and placeholder_msg:
                    await placeholder_msg.edit_text(item.content, parse_mode="MarkdownV2")
                    sent_messages.append(placeholder_msg)
                    first_text_sent = True
                else:
                    msg = await context.bot.send_message(
                        chat_id, 
                        item.content,
                        parse_mode="MarkdownV2"
                    )
                    sent_messages.append(msg)
                    
            elif item.content_type == ContentType.PHOTO:
                photo_file = io.BytesIO(item.file_data)
                photo_file.name = item.file_name
                
                # La caption ya viene formateada para MarkdownV2 si existe
                caption = item.caption if hasattr(item, 'caption') else None
                
                if not first_text_sent and placeholder_msg:
                    # No podemos editar un mensaje de texto a foto, borrar y enviar nuevo
                    await placeholder_msg.delete()
                    msg = await context.bot.send_photo(
                        chat_id,
                        photo=photo_file,
                        caption=caption,
                        parse_mode="MarkdownV2" if caption else None
                    )
                    sent_messages.append(msg)
                    first_text_sent = True
                else:
                    msg = await context.bot.send_photo(
                        chat_id,
                        photo=photo_file,
                        caption=caption,
                        parse_mode="MarkdownV2" if caption else None
                    )
                    sent_messages.append(msg)
                    
            elif item.content_type == ContentTypes.FILE:
                doc_file = io.BytesIO(item.file_data)
                doc_file.name = item.file_name
                
                # La caption ya viene formateada para MarkdownV2 si existe
                caption = item.caption if hasattr(item, 'caption') else None
                
                if not first_text_sent and placeholder_msg:
                    await placeholder_msg.delete()
                    msg = await context.bot.send_document(
                        chat_id,
                        document=doc_file,
                        caption=caption,
                        parse_mode="MarkdownV2" if caption else None
                    )
                    sent_messages.append(msg)
                    first_text_sent = True
                else:
                    msg = await context.bot.send_document(
                        chat_id,
                        document=doc_file,
                        caption=caption,
                        parse_mode="MarkdownV2" if caption else None
                    )
                    sent_messages.append(msg)
                    
        except Exception as e:
            print(f"Error enviando item de telegramify: {e}")
            # Fallback: intentar enviar como texto simple
            if hasattr(item, 'content'):
                msg = await context.bot.send_message(chat_id, item.content)
                sent_messages.append(msg)
    
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
        # Find a suitable split point
        split_index = -1
        
        # Try to split at the last newline before the limit
        last_newline = text.rfind('\n', 0, limit)
        if last_newline != -1:
            split_index = last_newline
        else:
            # If no newline, force split at limit
            split_index = limit

        # Candidate chunk and remaining
        if split_index == last_newline:
             candidate_chunk = text[:last_newline+1]
             candidate_remaining = text[last_newline+1:]  
        else:
             candidate_chunk = text[:limit]
             candidate_remaining = text[limit:]

        # --- Code Block Logic (Preview) ---
        # We need to calculate the actual impact on length to ensure progress
        code_block_markers = candidate_chunk.count("```")
        overhead_added = 0
        
        if code_block_markers % 2 != 0:
            # We would add "\n```" to chunk (4 chars)
            # And "```\n" to remaining (4 chars)
            # But the loop condition depends on len(remaining_with_modification)
            overhead_remaining = 4 # len("```\n")
        else:
            overhead_remaining = 0
            
        # Check if we are making progress
        # Current length: len(text)
        # New length will be: len(candidate_remaining) + overhead_remaining
        if len(candidate_remaining) + overhead_remaining >= len(text):
            # We are not shrinking the text fast enough (or at all).
            # Force split at limit
            split_index = limit
            candidate_chunk = text[:limit]
            candidate_remaining = text[limit:]
            
            # Re-eval overhead for limit split
            if candidate_chunk.count("```") % 2 != 0:
                 overhead_remaining = 4
            else:
                 overhead_remaining = 0
            
            # If still stuck, we must break the loop to avoid hanging
            if len(candidate_remaining) + overhead_remaining >= len(text):
                 # Emergency break: just take the chunk as is, or ignore code block safety?
                 # If we ignore code block safety we break formatting, but avoid loop.
                 # Let's just output `candidate_chunk` without modification and remaining without modification?
                 # No, better to accept slightly larger chunk?
                 # Let's break, append remaining text as one last chunk (violating limit) to handle edge case
                 parts.append(text)
                 text = ""
                 break

        # Apply logic
        chunk = candidate_chunk
        remaining = candidate_remaining
        
        if chunk.count("```") % 2 != 0:
            chunk += "\n```"
            remaining = "```\n" + remaining

        parts.append(chunk)
        text = remaining

    if text:
        parts.append(text)

    return parts


def prune_history(history: list, max_tokens: int = 30000) -> list:
    """
    Prunes chat history to keep estimated token usage below limit.
    Preserves system prompt and prioritizes recent messages.
    
    Args:
        history: List of message dictionaries
        max_tokens: Maximum tokens allowed
        
    Returns:
        Pruned history list
    """
    # Estimate 1 token ~= 4 chars (rough fast check)
    current_chars = sum(len(m.get('content', '')) for m in history)
    limit_chars = max_tokens * 4
    
    if current_chars <= limit_chars:
        return history
    
    # Split system and others
    system_msgs = [msg for msg in history if msg.get('role') == 'system']
    other_msgs = [msg for msg in history if msg.get('role') != 'system']
    
    # Calculate system usage
    system_chars = sum(len(m.get('content', '')) for m in system_msgs)
    budget = limit_chars - system_chars
    
    if budget <= 0:
        return system_msgs  # Should not happen unless system prompt is huge
    
    kept_msgs = []
    current_usage = 0
    
    # Take from end (most recent first)
    for msg in reversed(other_msgs):
        msg_len = len(msg.get('content', ''))
        if current_usage + msg_len > budget:
            break
        kept_msgs.append(msg)
        current_usage += msg_len
    
    return system_msgs + list(reversed(kept_msgs))


def format_math_for_telegram(text: str) -> str:
    """Format math response for Telegram Markdown compatibility."""
    import re
    
    # Remove LaTeX delimiters \( \) and replace with backticks
    text = re.sub(r'\\\((.*?)\\\)', r'`\1`', text)
    
    # Remove LaTeX delimiters \[ \] and format as code block
    text = re.sub(r'\\\[(.*?)\\\]', r'```\n\1\n```', text, flags=re.DOTALL)
    
    # Handle standard LaTeX delimiters $...$ and $$...$$
    # Block math $$...$$
    text = re.sub(r'\$\$(.*?)\$\$', r'```\n\1\n```', text, flags=re.DOTALL)
    
    # Inline math $...$
    # Regex: Match $...$ but avoid simple currency like $100 or $ 100
    # Logic: Lookahead ensures content doesn't start with (optional space + digit)
    # This allows $ p(x) $ but blocks $ 100
    text = re.sub(r'(?<!\$)\$(?!\$)(?!\s*\d)(.*?)(?<!\$)\$(?!\$)', r'`\1`', text)
    
    # Remove \boxed{} and format as bold
    text = re.sub(r'\\boxed\{(.*?)\}', r'*\1*', text)
    
    # Convert common LaTeX commands to readable format
    replacements = {
        r'\\cdot': '·',
        r'\\times': '×',
        r'\\div': '÷',
        r'\\pm': '±',
        r'\\mp': '∓',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\neq': '≠',
        r'\\approx': '≈',
        r'\\equiv': '≡',
        r'\\infty': '∞',
        r'\\sum': 'Σ',
        r'\\prod': 'Π',
        r'\\int': '∫',
        r'\\sqrt': '√',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\epsilon': 'ε',
        r'\\theta': 'θ',
        r'\\lambda': 'λ',
        r'\\mu': 'μ',
        r'\\pi': 'π',
        r'\\sigma': 'σ',
        r'\\phi': 'φ',
        r'\\omega': 'ω',
        r'\\rightarrow': '→',
        r'\\leftarrow': '←',
        r'\\Rightarrow': '⇒',
        r'\\Leftarrow': '⇐',
        # Complex replacements
        r'\\frac\{([^}]+)\}\{([^}]+)\}': r'(\1)/(\2)',
        r'\\text\{([^}]+)\}': r'\1',
        r'\^\{([^}]+)\}': r'^\1',
        r'_\{([^}]+)\}': r'_\1',
        # Clean specific artifacts
        r'\\left': '',
        r'\\right': '',
        r'\\quad': ' ',
        r'\\ ': ' ',
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    # Clean up any remaining LaTeX backslashes before special chars
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)
    
    
    # Ensure numbered lists use proper format
    text = re.sub(r'^(\d+)\.\s+', r'\1\. ', text, flags=re.MULTILINE)
    
    return text.strip()
