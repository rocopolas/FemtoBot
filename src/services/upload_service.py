"""
Upload Service for handling file uploads to external services like Catbox.moe.
"""
import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UploadService:
    CATBOX_API_URL = "https://catbox.moe/user/api.php"

    def __init__(self):
        pass

    def upload_to_catbox(self, file_path: str) -> Optional[str]:
        """
        Uploads a file to Catbox.moe and returns the URL.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        try:
            logger.info(f"Uploading to Catbox: {file_path}")
            
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
                
            with open(file_path, 'rb') as f:
                payload = {
                    'reqtype': 'fileupload'
                }
                # Only add userhash if it's not empty
                # payload['userhash'] = '' 
                
                files = {
                    'fileToUpload': (os.path.basename(file_path), f, mime_type)
                }
                response = requests.post(self.CATBOX_API_URL, data=payload, files=files)
                
            if response.status_code == 200:
                url = response.text.strip()
                if url:
                    logger.info(f"Upload successful: {url}")
                    return url
                else:
                    logger.error(f"Catbox returned 200 but empty body. Response: {response.content}")
                    return None
            else:
                logger.error(f"Catbox upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading to Catbox: {e}")
            return None

    def is_upload_intent(self, text: str) -> bool:
        """Check if text indicates an intent to upload."""
        if not text:
            return False
        
        keywords = ["catbox", "sube", "upload", "link", "url"]
        text_lower = text.lower()
        
        # Relaxed check: just "sube", "upload" or "catbox" is enough
        # The context (caption or reply to media) already implies the object is the file.
        triggers = ["catbox", "sube", "upload", "carga", "link", "url"]
        
        if any(t in text_lower for t in triggers):
            return True
            
        return False
            
        return False
