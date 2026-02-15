"""
Vector Store Manager using ChromaDB and Ollama Embeddings.
"""
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class VectorManager:
    """
    Manages vector database operations for RAG and longterm memory.
    """
    
    def __init__(self, config: Dict[str, Any], ollama_client):
        """
        Initialize VectorManager.
        
        Args:
            config: Configuration dictionary (loaded from config.yaml)
            ollama_client: Instance of OllamaClient
        """
        self.config = config
        self.client = ollama_client
        
        # RAG Config
        self.rag_config = config.get("RAG", {})
        self.embedding_model = self.rag_config.get("EMBEDDING_MODEL", "nomic-embed-text")
        self.similarity_threshold = self.rag_config.get("SIMILARITY_THRESHOLD", 0.7)
        self.max_results = self.rag_config.get("MAX_RESULTS", 3)
        logger.info(f"VectorManager Config: Threshold={self.similarity_threshold}, Max={self.max_results}")
        
        # Initialize ChromaDB
        from src.constants import DATA_DIR
        persist_path = os.path.join(DATA_DIR, "chroma_db")
        os.makedirs(persist_path, exist_ok=True)
        
        self.chroma = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        # Collections
        self.documents_collection = self.chroma.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.memory_collection = self.chroma.get_or_create_collection(
            name="memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"VectorManager initialized with model: {self.embedding_model}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama."""
        return await self.client.generate_embedding(self.embedding_model, text)

    async def add_document(self, text: str, metadata: Dict[str, Any], doc_id: str = None) -> bool:
        """
        Add a document chunk to the vector store.
        """
        try:
            embedding = await self._get_embedding(text)
            if not embedding:
                logger.warning("Failed to generate embedding for document")
                return False
                
            self.documents_collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id or str(hash(text))]
            )
            return True
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            return False

    async def add_memory(self, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Add a memory fragment (fact/conversation) to the vector store.
        """
        try:
            embedding = await self._get_embedding(text)
            if not embedding:
                return False
                
            self.memory_collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {"type": "memory"}],
                ids=[str(hash(text + str(metadata)))] # Basic ID generation
            )
            return True
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return False

    async def delete_memory(self, text_fragment: str) -> bool:
        """
        Delete a memory by finding the most similar entry and removing it.
        """
        try:
            # 1. Find the memory ID first
            results = await self.search(text_fragment, collection_type="memory", limit=1)
            
            if not results:
                logger.warning(f"Memory not found for deletion: {text_fragment}")
                return False
                
            best_match = results[0]
            # Verify it's actually similar enough to avoid accidental deletions
            if best_match['similarity'] < 0.85: # High threshold for deletion
                 logger.warning(f"Deletetion aborted. Best match '{best_match['content']}' similarity {best_match['similarity']} too low.")
                 return False

            # 2. Delete by ID
            # In Chroma, we need the ID. The search results usually return metadatas/documents.
            # We need to query again or store IDs better.
            # Rerunning query to get ID
            query_embedding = await self._get_embedding(text_fragment)
            raw_results = self.memory_collection.query(
                query_embeddings=[query_embedding],
                n_results=1
            )
            
            if raw_results['ids'] and raw_results['ids'][0]:
                target_id = raw_results['ids'][0][0]
                self.memory_collection.delete(ids=[target_id])
                logger.info(f"Deleted memory: {best_match['content']} (ID: {target_id})")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    async def search(self, query: str, collection_type: str = "documents", limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for relevant context in the specified collection.
        """
        limit = limit or self.max_results
        collection = self.documents_collection if collection_type == "documents" else self.memory_collection
        
        try:
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                return []
                
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Parse results
            parsed_results = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    # Convert distance to similarity (0 to 1, where 1 is identical)
                    # Cosine distance: 0 is identical, 2 is opposite. 
                    # Approximate similarity = 1 - distance (for normalized vectors)
                    similarity = 1 - distance 
                    logger.info(f"Candidate: '{doc[:30]}...' Sim: {similarity:.4f} vs Threshold: {self.similarity_threshold}")
                    
                    if similarity >= self.similarity_threshold:
                        parsed_results.append({
                            "content": doc,
                            "metadata": results["metadatas"][0][i],
                            "similarity": similarity
                        })
                        
            return parsed_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
