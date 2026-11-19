from pathlib import Path

import pytest

from document_parser import extract_text


def test_extracts_utf8_text_and_removes_bom(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("\ufeffHello EKIP\n", encoding="utf-8")
    assert extract_text(str(path), "text/plain") == "Hello EKIP"


def test_rejects_non_utf8_text(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(ValueError, match="UTF-8"):
        extract_text(str(path), "text/plain")


def test_rejects_fake_pdf(tmp_path):
    path = tmp_path / "fake.pdf"
    path.write_text("not a PDF", encoding="utf-8")
    with pytest.raises(ValueError, match="valid PDF"):
        extract_text(str(path), "application/pdf")


def test_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "notes.docx"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Only PDF and TXT"):
        extract_text(str(path), "application/pdf")


def test_missing_file_is_a_validation_error(tmp_path):
    with pytest.raises(ValueError, match="could not be found"):
        extract_text(str(tmp_path / "missing.txt"), "text/plain")
