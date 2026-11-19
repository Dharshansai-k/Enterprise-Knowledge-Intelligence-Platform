"""Safe text extraction for uploaded PDF and TXT documents."""

from pathlib import Path

from pypdf import PdfReader


def extract_text(file_path: str, file_type: str | None = None) -> str:
    path = Path(file_path)

    if not path.is_file():
        raise ValueError("The uploaded document could not be found.")

    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise ValueError("Only PDF and TXT files are supported.")

    if suffix == ".pdf":
        try:
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ValueError("The file is not a valid PDF document.")
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("Password-protected PDFs are not supported.")
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("The PDF is corrupted, unreadable, or unsupported.") from error

    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError as error:
        raise ValueError("The TXT file must use UTF-8 text encoding.") from error
    except OSError as error:
        raise ValueError("The TXT file could not be read.") from error
