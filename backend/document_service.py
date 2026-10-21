
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_user_document_ids(user_id: int) -> list[int]:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM documents
                WHERE owner_id = %s;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    return [row[0] for row in rows]


def get_user_document_id_by_filename(
    user_id: int,
    filename: str,
) -> int | None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM documents
                WHERE owner_id = %s
                  AND filename = %s
                ORDER BY uploaded_at DESC, id DESC
                LIMIT 1;
                """,
                (user_id, filename),
            )
            row = cur.fetchone()

    return row[0] if row else None
