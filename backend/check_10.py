from database import get_db_connection

DOCUMENT_ID = 10

original_text = "\n".join(
    chunk[2] for chunk in chunks
)
with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, chunk_index, content
            FROM document_chunks
            WHERE document_id = %s
            ORDER BY chunk_index
            """,
            (DOCUMENT_ID,),
        )

        chunks = cursor.fetchall()

print("Document ID:", DOCUMENT_ID)
print("Stored chunks:", len(chunks))

for chunk_id, chunk_index, content in chunks:
    print(f"\nChunk ID: {chunk_id}")
    print(f"Chunk Index: {chunk_index}")
    print(f"Content length: {len(content)}")
    print(content[:200])
    print("Chunk 0 ends:", chunks[0][2][-250:])
    print("Chunk 1 starts:", chunks[1][2][:250])

    print("\nChunk 1 ends:", chunks[1][2][-250:])
    print("Chunk 2 starts:", chunks[2][2][:250])