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

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"document_id": {"$in": allowed_document_ids}},
    )


def delete_document_chunks(document_id: int):
    collection.delete(
        where={"document_id": document_id}
    )
