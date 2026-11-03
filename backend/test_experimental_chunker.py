
from database import get_db_connection
from document_parser import extract_text
from chunker_experimental import chunk_document

DOCUMENT_ID = 12

with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT file_path, file_type
            FROM documents
            WHERE id = %s
            """,
            (DOCUMENT_ID,),
        )
        result = cursor.fetchone()

if not result:
    raise RuntimeError("Document not found")

file_path, file_type = result

text = extract_text(file_path, file_type)

chunks = chunk_document(text)

print("\n========== EXPERIMENTAL CHUNKING ==========")
print("Document ID:", DOCUMENT_ID)
print("Total characters:", len(text))
print("Total chunks:", len(chunks))

for index, chunk in enumerate(chunks):
    print("\n" + "=" * 60)
    print("CHUNK:", index)
    print("SECTION:", chunk["section"])
    print("CHARACTERS:", len(chunk["content"]))
    print("-" * 60)
    print(chunk["content"])

print("\n========== CHUNK METADATA ==========")

for index, chunk in enumerate(chunks):
    print({
        "chunk_id": f"doc12_chunk{index}",
        "document_id": DOCUMENT_ID,
        "chunk_index": index,
        "section": chunk["section"],
        "characters": len(chunk["content"]),
    })