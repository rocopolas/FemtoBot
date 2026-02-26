"""Search utility using SearXNG (self-hosted meta-search engine)."""
import os
import httpx
import logging
from typing import List, Optional

from utils.config_loader import get_config

logger = logging.getLogger(__name__)

# SearXNG URL from config or env, defaults to localhost:8080
def _get_searxng_url() -> str:
    """Get SearXNG base URL from config."""
    try:
        cfg = get_config("SEARXNG_URL")
        if cfg:
            return cfg.rstrip("/")
    except Exception:
        pass
    return os.getenv("SEARXNG_URL", "http://localhost:8080")

SEARXNG_URL = _get_searxng_url()


class BraveSearch:
    """
    Web search via SearXNG (self-hosted).
    Class name kept as BraveSearch for backward compatibility.
    """
    
    @staticmethod
    async def search(query: str, count: int = 3) -> str:
        """
        Search the web using SearXNG.
        Returns formatted results as a string.
        """
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }
        
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{SEARXNG_URL}/search",
                        params=params,
                        timeout=15.0
                    )
                    
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            import asyncio
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"SearXNG rate limit. Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        return "[Error: Rate limit exceeded]"
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    results = []
                    for i, r in enumerate(data.get("results", [])[:count], 1):
                        title = r.get("title", "No title")
                        description = r.get("content", r.get("description", "No description"))
                        url = r.get("url", "")
                        results.append(f"{i}. **{title}**\n   {description}\n   {url}")
                    
                    if not results:
                        return "[No results found]"
                    
                    return "\n\n".join(results)
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"SearXNG error: {e}")
                return f"[Search error: {e.response.status_code}]"
            except Exception as e:
                logger.error(f"Search error: {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(1)
                    continue
                return f"[Search error: {str(e)}]"
        
        return "[Error: Maximum retries exceeded]"
    
    @staticmethod
    async def _raw_search(query: str, count: int = 3) -> List[dict]:
        """
        Raw search returning structured results.
        Returns list of dicts with title, description, url.
        """
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SEARXNG_URL}/search",
                    params=params,
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for r in data.get("results", [])[:count]:
                    results.append({
                        "title": r.get("title", ""),
                        "description": r.get("content", r.get("description", "")),
                        "url": r.get("url", "")
                    })
                return results
        except Exception as e:
            logger.error(f"Raw search error: {e}")
            return []

    @staticmethod
    async def search_with_scrape(query: str, count: int = 3) -> str:
        """
        Search the web and scrape the top results for full content.
        Returns formatted results with full page text for richer LLM context.
        """
        raw_results = await BraveSearch._raw_search(query, count)
        if not raw_results:
            return await BraveSearch.search(query, count)
        
        try:
            from utils.web_fetcher import WebFetcher
            fetcher = WebFetcher(max_content_length=4000)
        except ImportError:
            logger.warning("WebFetcher not available, falling back to basic search")
            return await BraveSearch.search(query, count)
        
        import asyncio
        
        formatted = []
        
        async def fetch_one(result: dict) -> str:
            url = result["url"]
            title = result["title"]
            desc = result["description"]
            
            content = await fetcher.fetch_content(url)
            
            if content and len(content.strip()) > 50:
                return (
                    f"**{title}**\n"
                    f"URL: {url}\n"
                    f"Content:\n{content}"
                )
            else:
                return (
                    f"**{title}**\n"
                    f"URL: {url}\n"
                    f"Summary: {desc}"
                )
        
        tasks = [fetch_one(r) for r in raw_results]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results, 1):
            if isinstance(result, str):
                formatted.append(f"{i}. {result}")
            else:
                r = raw_results[i-1]
                formatted.append(f"{i}. **{r['title']}**\n   {r['description']}\n   {r['url']}")
        
        return "\n\n".join(formatted) if formatted else "[No results found]"

    @staticmethod
    async def search_images(query: str, count: int = 5) -> List[str]:
        """
        Search for images using SearXNG.
        Returns a list of image URLs.
        """
        params = {
            "q": query,
            "format": "json",
            "categories": "images",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SEARXNG_URL}/search",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                image_urls = []
                for r in data.get("results", []):
                    img_url = r.get("img_src") or r.get("url", "")
                    if img_url:
                        image_urls.append(img_url)
                
                return image_urls[:count]
                
        except Exception as e:
            logger.error(f"Image search error: {e}")
            return []
