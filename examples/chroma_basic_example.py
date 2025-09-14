#!/usr/bin/env python3
"""
Basic Chroma Vector Database Integration with LangChain
======================================================

This script demonstrates how to:
1. Connect to a Chroma vector database running in Docker
2. Create a collection
3. Add documents with embeddings
4. Perform similarity search
5. Basic CRUD operations

Prerequisites:
- Docker container running: docker-compose -f docker/docker-compose.dev.yml up -d
- Environment variables set (OPENAI_API_KEY)
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

class ChromaVectorStore:
    """Simple wrapper for Chroma vector store operations"""
    
    def __init__(self, collection_name: str = "warp_collection", host: str = "localhost", port: int = 8000):
        """Initialize Chroma client and vector store"""
        self.collection_name = collection_name
        self.host = host
        self.port = port
        
        # Initialize embeddings (requires OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings()
        
        # Connect to Chroma server
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize LangChain Chroma vector store
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            client=self.client
        )
        
        print(f"✅ Connected to Chroma at {host}:{port}")
        print(f"📂 Using collection: {collection_name}")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]] = None) -> List[str]:
        """Add documents to the vector store"""
        doc_objects = [Document(page_content=doc) for doc in documents]
        
        if metadatas:
            for i, metadata in enumerate(metadatas):
                if i < len(doc_objects):
                    doc_objects[i].metadata = metadata
        
        ids = self.vectorstore.add_documents(doc_objects)
        print(f"✅ Added {len(ids)} documents to vector store")
        return ids
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform similarity search"""
        results = self.vectorstore.similarity_search(query, k=k)
        print(f"🔍 Found {len(results)} similar documents for query: '{query}'")
        return results
    
    def similarity_search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """Perform similarity search with scores"""
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        print(f"🔍 Found {len(results)} similar documents with scores")
        return results
    
    def get_collection_info(self) -> Dict:
        """Get collection information"""
        collection = self.client.get_collection(self.collection_name)
        info = {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata
        }
        print(f"📊 Collection Info: {info}")
        return info
    
    def delete_collection(self):
        """Delete the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            print(f"🗑️ Deleted collection: {self.collection_name}")
        except Exception as e:
            print(f"⚠️ Error deleting collection: {e}")


def main():
    """Main demonstration function"""
    print("🚀 Starting Chroma Vector Store Demo")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Please set OPENAI_API_KEY environment variable")
        return
    
    try:
        # Initialize vector store
        vector_store = ChromaVectorStore()
        
        # Sample documents about Warp Terminal and development
        sample_documents = [
            "Warp is a modern terminal built for developers with AI-powered features and workflows.",
            "Vector databases store high-dimensional vectors and enable semantic search capabilities.",
            "LangChain provides a framework for developing applications powered by language models.",
            "Docker containers provide isolated environments for running applications consistently.",
            "Chroma is an open-source vector database designed for AI applications and embeddings.",
            "Semantic search allows finding documents based on meaning rather than exact keyword matches.",
            "Terminal automation can significantly improve developer productivity and workflow efficiency.",
            "RAG (Retrieval Augmented Generation) combines vector search with language model generation.",
        ]
        
        sample_metadata = [
            {"category": "terminal", "source": "warp-docs"},
            {"category": "database", "source": "vector-db-guide"},
            {"category": "ai-framework", "source": "langchain-docs"},
            {"category": "containerization", "source": "docker-docs"},
            {"category": "database", "source": "chroma-docs"},
            {"category": "search", "source": "ai-concepts"},
            {"category": "automation", "source": "dev-productivity"},
            {"category": "ai-architecture", "source": "rag-patterns"},
        ]
        
        # Add documents
        print("\n📝 Adding sample documents...")
        doc_ids = vector_store.add_documents(sample_documents, sample_metadata)
        
        # Get collection info
        print("\n📊 Collection Information:")
        vector_store.get_collection_info()
        
        # Perform searches
        test_queries = [
            "What is Warp terminal?",
            "How do vector databases work?",
            "Docker containers for development",
            "AI-powered search capabilities"
        ]
        
        print("\n🔍 Performing similarity searches...")
        for query in test_queries:
            print(f"\n Query: {query}")
            results = vector_store.similarity_search(query, k=3)
            
            for i, doc in enumerate(results):
                print(f"   {i+1}. {doc.page_content}")
                if doc.metadata:
                    print(f"      Metadata: {doc.metadata}")
        
        # Search with scores
        print(f"\n🎯 Similarity search with scores for: '{test_queries[0]}'")
        scored_results = vector_store.similarity_search_with_score(test_queries[0], k=3)
        
        for doc, score in scored_results:
            print(f"   Score: {score:.4f} - {doc.page_content}")
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure Docker container is running: docker-compose -f docker/docker-compose.dev.yml up -d")


if __name__ == "__main__":
    main()