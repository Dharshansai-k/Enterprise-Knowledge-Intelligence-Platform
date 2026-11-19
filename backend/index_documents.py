"""Rebuild the Chroma index from PostgreSQL-backed document chunks."""

from database import get_db_connection
from embedding_service import generate_embedding
from chroma_service import add_chunk


def index_documents():
    with get_db_connection() as conn:
        chunks = conn.execute(
            """
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                d.filename
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            ORDER BY dc.id;
            """
        ).fetchall()

    print(f"Found {len(chunks)} chunks")

    for chunk_id, document_id, chunk_index, content, filename in chunks:
        print(f"Indexing chunk {chunk_id}...")
        embedding = generate_embedding(content)
        add_chunk(
            chunk_id=str(chunk_id),
            content=content,
            embedding=embedding,
            metadata={
                "document_id": document_id,
                "chunk_index": chunk_index,
                "filename": filename,
            },
        )

    print("All chunks indexed successfully!")


if __name__ == "__main__":
    index_documents()
