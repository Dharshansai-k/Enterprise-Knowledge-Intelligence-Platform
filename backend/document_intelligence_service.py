"""Document-level analysis helpers for EKIP."""

import json
import os
import re
from pathlib import Path

from groq import Groq
from pypdf import PdfReader

MODEL_NAME = "openai/gpt-oss-20b"


def _extract_sections(text: str) -> list[str]:
    """Detect likely headings from extracted text without requiring an LLM."""
    headings = []
    seen = set()

    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or len(line) > 110:
            continue

        numbered = re.match(r"^(?:\d+(?:\.\d+)*[.)]?\s+|chapter\s+\w+|section\s+\w+)", line, re.I)
        title_case = (
            len(line.split()) <= 12
            and line == line.title()
            and not line.endswith((".", ",", ";"))
        )
        all_caps = len(line.split()) <= 12 and line.isupper() and any(ch.isalpha() for ch in line)

        if numbered or title_case or all_caps:
            normalized = line.strip(" :-")
            key = normalized.casefold()
            if normalized and key not in seen:
                headings.append(normalized)
                seen.add(key)

        if len(headings) >= 30:
            break

    return headings


def _get_page_count(file_path: str) -> int | None:
    if Path(file_path).suffix.lower() != ".pdf":
        return None
    try:
        return len(PdfReader(file_path).pages)
    except Exception:
        return None


def _generate_ai_insights(filename: str, text: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)
    # Keep the prompt bounded for long documents. The source text remains
    # document-grounded; this is an initial document overview, not exhaustive QA.
    source_text = text[:24000]
    prompt = f"""Analyze the following uploaded document for an enterprise knowledge platform.
Return ONLY a valid JSON object with these keys:
- summary: a faithful overview in 3-5 sentences
- key_topics: an array of 4-8 short topic labels
- key_takeaways: an array of 3-6 concise factual takeaways

Use only information explicitly present in the document. Do not infer missing facts.
If the document is too short for a field, return fewer items rather than inventing content.

Filename: {filename}

Document text:
{source_text}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a careful document analyst. Never invent information. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=2048,
        temperature=0.2,
        reasoning_effort="low",
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("The document analysis model returned an empty response.")

    data = json.loads(content)
    summary = data.get("summary")
    topics = data.get("key_topics", [])
    takeaways = data.get("key_takeaways", [])

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("The document analysis response did not contain a valid summary.")
    if not isinstance(topics, list) or not isinstance(takeaways, list):
        raise ValueError("The document analysis response had an invalid structure.")

    return {
        "summary": summary.strip(),
        "key_topics": [str(item).strip() for item in topics if str(item).strip()][:8],
        "key_takeaways": [str(item).strip() for item in takeaways if str(item).strip()][:6],
    }


def analyze_document(filename: str, file_path: str, text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("No readable text was found in this document.")

    return {
        "filename": filename,
        "file_size_bytes": os.path.getsize(file_path),
        "page_count": _get_page_count(file_path),
        "character_count": len(text),
        "word_count": len(text.split()),
        "sections": _extract_sections(text),
        **_generate_ai_insights(filename, text),
    }
