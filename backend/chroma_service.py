import chromadb
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name="ekip_documents"
)

def add_chunk(
    chunk_id: str,
    content: str,
    embedding: list,
    metadata: dict
):
    collection.add(
        ids=[chunk_id],
        documents=[content],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def search_chunks(
    query_embedding: list,
    n_results: int = 5,
    allowed_document_ids: list[int] | None = None,
):
    if not allowed_document_ids:
        return {
            "documents": [[]],
            "metadatas": [[]],
            "ids": [[]],
            "distances": [[]],
        }
    print("\n--- CHROMA DEBUG ---")
    print("Chroma path:", CHROMA_PATH)
    print("Collection:", collection.name)
    print("Collection count:", collection.count())
    print("Allowed IDs:", allowed_document_ids)
    print("Requested results:", n_results)
    print("--- END CHROMA DEBUG ---\n")
    # Execute semantic search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"document_id": {"$in": allowed_document_ids}},
    )
    return results


def delete_document_chunks(document_id: int):
    collection.delete(
        where={"document_id": document_id}
    )
