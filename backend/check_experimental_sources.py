import os
from database import get_db_connection

DOCUMENT_IDS = [5, 6, 10, 12]

with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, filename, file_path, file_type, owner_id
            FROM documents
            WHERE id = ANY(%s)
            ORDER BY id
            """,
            (DOCUMENT_IDS,),
        )

        documents = cursor.fetchall()

for doc in documents:
    document_id, filename, file_path, file_type, owner_id = doc

    print(f"\nDocument ID: {document_id}")
    print(f"Filename: {filename}")
    print(f"File path: {file_path}")
    print(f"File exists: {os.path.exists(file_path) if file_path else False}")