import psycopg

from embedding_service import generate_embedding
from chroma_service import add_chunk


DATABASE_URL = "postgresql://ekip_user:ekip-password@localhost:5432/ekip_db"


def index_documents():
    conn = psycopg.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            dc.id,
            dc.document_id,
            dc.chunk_index,
            dc.content,
            d.filename
        FROM document_chunks dc
        JOIN documents d
            ON dc.document_id = d.id
        ORDER BY dc.id;
    """)

    chunks = cursor.fetchall()

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

    cursor.close()
    conn.close()

    print("All chunks indexed successfully!")


if __name__ == "__main__":
    index_documents()