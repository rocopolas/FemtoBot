import os
import httpx
from dotenv import load_dotenv

load_dotenv()
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

class BraveSearch:
    """Utility class for Brave Search API."""
    
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"
    
    @staticmethod
    async def search(query: str, count: int = 3) -> str:
        """
        Searches the web using Brave Search API.
        Returns formatted results as a string.
        """
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not BRAVE_API_KEY:
            return "[Error: BRAVE_API_KEY not configured in .env]"
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        
        params = {
            "q": query,
            "count": count
        }
        
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        BraveSearch.BASE_URL,
                        headers=headers,
                        params=params,
                        timeout=10.0
                    )
                    
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limit hit (429). Retrying in {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            return "[Error: Rate limit exceeded (429)]"
                            
                    response.raise_for_status()
                    data = response.json()
                    
                    # Format results
                    results = []
                    web_results = data.get("web", {}).get("results", [])
                    
                    for i, result in enumerate(web_results[:count], 1):
                        title = result.get("title", "No title")
                        description = result.get("description", "No description")
                        url = result.get("url", "")
                        results.append(f"{i}. **{title}**\n   {description}\n   {url}")
                    
                    if not results:
                        return "[No results found]"
                    
                    return "\n\n".join(results)
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Search API error: {e}")
                return f"[Search error: {e.response.status_code}]"
            except Exception as e:
                logger.error(f"Unexpected search error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return f"[Search error: {str(e)}]"
        
        return "[Error: Maximum retries exceeded]"
    
    @staticmethod
    async def _raw_search(query: str, count: int = 3) -> list[dict]:
        """
        Raw search returning structured results.
        Returns list of dicts with title, description, url.
        """
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not BRAVE_API_KEY:
            return []
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {"q": query, "count": count}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    BraveSearch.BASE_URL,
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for r in data.get("web", {}).get("results", [])[:count]:
                    results.append({
                        "title": r.get("title", ""),
                        "description": r.get("description", ""),
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
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        raw_results = await BraveSearch._raw_search(query, count)
        if not raw_results:
            return await BraveSearch.search(query, count)
        
        try:
            from utils.web_fetcher import WebFetcher
            fetcher = WebFetcher(timeout=10.0, max_content_length=4000)
        except ImportError:
            logger.warning("WebFetcher not available, falling back to basic search")
            return await BraveSearch.search(query, count)
        
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
                # Exception fallback
                r = raw_results[i-1]
                formatted.append(f"{i}. **{r['title']}**\n   {r['description']}\n   {r['url']}")
        
        return "\n\n".join(formatted) if formatted else "[No results found]"

    @staticmethod
    async def search_images(query: str, count: int = 5) -> list[str]:
        """
        Searches for images using Brave Search API.
        Returns a list of image URLs.
        """
        if not BRAVE_API_KEY:
            return []
        
        url = "https://api.search.brave.com/res/v1/images/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {"q": query, "count": count}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                image_urls = []
                for result in results:
                    # 'properties' -> 'url' is the image source
                    img_url = result.get("properties", {}).get("url")
                    if img_url:
                        image_urls.append(img_url)
                        
                return image_urls[:count]
                
        except Exception as e:
            print(f"[Brave Images] Error: {e}")
            return []
