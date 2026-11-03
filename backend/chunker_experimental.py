
import re
from chunker import chunk_text

SECTION_HEADINGS = {
    "PROFESSIONAL SUMMARY",
    "EDUCATION",
    "TECHNICAL SKILLS",
    "PROJECTS",
    "CERTIFICATIONS",
    "INTERNSHIP EXPERIENCE",
    "EXPERIENCE",
    "SKILLS",
    "PUBLICATIONS",
    "ACHIEVEMENTS",
}

def detect_sections(text):
    lines = text.splitlines()
    sections = []
    current_heading = "GENERAL"
    current_content = []

    for line in lines:
        cleaned = line.strip()

        if not cleaned:
            continue

        normalized = re.sub(
            r"\s+", " ", cleaned
        ).strip().upper()

        if normalized in SECTION_HEADINGS:
            if current_content:
                sections.append({
                    "section": current_heading,
                    "content": "\n".join(current_content),
                })

            current_heading = normalized
            current_content = []
        else:
            current_content.append(cleaned)

    if current_content:
        sections.append({
            "section": current_heading,
            "content": "\n".join(current_content),
        })

    return sections


def chunk_document(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
):
    if not text or not text.strip():
        return []

    sections = detect_sections(text)
    final_chunks = []

    for section_data in sections:
        heading = section_data["section"]
        content = section_data["content"]

        if not content.strip():
            continue

        content_chunks = chunk_text(
            content,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk in content_chunks:
            final_chunks.append({
                "section": heading,
                "content": f"{heading}\n{chunk}",
            })

    return final_chunks
