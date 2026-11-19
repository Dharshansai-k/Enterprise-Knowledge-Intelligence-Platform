import pytest

from chunker import chunk_text


def test_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n ") == []


def test_chunks_respect_size_limit_and_keep_content():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert chunks
    assert all(len(chunk) <= 100 for chunk in chunks)
    combined = " ".join(chunks)
    for word in text.split():
        assert word in combined


def test_long_single_token_is_split_without_data_loss():
    token = "x" * 250
    chunks = chunk_text(token, chunk_size=80, overlap=10)
    assert all(len(chunk) <= 80 for chunk in chunks)
    assert "".join(chunks) == token


@pytest.mark.parametrize(
    "chunk_size,overlap",
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunk_settings_raise(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("some content", chunk_size, overlap)
