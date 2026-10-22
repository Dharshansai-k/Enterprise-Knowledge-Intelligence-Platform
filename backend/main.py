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
from embedding_service import generate_embedding
from chroma_service import add_chunk,delete_document_chunks
from database import get_db_connection
from conversation_service import (
    create_conversation,
    list_conversations,
    get_conversation,
    save_message,
    list_messages,
)


class QuestionRequest(BaseModel):
    question: str
    filename: str | None = None





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


UPLOAD_DIR = "../documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)



@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    # Prevent directory traversal through uploaded filenames.
    filename = os.path.basename(file.filename)

    if not filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            text = extract_text(file_path, file.content_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text was found in the document.",
            )

        chunks = chunk_text(text)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No text chunks were generated.",
            )

        # Generate embeddings before writing to the database.
        embeddings = [
            generate_embedding(chunk)
            for chunk in chunks
        ]

        conn = get_db_connection()
        cursor = conn.cursor()
        indexed_chunk_ids = []

        try:
            cursor.execute(
                """
                INSERT INTO documents
                    (filename, file_path, file_type, owner_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    filename,
                    file_path,
                    file.content_type,
                    current_user["id"],
                ),
            )

            document_id = cursor.fetchone()[0]
            chunk_records = []

            for index, chunk in enumerate(chunks):
                cursor.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, content)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (document_id, index, chunk),
                )

                chunk_id = cursor.fetchone()[0]
                chunk_records.append((chunk_id, index, chunk))

            # Index each chunk in ChromaDB.
            for (chunk_id, index, chunk), embedding in zip(
                chunk_records, embeddings
            ):
                add_chunk(
                    chunk_id=str(chunk_id),
                    content=chunk,
                    embedding=embedding,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": index,
                    },
                )
                indexed_chunk_ids.append(str(chunk_id))

            conn.commit()

        except Exception:
            conn.rollback()

            # Best-effort cleanup if some chunks were indexed.
            if indexed_chunk_ids:
                try:
                    from chroma_service import collection
                    collection.delete(ids=indexed_chunk_ids)
                except Exception:
                    pass

            raise

        finally:
            cursor.close()
            conn.close()

        return {
            "message": "Document uploaded and indexed successfully",
            "document_id": document_id,
            "filename": filename,
            "chunks_created": len(chunks),
            "characters_extracted": len(text),
        }

    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail="Document upload or indexing failed.",
        )

    finally:
        await file.close()


@app.get("/documents")
def list_documents(
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, filename, file_type, uploaded_at
            FROM documents
            WHERE owner_id = %s
            ORDER BY uploaded_at DESC, id DESC;
            """,
            (current_user["id"],),
        )

        rows = cursor.fetchall()

        return {
            "documents": [
                {
                    "id": row[0],
                    "filename": row[1],
                    "file_type": row[2],
                    "uploaded_at": (
                        row[3].isoformat() if row[3] else None
                    ),
                }
                for row in rows
            ]
        }

    finally:
        cursor.close()
        conn.close()



@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT filename, file_path
            FROM documents
            WHERE id = %s AND owner_id = %s;
            """,
            (document_id, current_user["id"]),
        )
        document = cursor.fetchone()

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        filename, file_path = document

        # Remove vectors before deleting the database records.
        delete_document_chunks(document_id)

        cursor.execute(
            "DELETE FROM document_chunks WHERE document_id = %s;",
            (document_id,),
        )

        cursor.execute(
            """
            DELETE FROM documents
            WHERE id = %s AND owner_id = %s;
            """,
            (document_id, current_user["id"]),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    # Remove the uploaded file after successful database deletion.
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
        "filename": filename,
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
def ask(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    result = ask_question(
        question=request.question,
        n_results=5,
        user_id=current_user["id"],
        filename=request.filename,
    )

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"],
        "context": result["context"]
    }



class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class MessageCreateRequest(BaseModel):
    role: str
    content: str = Field(min_length=1)
    sources: list[dict] = Field(default_factory=list)


@app.post("/conversations", status_code=201)
def create_conversation_route(
    request: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")

    return create_conversation(
        user_id=current_user["id"],
        title=title,
    )


@app.get("/conversations")
def list_conversations_route(
    current_user: dict = Depends(get_current_user),
):
    conversations = list_conversations(current_user["id"])
    return {"conversations": conversations}


@app.get("/conversations/{conversation_id}")
def get_conversation_route(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    conversation = get_conversation(
        user_id=current_user["id"],
        conversation_id=conversation_id,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = list_messages(
        user_id=current_user["id"],
        conversation_id=conversation_id,
    )

    return {
        "conversation": conversation,
        "messages": messages,
    }



@app.post("/conversations/{conversation_id}/messages", status_code=201)
def save_conversation_message_route(
    conversation_id: int,
    request: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    conversation = get_conversation(
        user_id=current_user["id"],
        conversation_id=conversation_id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    if request.role not in {"user", "assistant"}:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'user' or 'assistant'.",
        )

    if not request.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Message content cannot be empty.",
        )

    message = save_message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        sources=request.sources if request.role == "assistant" else [],
    )

    # Set the title from the first user question.
    if (
        request.role == "user"
        and conversation["title"] == "New conversation"
    ):
        title = " ".join(request.content.strip().split())

        if len(title) > 50:
            title = title[:47].rstrip() + "..."

        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                """,
                (title, conversation_id, current_user["id"]),
            )

    # Return a response for BOTH user and assistant messages.
    return {"message": message}



class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@app.patch("/conversations/{conversation_id}")
def rename_conversation_route(
    conversation_id: int,
    request: ConversationRenameRequest,
    current_user: dict = Depends(get_current_user),
):
    conversation = get_conversation(
        user_id=current_user["id"],
        conversation_id=conversation_id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    title = " ".join(request.title.strip().split())

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty.",
        )

    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE conversations
            SET title = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (title, conversation_id, current_user["id"]),
        )

    return {
        "id": conversation_id,
        "title": title,
    }



@app.delete("/conversations/{conversation_id}")
def delete_conversation_route(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    conversation = get_conversation(
        user_id=current_user["id"],
        conversation_id=conversation_id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    with get_db_connection() as conn:
        conn.execute(
            """
            DELETE FROM conversations
            WHERE id = %s AND user_id = %s
            """,
            (conversation_id, current_user["id"]),
        )

    return {
        "message": "Conversation deleted successfully.",
        "conversation_id": conversation_id,
    }
