"""YouTube audio download utilities using yt-dlp."""
import tempfile
import os
import re

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

async def download_youtube_audio(url: str) -> str:
    """
    Downloads audio from a YouTube video.
    Returns the path to the downloaded audio file.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp no instalado. Ejecuta: pip install yt-dlp")
    
    # Create temp file for audio
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "audio.mp3")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
        'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
        'quiet': False, # Changed to see errors in logs
        'no_warnings': False,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # 'cookiesfrombrowser': ('chrome',), # Optional: enable if user has cookies
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find the downloaded file
    for f in os.listdir(temp_dir):
        if f.endswith('.mp3'):
            return os.path.join(temp_dir, f)
    
    raise RuntimeError("No se pudo descargar el audio")

def get_video_title(url: str) -> str:
    """Gets the video title without downloading."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Video')
    except:
        return "Video"

async def download_youtube_video(url: str) -> str:
    """
    Downloads video from YouTube.
    Returns the path to the downloaded mp4 file.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp no instalado.")
        
    temp_dir = tempfile.mkdtemp()
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Try to get mp4 directly
        'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: _download_video_sync(url, ydl_opts))
    
    # Find file
    for f in os.listdir(temp_dir):
        if f.endswith('.mp4') or f.endswith('.mkv') or f.endswith('.webm'):
            return os.path.join(temp_dir, f)
            
    raise RuntimeError("No se pudo descargar el video")

def _download_video_sync(url, opts):
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
