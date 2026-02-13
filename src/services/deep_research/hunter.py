"""Hunter module: Searches for relevant sources."""
import logging
from typing import List

from src.services.deep_research.models import ResearchTask, Source
from utils.search_utils import BraveSearch

logger = logging.getLogger(__name__)


class Hunter:
    """Finds relevant web sources for a given research task."""
    
    def __init__(self, search_count: int = 5):
        self.search_count = search_count
    
    async def hunt(self, task: ResearchTask) -> List[Source]:
        """
        Execute search for a task and return relevant sources.
        
        Args:
            task: The research task to search for
            
        Returns:
            List of Source objects
        """
        logger.info(f"Hunter searching for task: {task.query}")
        
        try:
            # Use Brave Search API
            search_results = await BraveSearch.search(
                query=task.query,
                count=self.search_count
            )
            
            # Parse results and create Source objects
            sources = self._parse_search_results(search_results, task.id)
            
            logger.info(f"Hunter found {len(sources)} sources for task {task.id}")
            return sources
            
        except Exception as e:
            logger.error(f"Error in hunter for task {task.id}: {e}")
            return []
    
    def _parse_search_results(self, results: str, task_id: str) -> List[Source]:
        """Parse Brave Search results into Source objects."""
        sources = []
        
        if not results or results.startswith("[") or results.startswith("No results"):
            return sources
        
        # Parse the formatted results from BraveSearch
        # Format: "1. **Title**\n   Description\n   URL"
        entries = results.split("\n\n")
        
        for entry in entries:
            lines = entry.strip().split("\n")
            if len(lines) >= 3:
                # Extract title (remove number prefix and bold markers)
                title_line = lines[0]
                title = title_line.split(". ", 1)[-1] if ". " in title_line else title_line
                title = title.replace("**", "").strip()
                
                # Extract description
                description = lines[1].strip()
                
                # Extract URL
                url = lines[2].strip()
                
                source = Source(
                    url=url,
                    title=title,
                    description=description,
                    task_id=task_id
                )
                sources.append(source)
        
        return sources
