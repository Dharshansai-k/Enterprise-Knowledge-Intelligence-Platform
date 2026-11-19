from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg
import os
import shutil
from dotenv import load_dotenv
from document_parser import extract_text
from chunker import chunk_text
from rag_service import ask_question
from document_intelligence_service import analyze_document
from pydantic import BaseModel, EmailStr, Field, field_validator
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
    get_recent_messages,
)
import uuid

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    filename: str | None = Field(default=None, max_length=255)
    document_id: int | None = Field(default=None, gt=0)
    conversation_id: int | None = Field(default=None, gt=0)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        return value

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Filename cannot be empty.")
        return value.strip() if value is not None else value


class KnowledgeIssueCreateRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    category: str = Field(
        default="missing_information",
        pattern="^(missing_information|access_problem|incorrect_answer)$"
    )
    details: str | None = Field(default=None, max_length=2000)


class KnowledgeIssueUpdateRequest(BaseModel):
    status: str = Field(
        pattern="^(open|under_review|resolved|rejected)$"
    )
    admin_response: str | None = Field(
        default=None,
        max_length=5000
    )


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

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 non-space characters.")
        return value

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


security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "documents")
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
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

    if len(filename) > 255 or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        total_bytes = 0
        with open(file_path, "wb") as buffer:
            while True:
                block = await file.read(1024 * 1024)
                if not block:
                    break
                total_bytes += len(block)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File is too large. Maximum upload size is 15 MB.",
                    )
                buffer.write(block)

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
            SELECT
                d.id,
                d.filename,
                d.file_type,
                d.uploaded_at,
                d.owner_id,
                u.full_name AS uploaded_by
            FROM documents d
            LEFT JOIN users u ON d.owner_id = u.id
            ORDER BY d.uploaded_at DESC, d.id DESC;
            """
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
                    "owner_id": row[4],
                    "uploaded_by": row[5] or "Unknown",
                }
                for row in rows
            ]

        }

    finally:
        cursor.close()
        conn.close()


@app.get("/documents/{document_id}/intelligence")
def get_document_intelligence(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Generate a document-level overview for any document visible in EKIP."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT filename, file_path FROM documents WHERE id = %s;",
            (document_id,),
        )
        document = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    filename, file_path = document
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail="The original document file is unavailable for analysis.",
        )

    try:
        text = extract_text(file_path, None)
        return {
            "document_id": document_id,
            **analyze_document(filename, file_path, text),
        }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except Exception as error:
        print(f"Document intelligence failed for document {document_id}: {error}")
        raise HTTPException(
            status_code=502,
            detail="Unable to generate document insights. Please try again.",
        )


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if current_user["role"] == "admin":
            cursor.execute(
                """
                SELECT filename, file_path
                FROM documents
                WHERE id = %s;
                """,
                (document_id,),
            )
        else:
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

        # Delete relational records first. Vector cleanup runs after commit:
        # ChromaDB is not part of the PostgreSQL transaction.
        cursor.execute(
            "DELETE FROM document_chunks WHERE document_id = %s;",
            (document_id,),
        )

        if current_user["role"] == "admin":
            cursor.execute(
                "DELETE FROM documents WHERE id = %s;",
                (document_id,),
            )
        else:
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

    # Clean up the vector index after the relational transaction commits.
    # A failure here cannot roll back PostgreSQL; the stale vectors are harmless
    # because search scopes results to document IDs still present in PostgreSQL.
    try:
        delete_document_chunks(document_id)
    except Exception:
        pass

    # Remove the physical file after successful database deletion.
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
    user_id = current_user["id"]
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    print("\n--- ASK API DEBUG ---")
    print("Authenticated user ID:", user_id)
    print("Question:", request.question)
    print("Conversation ID:", request.conversation_id)

    conversation_history = []

    # Validate conversation ownership before accessing its history.
    if request.conversation_id is not None:
        conversation = get_conversation(
            user_id=user_id,
            conversation_id=request.conversation_id,
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        conversation_history = get_recent_messages(
            user_id=user_id,
            conversation_id=request.conversation_id,
            limit=6,
        )

    result = ask_question(
        question=request.question,
        n_results=5,
        user_id=user_id,
        filename=request.filename,
        document_id=request.document_id,
        conversation_history=conversation_history,
    )

    print("Retrieved sources:", len(result["sources"]))
    print("Context length:", len(result["context"]))
    print("History messages:", len(conversation_history))
    print("--- END ASK API DEBUG ---\n")

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"],
        "documents_used": result["documents_used"],
        "context": result["context"],
        "has_sufficient_evidence": result["has_sufficient_evidence"],
        "suggested_questions": result["suggested_questions"],
    }

@app.post("/issues", status_code=201)
def create_knowledge_issue(
    request: KnowledgeIssueCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    details = request.details.strip() if request.details else None

    with get_db_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO knowledge_issues
                (user_id, question, category, details)
            VALUES (%s, %s, %s, %s)
            RETURNING id, question, category, details,
                      status, created_at;
            """,
            (
                current_user["id"],
                question,
                request.category,
                details,
            ),
        ).fetchone()

    return {
        "message": "Issue submitted successfully.",
        "issue": {
            "id": row[0],
            "question": row[1],
            "category": row[2],
            "details": row[3],
            "status": row[4],
            "created_at": row[5].isoformat(),
        },
    }

@app.get("/issues")
def list_my_knowledge_issues(
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                question,
                category,
                details,
                status,
                admin_response,
                created_at,
                updated_at
            FROM knowledge_issues
            WHERE user_id = %s
            ORDER BY created_at DESC;
            """,
            (current_user["id"],),
        ).fetchall()

    return {
        "issues": [
            {
                "id": row[0],
                "question": row[1],
                "category": row[2],
                "details": row[3],
                "status": row[4],
                "admin_response": row[5],
                "created_at": row[6].isoformat(),
                "updated_at": row[7].isoformat(),
            }
            for row in rows
        ],
        "total": len(rows),
    }


@app.get("/admin/issues")
def list_knowledge_issues(
    current_user: dict = Depends(require_role("admin")),
):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ki.id,
                ki.question,
                ki.category,
                ki.details,
                ki.status,
                ki.admin_response,
                ki.created_at,
                ki.updated_at,
                u.email
            FROM knowledge_issues ki
            JOIN users u ON u.id = ki.user_id
            ORDER BY ki.created_at DESC;
            """
        ).fetchall()

    return {
        "issues": [
            {
                "id": row[0],
                "question": row[1],
                "category": row[2],
                "details": row[3],
                "status": row[4],
                "admin_response": row[5],
                "created_at": row[6].isoformat(),
                "updated_at": row[7].isoformat(),
                "reported_by": row[8],
            }
            for row in rows
        ],
        "total": len(rows),
    }


@app.patch("/admin/issues/{issue_id}")
def update_knowledge_issue(
    issue_id: int,
    request: KnowledgeIssueUpdateRequest,
    current_user: dict = Depends(require_role("admin")),
):
    admin_response = (
        request.admin_response.strip()
        if request.admin_response
        else None
    )

    with get_db_connection() as conn:
        row = conn.execute(
            """
            UPDATE knowledge_issues
            SET status = %s,
                admin_response = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, question, category, status,
                      admin_response, updated_at;
            """,
            (
                request.status,
                admin_response,
                issue_id,
            ),
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Knowledge issue not found.",
        )

    return {
        "message": "Knowledge issue updated successfully.",
        "issue": {
            "id": row[0],
            "question": row[1],
            "category": row[2],
            "status": row[3],
            "admin_response": row[4],
            "updated_at": row[5].isoformat(),
        },
    }


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title cannot be empty.")
        return value


class MessageCreateRequest(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=20000)
    sources: list[dict] = Field(default_factory=list, max_length=20)
    suggested_questions: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be empty.")
        return value


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
        suggested_questions=(
            request.suggested_questions
            if request.role == "assistant"
            else []
        ),
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

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title cannot be empty.")
        return value


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
