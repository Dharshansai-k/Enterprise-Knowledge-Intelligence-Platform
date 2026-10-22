import psycopg
from psycopg.rows import dict_row
from database import get_db_connection

def create_conversation(user_id: int, title: str = "New conversation"):
    conn = get_db_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (user_id, title)
                VALUES (%s, %s)
                RETURNING id, user_id, title, created_at, updated_at;
                """,
                (user_id, title),
            )
            conversation = cursor.fetchone()
            conn.commit()
            return conversation
    finally:
        conn.close()


def list_conversations(user_id: int):
    conn = get_db_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC;
                """,
                (user_id,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def get_conversation(user_id: int, conversation_id: int):
    conn = get_db_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = %s AND user_id = %s;
                """,
                (conversation_id, user_id),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def save_message(
    conversation_id: int,
    role: str,
    content: str,
    sources: list | None = None,
):
    if role not in {"user", "assistant"}:
        raise ValueError("Invalid message role.")

    conn = get_db_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages
                    (conversation_id, role, content, sources)
                VALUES (%s, %s, %s, %s)
                RETURNING id, conversation_id, role, content, sources, created_at;
                """,
                (
                    conversation_id,
                    role,
                    content,
                    psycopg.types.json.Jsonb(sources or []),
                ),
            )

            message = cursor.fetchone()

            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (conversation_id,),
            )

            conn.commit()
            return message
    finally:
        conn.close()


def list_messages(user_id: int, conversation_id: int):
    conn = get_db_connection()

    try:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT m.id, m.role, m.content, m.sources, m.created_at
                FROM chat_messages AS m
                JOIN conversations AS c
                  ON c.id = m.conversation_id
                WHERE c.id = %s AND c.user_id = %s
                ORDER BY m.created_at ASC, m.id ASC;
                """,
                (conversation_id, user_id),
            )
            return cursor.fetchall()
    finally:
        conn.close()
