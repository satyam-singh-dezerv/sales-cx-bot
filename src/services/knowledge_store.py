# src/services/knowledge_store.py

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class KnowledgeStore:
    """
    Manages the vector database (ChromaDB) and the embedding model.
    """
    def __init__(self, path: str = "./chroma_db"):
        # 1. Load a powerful but lightweight embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 2. Set up the ChromaDB client and collection
        # This will create the DB in a local folder named 'chroma_db'
        self.client = chromadb.PersistentClient(path=path)
        
        # A 'collection' is like a table in a traditional database
        self.collection = self.client.get_or_create_collection(
            name="slack_knowledge_base"
        )
        print("Knowledge store initialized.")

    def _create_chunk_from_thread(self, thread: Dict) -> str:
        """
        Creates a single text document from a Slack thread for embedding.
        This is our 'chunking' strategy.
        """
        # Start with the parent message
        text = f"User '{thread['user']}' started a thread:\n{thread['text']}\n"
        
        # Add all replies
        if thread['replies']:
            text += "\n--- Replies ---\n"
            for reply in thread['replies']:
                text += f"User '{reply['user']}' replied:\n{reply['text']}\n"
        
        return text.strip()

    def add_thread(self, thread: Dict):
        """
        Processes a single Slack thread, creates an embedding, and stores it.
        """
        thread_id = thread['ts'] # Use the thread timestamp as a unique ID
        
        document = self._create_chunk_from_thread(thread)
        
        # ChromaDB can handle embedding internally, but doing it explicitly
        # gives us more control and allows using any model.
        vector = self.model.encode(document).tolist()
        
        metadata = {
            "user": thread['user'],
            "datetime_utc": thread['datetime_utc'],
            "reply_count": thread['reply_count'],
            "source": "slack"
        }
        
        # 'Upsert' will add the document if the ID doesn't exist, 
        # or update it if it does.
        self.collection.upsert( # CHANGED from .add() to .upsert()
            ids=[thread_id],
            embeddings=[vector],
            documents=[document],
            metadatas=[metadata]
        )
        print(f"Upserted thread {thread_id} in knowledge base.")


    def query_knowledge(self, query_text: str, n_results: int = 5) -> Dict:
        """
        Searches the knowledge base for relevant documents.
        """
        # Create an embedding for the user's query
        query_vector = self.model.encode(query_text).tolist()
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=n_results
        )
        
        return results