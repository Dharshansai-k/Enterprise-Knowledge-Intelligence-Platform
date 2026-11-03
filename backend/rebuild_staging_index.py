
from database import get_db_connection
from document_parser import extract_text
from chunker import chunk_text
from embedding_service import generate_embedding
import chromadb
import os
import sys

CHROMA_PATH = "../chroma_db"
STAGING_NAME = "ekip_documents_staging_v1"
CHUNK_SIZE = 1000
OVERLAP = 200

client = chromadb.PersistentClient(path=CHROMA_PATH)


def merge_stored_chunks(chunks):
    """Reconstruct text while removing clear, exact chunk overlap."""
    text = ""

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        if not text:
            text = chunk
            continue

        # Existing chunks used approximately 200 characters of overlap.
        max_overlap = min(300, len(text), len(chunk))
        overlap_size = 0

        for size in range(max_overlap, 99, -1):
            if text.endswith(chunk[:size]):
                overlap_size = size
                break

        text += chunk[overlap_size:] if overlap_size else "\n\n" + chunk

    return text.strip()


def load_documents():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, file_path, file_type, owner_id
                FROM documents
                WHERE id IN (5, 6, 10, 12)
                ORDER BY id;
            """)
            documents = cursor.fetchall()

            cursor.execute("""
                SELECT document_id, chunk_index, content
                FROM document_chunks
                WHERE document_id IN (5, 6, 10, 12)
                ORDER BY document_id, chunk_index;
            """)
            stored_chunks = cursor.fetchall()

    chunks_by_document = {}
    for document_id, chunk_index, content in stored_chunks:
        chunks_by_document.setdefault(document_id, []).append(
            (chunk_index, content)
        )

    prepared = []

    for document_id, filename, file_path, file_type, owner_id in documents:
        if document_id == 10:
            stored = chunks_by_document.get(document_id, [])
            text = merge_stored_chunks(
                [content for _, content in stored]
            )
            source = "recovered_postgres_chunks"
        else:
            if not file_path:
                raise RuntimeError(
                    f"Document {document_id} has no file path."
                )

            resolved_path = os.path.abspath(file_path)
            if not os.path.isfile(resolved_path):
                raise FileNotFoundError(
                    f"Source file missing for document {document_id}: "
                    f"{resolved_path}"
                )

            text = extract_text(resolved_path, file_type or "")
            source = "original_file"

        if not text.strip():
            raise RuntimeError(
                f"No recoverable text for document {document_id}."
            )

        chunks = chunk_text(
            text,
            chunk_size=CHUNK_SIZE,
            overlap=OVERLAP,
        )

        if not chunks:
            raise RuntimeError(
                f"No chunks generated for document {document_id}."
            )

        prepared.append({
            "document_id": document_id,
            "filename": filename,
            "owner_id": owner_id,
            "source": source,
            "chunks": chunks,
        })

        print(
            f"Prepared document {document_id} ({filename}): "
            f"{len(text)} characters, {len(chunks)} chunks, "
            f"source={source}"
        )

    return prepared


def main():
    # Refuse to overwrite an earlier staging collection.
    existing_names = {
        item.name for item in client.list_collections()
    }
    if STAGING_NAME in existing_names:
        raise RuntimeError(
            f"Collection {STAGING_NAME!r} already exists. "
            "Nothing was changed. Choose a new staging name "
            "after inspecting the existing collection."
        )

    # Validate and prepare all source text before creating the collection.
    prepared = load_documents()

    records = []
    for document in prepared:
        document_id = document["document_id"]

        for index, content in enumerate(document["chunks"]):
            metadata = {
                "document_id": document_id,
                "filename": document["filename"],
                "chunk_index": index,
                "source": document["source"],
            }

            if document["owner_id"] is not None:
                metadata["owner_id"] = document["owner_id"]

            records.append({
                "id": f"doc{document_id}_chunk{index}",
                "content": content,
                "metadata": metadata,
            })

    print(f"\nTotal staged chunks to create: {len(records)}")

    # Create a separate collection; do not modify the live collection.
    collection = client.create_collection(
        name=STAGING_NAME,
        metadata={"hnsw:space": "l2"},
    )

    try:
        for start in range(0, len(records), 32):
            batch = records[start:start + 32]

            embeddings = [
                generate_embedding(item["content"])
                for item in batch
            ]

            if any(len(vector) != 384 for vector in embeddings):
                raise RuntimeError(
                    "Unexpected embedding dimension; expected 384."
                )

            collection.add(
                ids=[item["id"] for item in batch],
                documents=[item["content"] for item in batch],
                embeddings=embeddings,
                metadatas=[item["metadata"] for item in batch],
            )

        # Read back the collection and validate its contents.
        result = collection.get(include=["metadatas", "documents"])

        if len(result["ids"]) != len(records):
            raise RuntimeError(
                f"Count mismatch: expected {len(records)}, "
                f"found {len(result['ids'])}."
            )

        if len(set(result["ids"])) != len(records):
            raise RuntimeError("Duplicate IDs detected in staging.")

        indexed_document_ids = {
            metadata["document_id"]
            for metadata in result["metadatas"]
        }
        expected_document_ids = {5, 6, 10, 12}

        if indexed_document_ids != expected_document_ids:
            raise RuntimeError(
                f"Document ID mismatch: {indexed_document_ids}"
            )

        print("\nStaging index created and validated.")
        print("Collection:", collection.name)
        print("Vector count:", collection.count())
        print("Document IDs:", sorted(indexed_document_ids))
        print("Embedding dimension: 384")
        print("Live collection was not modified.")

    except Exception:
        # Only remove the new staging collection on a failed build.
        try:
            client.delete_collection(STAGING_NAME)
            print("Failed staging collection removed.")
        except Exception as cleanup_error:
            print(
                "WARNING: staging cleanup failed:",
                cleanup_error,
                file=sys.stderr,
            )
        raise


if __name__ == "__main__":
    main()
