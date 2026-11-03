import re

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size"
        )

    # Normalize whitespace while preserving paragraph boundaries.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    # Split long paragraphs into sentences, then split oversized
    # sentences by words so no unit exceeds chunk_size.
    units = []

    for paragraph in paragraphs:
        sentences = (
            [paragraph]
            if len(paragraph) <= chunk_size
            else re.split(r"(?<=[.!?])\s+", paragraph)
        )

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) <= chunk_size:
                units.append(sentence)
                continue

            words = sentence.split()
            part = ""

            for word in words:
                # Handle a single word longer than the limit.
                if len(word) > chunk_size:
                    if part:
                        units.append(part)
                        part = ""

                    for start in range(0, len(word), chunk_size):
                        units.append(word[start:start + chunk_size])
                    continue

                candidate = f"{part} {word}".strip()

                if len(candidate) > chunk_size:
                    if part:
                        units.append(part)
                    part = word
                else:
                    part = candidate

            if part:
                units.append(part)

    # Pack units and retain previous units as actual overlap.
    chunks = []
    current = []

    def chunk_length(items):
        return sum(len(item) for item in items) + max(0, len(items) - 1)

    for unit in units:
        candidate = current + [unit]

        if chunk_length(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append("\n".join(current))

        # Keep the largest suffix that fits the overlap budget.
        overlap_units = []
        for previous in reversed(current):
            candidate_overlap = [previous] + overlap_units

            if chunk_length(candidate_overlap) > overlap:
                break

            overlap_units = candidate_overlap

        # Always make progress, even if overlap leaves no room.
        current = overlap_units

        if chunk_length(current + [unit]) <= chunk_size:
            current.append(unit)
        else:
            current = [unit]

    if current:
        chunks.append("\n".join(current))

    return chunks
