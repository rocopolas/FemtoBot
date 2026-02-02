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
            'preferredquality': '128',
        }],
        'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
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
