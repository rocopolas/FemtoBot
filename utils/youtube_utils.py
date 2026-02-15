"""YouTube audio download utilities using yt-dlp."""
import tempfile
import os
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

def is_youtube_url(text: str) -> str | None:
    """Check if text contains a YouTube URL. Returns the URL if found, None otherwise."""
    patterns = [
        r'(https?://(www\.)?youtube\.com/watch\?v=[\w-]+)',
        r'(https?://youtu\.be/[\w-]+)',
        r'(https?://(www\.)?youtube\.com/shorts/[\w-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def _download_audio_sync(url: str, temp_dir: str) -> str:
    """Synchronous audio download function."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp no instalado. Ejecuta: pip install yt-dlp")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
        'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
        'quiet': True, 
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find the downloaded file
    for f in os.listdir(temp_dir):
        if f.endswith('.mp3'):
            return os.path.join(temp_dir, f)
            
    raise RuntimeError("No se pudo descargar el audio")

async def download_youtube_audio(url: str) -> str:
    """
    Downloads audio from a YouTube video (Non-blocking).
    Returns the path to the downloaded audio file.
    """
    temp_dir = await asyncio.to_thread(tempfile.mkdtemp)
    try:
        return await asyncio.to_thread(_download_audio_sync, url, temp_dir)
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        # Clean up temp dir if failed
        await asyncio.to_thread(lambda: os.rmdir(temp_dir) if os.path.exists(temp_dir) else None)
        raise e

def _get_title_sync(url: str) -> str:
    """Synchronous title fetch."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Video')
    except Exception as e:
        logger.warning(f"Error getting title: {e}")
        return "Video"

def get_video_title(url: str) -> str:
    """Gets the video title without downloading (Blocking - wrapper kept for compatibility if needed, but better to use async)."""
    # Note: This is still blocking if called directly. 
    # But we usually call this from async context.
    # It's better to make an async version `get_video_title_async` or wrap it.
    # For now, let's just make it call the sync version directly to avoid breaking changes if it's expected to be sync,
    # BUT the plan was to make it non-blocking.
    
    # Actually, the MediaService calls this. Let's check MediaService usage.
    # src/services/media_service.py:74: video_title = get_video_title(url)
    # MediaService calls it synchronously.
    
    # To fix blocking, we should ideally change MediaService to await a new async function,
    # OR we use run_in_executor inside MediaService.
    
    # However, MediaService.transcribe_youtube is async.
    # So we can change get_video_title to be just the sync implementation
    # and change MediaService to use asyncio.to_thread(get_video_title, url).
    
    # OR we change this function to strictly be sync helper and add async wrapper.
    return _get_title_sync(url)

async def get_video_title_async(url: str) -> str:
    """Async wrapper for getting video title."""
    return await asyncio.to_thread(_get_title_sync, url)

def _download_video_sync(url: str, temp_dir: str) -> str:
    """Synchronous video download."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp no instalado.")
        
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Try to get mp4 directly
        'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find file
    for f in os.listdir(temp_dir):
        if f.endswith('.mp4') or f.endswith('.mkv') or f.endswith('.webm'):
            return os.path.join(temp_dir, f)
            
    raise RuntimeError("No se pudo descargar el video")

async def download_youtube_video(url: str) -> str:
    """
    Downloads video from YouTube (Non-blocking).
    Returns the path to the downloaded mp4 file.
    """
    temp_dir = await asyncio.to_thread(tempfile.mkdtemp)
    return await asyncio.to_thread(_download_video_sync, url, temp_dir)
