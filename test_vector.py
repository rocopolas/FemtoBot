import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.memory.vector_store import VectorManager
from src.client import OllamaClient
from utils.logger import setup_logging
from utils.config_loader import get_all_config

async def main():
    setup_logging()
    
    config = get_all_config()
    client = OllamaClient()
    manager = VectorManager(config, client)
    
    docs_count = manager.documents_collection.count()
    mem_count = manager.memory_collection.count()
    print(f"Total documents before: {docs_count}")
    
    # Add a document
    doc_text = "Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval with a text generator model."
    metadata = {"source": "test_script.py"}
    success = await manager.add_document(doc_text, metadata)
    print(f"Adding document success: {success}")
    
    docs_count = manager.documents_collection.count()
    print(f"Total documents after: {docs_count}")
    
    query = "What is RAG?"
    print(f"Querying: {query}")
    
    docs_results = await manager.search(query, collection_type="documents", limit=5)
    mem_results = await manager.search(query, collection_type="memory", limit=5)
    
    print("\nDocument Results:")
    for res in docs_results:
        print(f"Sim: {res['similarity']:.4f}, Content: {res['content'][:50]}")
        
    print("\nMemory Results:")
    for res in mem_results:
        print(f"Sim: {res['similarity']:.4f}, Content: {res['content'][:50]}")

if __name__ == "__main__":
    asyncio.run(main())
