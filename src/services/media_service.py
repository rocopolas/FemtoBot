"""
Media Service for handling Twitter and YouTube downloads.
"""
import os
import logging
from typing import Optional, Tuple, Union

# Import utils
from utils.youtube_utils import is_youtube_url, download_youtube_video, download_youtube_audio, get_video_title
from utils.twitter_utils import is_twitter_url, download_twitter_video
from utils.audio_utils import transcribe_audio

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self):
        pass

    async def process_twitter(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Process Twitter URL if present.
        Returns: (media_path, media_type) or None
        media_type is 'video' or 'photo' (determined by extension)
        """
        url = is_twitter_url(text)
        if not url:
            return None
            
        keywords = ["descarga", "baja", "video", "bajar", "download"]
        if not any(k in text.lower() for k in keywords):
            return None

        try:
            logger.info(f"Processing Twitter URL: {url}")
            media_path = await download_twitter_video(url)
            
            if media_path.endswith(('.jpg', '.png', '.jpeg')):
                return media_path, 'photo'
            else:
                return media_path, 'video'
        except Exception as e:
            logger.error(f"Error processing Twitter URL: {e}")
            raise e

    async def process_youtube(self, text: str) -> Optional[Union[Tuple[str, str], Tuple[str, str, str]]]:
        """
        Process YouTube URL if present.
        Returns: 
            - (video_path, 'video') for video download
            - (transcription_text, 'transcription', video_title) for transcription
            - None if no action needed
        """
        url = is_youtube_url(text)
        if not url:
            return None
            
        keywords = ["descarga", "baja", "video", "bajar", "download"]
        
        # Video Download
        if any(k in text.lower() for k in keywords):
            try:
                logger.info(f"Downloading YouTube video: {url}")
                video_path = await download_youtube_video(url)
                return video_path, 'video'
            except Exception as e:
                logger.error(f"Error downloading YouTube video: {e}")
                raise e
        
        # Transcription (default if not downloading)
        try:
            logger.info(f"Transcribing YouTube video: {url}")
            video_title = get_video_title(url)
            audio_path = await download_youtube_audio(url)
            
            transcription = await transcribe_audio(audio_path)
            
            # Clean up audio file
            if os.path.exists(audio_path):
                os.unlink(audio_path)
                
            return transcription, 'transcription', video_title
        except Exception as e:
            logger.error(f"Error transcribing YouTube video: {e}")
            raise e

    def is_media_url(self, text: str) -> bool:
        return bool(is_twitter_url(text) or is_youtube_url(text))
