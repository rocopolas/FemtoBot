"""Reader module: Extracts relevant content from sources."""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import List, Optional

from src.services.deep_research.models import Source, Chunk
from utils.web_fetcher import WebFetcher

logger = logging.getLogger(__name__)


class Reader:
    """Reads and extracts relevant content chunks from web sources."""
    
    def __init__(
        self,
        llm_client,
        min_relevance: float = 0.7,
        max_concurrent: int = 3,
        fetch_delay: float = 1.0
    ):
        self.client = llm_client
        self.min_relevance = min_relevance
        self.fetcher = WebFetcher()
        self.max_concurrent = max_concurrent
        self.fetch_delay = fetch_delay
    
    async def read_sources(
        self, 
        sources: List[Source], 
        task_query: str, 
        model: str
    ) -> List[Chunk]:
        """
        Extract relevant content chunks from sources.
        Fetches pages concurrently, then runs LLM extraction sequentially
        (local models can only handle one request at a time).
        """
        chunks = []
        
        # PHASE 1: Fetch all pages concurrently (fast IO)
        async def fetch_one(source: Source) -> tuple:
            """Fetch a single source's content."""
            try:
                content = await self._fetch_content(source.url)
                if not content or len(content.strip()) < 50:
                    logger.warning(f"Using description fallback for {source.url}")
                    content = source.description
                source.fetched_content = content
                source.fetched_at = datetime.now()
                return (source, content)
            except Exception as e:
                logger.error(f"Error fetching {source.url}: {e}")
                return (source, source.description)
        
        logger.info(f"Fetching {len(sources)} pages concurrently...")
        fetch_tasks = [fetch_one(s) for s in sources]
        fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # PHASE 2: LLM extraction — ONE AT A TIME (local model limitation)
        for result in fetched:
            if isinstance(result, Exception):
                logger.error(f"Fetch failed: {result}")
                continue
            
            source, content = result
            try:
                extracted = await self._extract_relevant_chunks(
                    content=content,
                    source=source,
                    task_query=task_query,
                    model=model
                )
                chunks.extend(extracted)
                logger.info(f"Extracted {len(extracted)} chunks from {source.url}")
            except Exception as e:
                logger.error(f"Extraction error for {source.url}: {e}")
                # Fallback: use raw content as a chunk
                chunks.append(Chunk(
                    content=content[:2000] if content else source.description,
                    source=source,
                    relevance_score=0.5,
                    extracted_at=datetime.now(),
                    task_id=source.task_id
                ))
        
        logger.info(f"Reader extracted {len(chunks)} chunks from {len(sources)} sources")
        return chunks
    
    async def _fetch_content(self, url: str) -> str:
        """
        Fetch content from URL using WebFetcher (trafilatura).
        
        Args:
            url: The URL to fetch
            
        Returns:
            Extracted main content text or empty string if failed
        """
        try:
            content = await self.fetcher.fetch_content(url)
            return content if content else ""
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return ""
    
    async def _extract_relevant_chunks(
        self, 
        content: str, 
        source: Source,
        task_query: str,
        model: str
    ) -> List[Chunk]:
        """Use LLM to extract relevant chunks from content."""
        prompt = self._create_extraction_prompt(content, source, task_query)
        
        try:
            response = await self._get_llm_response(prompt, model)
            logger.debug(f"Extraction response for {source.url}: {response[:500]}")
            chunks_data = self._parse_extraction_response(response)
            
            chunks = []
            for chunk_data in chunks_data:
                # Validate chunk data
                if not isinstance(chunk_data, dict) or "content" not in chunk_data:
                    continue
                    
                relevance = chunk_data.get("relevance", 0.5)
                
                # Only keep highly relevant chunks
                if relevance >= self.min_relevance:
                    chunk = Chunk(
                        content=chunk_data["content"],
                        source=source,
                        relevance_score=relevance,
                        extracted_at=datetime.now(),
                        task_id=source.task_id
                    )
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting chunks: {e}")
            # Return entire content as single chunk
            return [Chunk(
                content=content[:2000],  # Limit content length
                source=source,
                relevance_score=0.5,
                extracted_at=datetime.now(),
                task_id=source.task_id
            )]
    
    def _create_extraction_prompt(self, content: str, source: Source, task_query: str) -> str:
        """Create prompt for chunk extraction."""
        return f"""You are a Content Extraction Agent. Your task is to extract relevant information from web content.

Task Query: {task_query}
Source Title: {source.title}
Source URL: {source.url}

Content to analyze:
---
{content[:8000] if len(content) > 8000 else content}
---

Extract the most relevant information chunks that answer the task query.
Each chunk should be a complete, self-contained piece of information.

Respond ONLY with a valid JSON array in this format:
[
  {{
    "content": "The extracted text chunk with relevant information",
    "relevance": 0.95
  }},
  {{
    "content": "Another relevant chunk",
    "relevance": 0.85
  }}
]

Guidelines:
- Relevance score: 0.0 to 1.0 (1.0 = highly relevant)
- Extract only substantial information, not fluff
- Each chunk should be 1-3 sentences or a short paragraph
- Maximum 5 chunks per source
- If content is not relevant, return empty array []
"""
    
    async def _get_llm_response(self, prompt: str, model: str) -> str:
        """Get response from LLM (thinking disabled for extraction speed)."""
        messages = [
            {"role": "system", "content": "You are a precise data extraction assistant. Respond ONLY with valid JSON. Do not think out loud or explain."},
            {"role": "user", "content": prompt}
        ]
        full_response = ""
        
        async for chunk in self.client.stream_chat(model, messages):
            full_response += chunk
        
        logger.debug(f"RAW LLM response ({len(full_response)} chars): {full_response[:1000]}")
        
        # Strip thinking tags
        cleaned = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL)
        cleaned = re.sub(r'<think>.*', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()
        
        # If stripping think tags left nothing, try to extract JSON from within them
        if not cleaned:
            # Look for JSON array inside think blocks
            think_match = re.search(r'<think>(.*?)</think>', full_response, flags=re.DOTALL)
            if think_match:
                think_content = think_match.group(1)
                # Try to find a JSON array in the think content
                json_match = re.search(r'(\[[\s\S]*\])', think_content)
                if json_match:
                    cleaned = json_match.group(1).strip()
                    logger.debug("Salvaged JSON from inside <think> block")
            # Also check unclosed think
            if not cleaned:
                think_match = re.search(r'<think>(.*)', full_response, flags=re.DOTALL)
                if think_match:
                    think_content = think_match.group(1)
                    json_match = re.search(r'(\[[\s\S]*\])', think_content)
                    if json_match:
                        cleaned = json_match.group(1).strip()
                        logger.debug("Salvaged JSON from unclosed <think> block")
        
        return cleaned
    
    def _parse_extraction_response(self, response: str) -> List[dict]:
        """Parse JSON response from LLM."""
        # Clean up response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "chunks" in data:
                return data["chunks"]
            else:
                return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse extraction response: {response[:200]}")
            return []
