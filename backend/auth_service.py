from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
import os
import psycopg
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
password_hash = PasswordHash.recommended()


def register_user(full_name: str, email: str, password: str):
    hashed_password = password_hash.hash(password)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (full_name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, full_name, email, role, created_at;
                """,
                (full_name.strip(), email.strip().lower(), hashed_password),
            )
            user = cur.fetchone()

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[3],
        "created_at": user[4],
    }



JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


def authenticate_user(email: str, password: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, full_name, email, password_hash, role, is_active
                FROM users
                WHERE email = %s;
                """,
                (email.strip().lower(),),
            )
            user = cur.fetchone()

    if not user or not password_hash.verify(password, user[3]):
        return None

    if not user[5]:
        return None

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[4],
    }


def create_access_token(user: dict) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)



def get_user_by_id(user_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, full_name, email, role, is_active
                FROM users
                WHERE id = %s;
                """,
                (user_id,),
            )
            user = cur.fetchone()

    if not user or not user[4]:
        return None

    return {
        "id": user[0],
        "full_name": user[1],
        "email": user[2],
        "role": user[3],
    }
