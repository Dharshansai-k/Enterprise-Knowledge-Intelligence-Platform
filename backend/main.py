from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg
import os
import shutil
from dotenv import load_dotenv
from document_parser import extract_text
from chunker import chunk_text

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

#Database connection
def get_db_connection():
    return psycopg.connect(DATABASE_URL)


UPLOAD_DIR = "../documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
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
            INSERT INTO documents (filename, file_path, file_type)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (file.filename, file_path, file.content_type),
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