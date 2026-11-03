
from database import get_db_connection
from document_parser import extract_text
from chunker_experimental import chunk_document
from embedding_service import generate_embedding

import chromadb

DOCUMENT_ID = 12
COLLECTION_NAME = "ekip_documents_experimental_v2"
CHROMA_PATH = "../chroma_db"

client = chromadb.PersistentClient(path=CHROMA_PATH)


def main():

    # Prevent accidental overwrite
    existing_names = {
        item.name for item in client.list_collections()
    }

    if COLLECTION_NAME in existing_names:
        raise RuntimeError(
            f"{COLLECTION_NAME} already exists. "
            "Inspect it before choosing another collection name."
        )

    # Fetch document information
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, file_path, file_type, owner_id
                FROM documents
                WHERE id = %s
                """,
                (DOCUMENT_ID,),
            )

            document = cursor.fetchone()

    if not document:
        raise RuntimeError("Document not found")

    document_id, filename, file_path, file_type, owner_id = document

    # Extract original document text
    text = extract_text(file_path, file_type)

    if not text.strip():
        raise RuntimeError("No readable text found")

    # Generate experimental chunks
    chunks = chunk_document(
        text,
        chunk_size=800,
        overlap=120,
    )

    if not chunks:
        raise RuntimeError("No chunks generated")

    print("Document:", filename)
    print("Document ID:", document_id)
    print("Experimental chunks:", len(chunks))

    # Prepare embeddings and metadata
    records = []

    for index, chunk in enumerate(chunks):

        embedding = generate_embedding(chunk["content"])

        if len(embedding) != 384:
            raise RuntimeError("Unexpected embedding dimension")

        records.append({
            "id": f"doc{document_id}_exp_chunk{index}",
            "content": chunk["content"],
            "embedding": embedding,
            "metadata": {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
                "section": chunk["section"],
                "owner_id": owner_id,
            },
        })

    # Create a separate experimental collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "l2"},
    )

    try:
        collection.add(
            ids=[item["id"] for item in records],
            documents=[item["content"] for item in records],
            embeddings=[item["embedding"] for item in records],
            metadatas=[item["metadata"] for item in records],
        )

        # Validate indexed records
        result = collection.get(
            include=["documents", "metadatas"]
        )

        if len(result["ids"]) != len(records):
            raise RuntimeError("Staging count mismatch")

        if collection.count() != len(chunks):
            raise RuntimeError("Vector count mismatch")

        print("\nExperimental staging created successfully!")
        print("Collection:", collection.name)
        print("Vector count:", collection.count())

        print("\nIndexed sections:")

        for metadata in result["metadatas"]:
            print(
                f"Chunk {metadata['chunk_index']}: "
                f"{metadata['section']}"
            )

        print("\nLive ChromaDB collection was not modified.")

    except Exception:
        client.delete_collection(COLLECTION_NAME)
        print("Failed experimental collection removed.")
        raise


if __name__ == "__main__":
    main()
