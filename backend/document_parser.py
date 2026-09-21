from pathlib import Path
from pypdf import PdfReader


def extract_text(file_path: str, file_type: str) -> str:
    path = Path(file_path)

    if file_type == "application/pdf" or path.suffix.lower() == ".pdf":
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()

    if file_type == "text/plain" or path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8").strip()

    raise ValueError(f"Unsupported file type: {file_type}")