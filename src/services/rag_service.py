"""
RAG Service for managing context retrieval and formatting.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RagService:
    def __init__(self, vector_manager):
        self.vector_manager = vector_manager

    async def get_context(self, query: str, limit: int = 3) -> str:
        """
        Retrieve and format context from vector store.
        """
        try:
            # Search both collections
            docs_results = await self.vector_manager.search(query, collection_type="documents", limit=limit)
            mem_results = await self.vector_manager.search(query, collection_type="memory", limit=limit)
            
            # Combine and sort by similarity
            all_results = docs_results + mem_results
            all_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            # Take top results
            search_results = all_results[:limit]
            
            if search_results:
                 logger.info(f"🔍 RAG Results found: {len(search_results)}")
                 rag_entries = [
                    f"- {res['content']} (Sim: {res.get('similarity', 0):.2f})"
                    for res in search_results
                ]
                 context = "\n\n# Contexto Recuperado (RAG)\n" + "\n".join(rag_entries)
                 logger.info(f"📄 RAG Context injected: {context[:50]}...")
                 return context
            else:
                 logger.info("❌ No RAG results found.")
                 return ""
        except Exception as e:
            logger.error(f"RAG Error: {e}", exc_info=True)
            return ""
