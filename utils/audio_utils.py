import os
from pathlib import Path
from utils.config_loader import get_config
import gc

# Lazy load whisper to avoid import errors if not installed
_model = None
_model_large = None

def get_whisper_model():
    """Lazy load faster-whisper model for voice messages."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            model_name = get_config("WHISPER_MODEL_VOICE")
            _model = WhisperModel(model_name, device="cpu", compute_type="int8")
        except ImportError:
            return None
    return _model

def get_whisper_model_large():
    """Lazy load faster-whisper model for external audio."""
    global _model_large
    if _model_large is None:
        try:
            from faster_whisper import WhisperModel
            model_name = get_config("WHISPER_MODEL_EXTERNAL")
            _model_large = WhisperModel(model_name, device="cpu", compute_type="int8")
        except ImportError:
            return None
    return _model_large

def unload_whisper_model():
    """Unload the voice whisper model from memory."""
    global _model
    if _model is not None:
        del _model
        _model = None
        gc.collect()

def unload_whisper_model_large():
    """Unload the large whisper model from memory."""
    global _model_large
    if _model_large is not None:
        del _model_large
        _model_large = None
        gc.collect()

async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes an audio file using faster-whisper.
    Returns the transcription text or an error message.
    Unloads the model after transcription to free RAM.
    """
    model = get_whisper_model()
    
    if model is None:
        return "[Error: faster-whisper no instalado. Ejecuta: pip install faster-whisper]"
    
    try:
        language = get_config("WHISPER_LANGUAGE")
        segments, info = model.transcribe(audio_path, language=language)
        
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        transcription = " ".join(text_parts).strip()
        transcription = " ".join(transcription.split())
        return transcription if transcription else "[Audio sin contenido detectado]"
        
    except Exception as e:
        return f"[Error de transcripción: {str(e)}]"
    finally:
        unload_whisper_model()

async def transcribe_audio_large(audio_path: str) -> str:
    """
    Transcribes an audio file using the larger whisper model.
    For external audio files that need better quality.
    Unloads the model after transcription to free RAM.
    """
    model = get_whisper_model_large()
    
    if model is None:
        return "[Error: faster-whisper no instalado]"
    
    try:
        language = get_config("WHISPER_LANGUAGE")
        segments, info = model.transcribe(audio_path, language=language)
        
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        transcription = " ".join(text_parts).strip()
        transcription = " ".join(transcription.split())
        return transcription if transcription else "[Audio sin contenido detectado]"
        
    except Exception as e:
        return f"[Error de transcripción: {str(e)}]"
    finally:
        unload_whisper_model_large()

def is_whisper_available() -> bool:
    """Check if faster-whisper is available."""
    try:
        from faster_whisper import WhisperModel
        return True
    except ImportError:
        return False

