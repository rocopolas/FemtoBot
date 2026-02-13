"""Async web content fetching utility using trafilatura."""
import logging
import httpx
from typing import Optional
import trafilatura

logger = logging.getLogger(__name__)


class WebFetcher:
    """
    Fetches and extracts main content from web pages.
    Uses trafilatura for intelligent content extraction.
    """
    
    DEFAULT_TIMEOUT = 15.0
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        min_content_length: int = 100,
        max_content_length: int = 50000
    ):
        self.timeout = timeout
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self.headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    
    async def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract main content from a URL.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Extracted main text content or None if failed
        """
        logger.info(f"Fetching content from: {url}")
        
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.warning(f"Non-HTML content type for {url}: {content_type}")
                    return None
                
                html_content = response.text
                
                # Extract main content using trafilatura
                extracted = trafilatura.extract(
                    html_content,
                    url=url,
                    include_comments=False,
                    include_tables=True,
                    include_images=False,
                    include_links=False,
                    favor_precision=True,
                    deduplicate=True,
                    target_language=None  # Auto-detect language
                )
                
                if not extracted:
                    logger.warning(f"Trafilatura extraction returned empty for {url}")
                    return None
                
                extracted = extracted.strip()
                
                if len(extracted) < self.min_content_length:
                    logger.warning(f"Content too short ({len(extracted)} chars) for {url}")
                    return None
                
                # Truncate if too long
                if len(extracted) > self.max_content_length:
                    extracted = extracted[:self.max_content_length] + "\n\n[Content truncated due to length...]"
                    logger.info(f"Content truncated for {url}")
                
                logger.info(f"Successfully extracted {len(extracted)} chars from {url}")
                return extracted
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
