from database import get_db_connection
from document_parser import extract_text
from chunker_experimental import chunk_document
from embedding_service import generate_embedding

import chromadb

DOCUMENT_IDS = [5, 6, 10, 12]
COLLECTION_NAME = "ekip_documents_experimental_all_v3"
CHROMA_PATH = "../chroma_db"

CHUNK_SIZE = 800
OVERLAP = 120

client = chromadb.PersistentClient(path=CHROMA_PATH)


def reconstruct_document_10(chunks):
    """Reconstruct original text by removing overlapping characters."""

    if not chunks:
        raise RuntimeError("No stored chunks found for document 10")

    reconstructed = chunks[0]

    for chunk in chunks[1:]:
        max_overlap = min(len(reconstructed), len(chunk))

        overlap = 0

        for size in range(max_overlap, 0, -1):
            if reconstructed.endswith(chunk[:size]):
                overlap = size
                break

        reconstructed += chunk[overlap:]

    return reconstructed


def fetch_document(document_id):

    with get_db_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT id, filename, file_path, file_type, owner_id
                FROM documents
                WHERE id = %s
                """,
                (document_id,),
            )

            document = cursor.fetchone()

            if not document:
                raise RuntimeError(
                    f"Document {document_id} not found"
                )

            document_id, filename, file_path, file_type, owner_id = document

            if document_id == 10:
                cursor.execute(
                    """
                    SELECT content
                    FROM document_chunks
                    WHERE document_id = %s
                    ORDER BY chunk_index
                    """,
                    (document_id,),
                )

                stored_chunks = [
                    row[0] for row in cursor.fetchall()
                ]

                text = reconstruct_document_10(stored_chunks)

            else:
                text = extract_text(file_path, file_type)

    return document_id, filename, owner_id, text


def main():

    existing_names = {
        item.name for item in client.list_collections()
    }

    if COLLECTION_NAME in existing_names:
        raise RuntimeError(
            f"{COLLECTION_NAME} already exists. "
            "Inspect it before choosing another name."
        )

    records = []

    for document_id in DOCUMENT_IDS:

        print(f"\nProcessing document {document_id}...")

        document_id, filename, owner_id, text = fetch_document(
            document_id
        )

        if not text.strip():
            raise RuntimeError(
                f"No readable text for document {document_id}"
            )

        chunks = chunk_document(
            text,
            chunk_size=CHUNK_SIZE,
            overlap=OVERLAP,
        )

        print("Filename:", filename)
        print("Extracted characters:", len(text))
        print("Experimental chunks:", len(chunks))

        for index, chunk in enumerate(chunks):

            embedding = generate_embedding(chunk["content"])

            if len(embedding) != 384:
                raise RuntimeError(
                    "Unexpected embedding dimension"
                )

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

    if not records:
        raise RuntimeError("No experimental chunks generated")

    print("\nTotal experimental chunks:", len(records))

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

        if collection.count() != len(records):
            raise RuntimeError("Vector count mismatch")

        print("\nExperimental collection created successfully!")
        print("Collection:", collection.name)
        print("Total vectors:", collection.count())

        print("\nDocument-wise chunk counts:")

        for document_id in DOCUMENT_IDS:

            result = collection.get(
                where={"document_id": document_id},
                include=["metadatas"],
            )

            print(
                f"Document {document_id}: "
                f"{len(result['ids'])} chunks"
            )

        print("\nLive collection was not modified.")
        print("Previous experimental collection was not modified.")

    except Exception:
        client.delete_collection(COLLECTION_NAME)
        print("Failed experimental collection removed.")
        raise


if __name__ == "__main__":
    main()