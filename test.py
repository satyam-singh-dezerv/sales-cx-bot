import chromadb
import sys
import json

def check_doc(thread_id: str):
    """Fetches and prints a specific document from the knowledge base."""
    if not thread_id:
        print("Please provide a thread ID (e.g., 1758271371.915139)")
        return

    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="slack_knowledge_base")

        print(f"\n🔍 Fetching document with ID: {thread_id}...")
        result = collection.get(limit=5)

        print(result)
        

        if not result or not result.get('documents'):
            print("❌ Document not found.")
            return

        print("\n--- Document Content ---")
        # Print the raw text content
        print(result['documents'][0])
        print("\n--- End of Content ---\n")

        print("✅ Done.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_document.py <thread_id>")
    else:
        check_doc(sys.argv[1])