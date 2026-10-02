import chromadb


CHROMA_PATH = "../chroma_db"

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
    n_results: int = 5
):
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )