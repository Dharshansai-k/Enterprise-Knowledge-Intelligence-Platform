from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg
import os
import shutil
from dotenv import load_dotenv
from document_parser import extract_text
from chunker import chunk_text
from rag_service import ask_question
from pydantic import BaseModel, EmailStr, Field
from psycopg.errors import UniqueViolation
from auth_service import authenticate_user, create_access_token, register_user
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth_service import get_user_by_id

class QuestionRequest(BaseModel):
    question: str



load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="EKIP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


@app.post("/auth/login")
def login(request: LoginRequest):
    user = authenticate_user(
        email=str(request.email),
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800,
        "user": user,
    }




class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

#LoginRequest model
@app.post("/auth/register", status_code=201)
def register(request: RegisterRequest):
    try:
        return register_user(
            full_name=request.full_name,
            email=str(request.email),
            password=request.password,
        )

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again.",
        )


security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT configuration is missing",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive",
        )

    return user


def require_role(*allowed_roles: str):
    def role_checker(
        current_user: dict = Depends(get_current_user),
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return role_checker


@app.get("/admin/test")
def admin_test(
    current_user: dict = Depends(require_role("admin")),
):
    return {
        "message": "Admin access granted",
        "user": current_user["email"],
        "role": current_user["role"],
    }


@app.get("/auth/me")
def read_current_user(
    current_user: dict = Depends(get_current_user),
):
    return current_user



#Database connection
def get_db_connection():
    return psycopg.connect(DATABASE_URL)


UPLOAD_DIR = "../documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...),current_user: dict = Depends(get_current_user),):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text(file_path, file.content_type)
    except ValueError as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    chunks = chunk_text(text)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO documents
                (filename, file_path, file_type, owner_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                file.filename,
                file_path,
                file.content_type,
                current_user["id"],
            ),
        )

        document_id = cursor.fetchone()[0]

        for index, chunk in enumerate(chunks):
            cursor.execute(
                """
                INSERT INTO document_chunks
                (document_id, chunk_index, content)
                VALUES (%s, %s, %s);
                """,
                (document_id, index, chunk),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return {
        "message": "Document processed successfully",
        "document_id": document_id,
        "filename": file.filename,
        "chunks_created": len(chunks),
        "characters_extracted": len(text),
    }
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text(file_path, file.content_type)
    except ValueError as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents (filename, file_path, file_type)
        VALUES (%s, %s, %s)
        RETURNING id;
        """,
        (file.filename, file_path, file.content_type),
    )

    document_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "message": "Document uploaded and text extracted successfully",
        "document_id": document_id,
        "filename": file.filename,
        "characters_extracted": len(text),
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-test")
def db_test():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_database(), current_user;")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        "database": result[0],
        "user": result[1],
        "status": "connected"
    }

@app.post("/ask")
def ask(request: QuestionRequest):

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    result = ask_question(
        question=request.question,
        n_results=5
    )

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"],
        "context": result["context"]
    }