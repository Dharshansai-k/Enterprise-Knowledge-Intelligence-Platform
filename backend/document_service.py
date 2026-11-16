
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
                WHERE owner_id = %s
                ORDER BY id;
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
                ORDER BY id
                LIMIT 1;
                """,
                (user_id, filename),
            )
            row = cur.fetchone()

    return row[0] if row else None


def get_document_id_by_filename(filename: str) -> int | None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM documents
                WHERE filename = %s
                ORDER BY id
                LIMIT 1;
                """,
                (filename,),
            )
            row = cur.fetchone()

    return row[0] if row else None


def get_all_document_ids() -> list[int]:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM documents
                ORDER BY id;
                """
            )
            rows = cur.fetchall()

    return [row[0] for row in rows]