import sys
import os
import requests

# Add src to path to import UploadService
sys.path.append(os.path.join(os.getcwd(), 'src'))
# Also need to make sure we can import from src root
sys.path.append(os.getcwd())

from src.services.upload_service import UploadService

def create_dummy_video(filename="test_video.mp4"):
    # Create a small dummy file, just random bytes, but with mp4 extension
    with open(filename, "wb") as f:
        f.write(os.urandom(1024)) # 1KB dummy file
    return filename

def test_catbox_upload():
    print("Initializing UploadService...")
    uploader = UploadService()
    filename = create_dummy_video()
    
    try:
        print(f"Attempting to upload {filename}...")
        url = uploader.upload_to_catbox(filename)
        
        if url:
            print(f"Success! URL: {url}")
            # Optional: check if URL is reachable
            resp = requests.head(url)
            print(f"URL availability check: {resp.status_code}")
        else:
            print("Upload failed: No URL returned")
            
    except Exception as e:
        print(f"Exception during upload: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_catbox_upload()
