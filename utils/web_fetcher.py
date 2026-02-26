"""Async web content fetching utility using Crawl4AI."""
import re
import logging
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

logger = logging.getLogger(__name__)


class WebFetcher:
    """
    Fetches and extracts main content from web pages.
    Uses Crawl4AI for intelligent content extraction as clean Markdown.
    """
    
    def __init__(
        self,
        min_content_length: int = 100,
        max_content_length: int = 15000
    ):
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self._browser_config = BrowserConfig(
            headless=True,
            verbose=False,
        )
    
    async def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract main content from a URL as clean Markdown.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Extracted content as clean Markdown, or None if failed
        """
        logger.info(f"Fetching content from: {url}")
        
        try:
            run_config = CrawlerRunConfig(
                page_timeout=30000,
                wait_until="domcontentloaded",
            )
            
            async with AsyncWebCrawler(config=self._browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if not result.success:
                    logger.warning(f"Crawl4AI failed for {url}: {result.error_message}")
                    return None
                
                # Prefer fit_markdown (main content) over full markdown
                content = ""
                if hasattr(result, 'markdown_v2') and result.markdown_v2:
                    content = result.markdown_v2.fit_markdown or result.markdown_v2.raw_markdown or ""
                if not content:
                    content = getattr(result, 'fit_markdown', '') or result.markdown or ""
                
                content = content.strip()
                
                if not content:
                    logger.warning(f"Crawl4AI returned empty content for {url}")
                    return None
                
                # Clean up the markdown
                content = self._clean_markdown(content)
                
                if len(content) < self.min_content_length:
                    logger.warning(f"Content too short ({len(content)} chars) for {url}")
                    return None
                
                # Truncate if too long
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length] + "\n\n[Content truncated...]"
                    logger.info(f"Content truncated for {url}")
                
                logger.info(f"Successfully extracted {len(content)} chars from {url}")
                return content
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _clean_markdown(self, text: str) -> str:
        """Clean and compact markdown text for LLM consumption."""
        # Remove image references
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # Process line by line to remove nav/boilerplate
        cleaned_lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append('')
                continue
            
            # Skip lines that are mostly links (nav menus)
            text_without_links = re.sub(r'\[([^\]]*)\]\([^\)]+\)', r'\1', stripped)
            text_only = re.sub(r'https?://\S+', '', text_without_links).strip()
            
            # If removing links leaves <40% of original content, it's nav
            if len(stripped) > 30 and len(text_only) < len(stripped) * 0.4:
                continue
            
            # Skip common boilerplate
            if re.match(r'^(Buscar|Bienvenido|Iniciar sesión|Sign|Log in|Cookie|Newsletter|Suscri)', stripped, re.IGNORECASE):
                continue
            
            # Skip tag link lists
            if '/tag/' in stripped and stripped.count('[') > 1:
                continue
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Remove excessive blank lines (3+ → 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove lines that are just whitespace
        text = re.sub(r'\n[ \t]+\n', '\n\n', text)
        # Compact multiple spaces
        text = re.sub(r'[ \t]{2,}', ' ', text)
        return text.strip()
