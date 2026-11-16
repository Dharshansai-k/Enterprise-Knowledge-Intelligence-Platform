import math
import re
from collections import OrderedDict
from functools import lru_cache

from rank_bm25 import BM25Okapi

from chroma_service import collection, search_chunks
from document_service import (
    get_document_id_by_filename,
    get_all_document_ids,
)
from embedding_service import generate_embedding


def _empty_results():
    return {
        "documents": [[]],
        "metadatas": [[]],
        "ids": [[]],
        "distances": [[]],
    }



def _diversify_global_results(results, limit: int):
    """
    Preserve relevance ranking while allowing up to two chunks
    from the same document in global search results.
    """
    ids = (results.get("ids") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    selected = []
    document_counts = {}

    for chunk_id, content, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        metadata = metadata or {}
        document_id = str(metadata.get("document_id", "unknown"))

        # Allow at most two chunks per document.
        if document_counts.get(document_id, 0) >= 2:
            continue

        selected.append((chunk_id, content, metadata, distance))
        document_counts[document_id] = (
            document_counts.get(document_id, 0) + 1
        )

        if len(selected) >= limit:
            break

    return {
        "ids": [[row[0] for row in selected]],
        "documents": [[row[1] for row in selected]],
        "metadatas": [[row[2] for row in selected]],
        "distances": [[row[3] for row in selected]],
    }


def _tokenize(text: str) -> list[str]:
    return re.findall(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        (text or "").lower()
    )

@lru_cache(maxsize=8)
def _get_bm25_index(
    allowed_document_ids: tuple[int, ...],
    _collection_count: int,
):
    data = collection.get(
        where={"document_id": {"$in": list(allowed_document_ids)}},
        include=["documents", "metadatas"],
    )
    ids = data.get("ids") or []
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []

    chunks = []
    for chunk_id, content, metadata in zip(ids, documents, metadatas):
        tokens = _tokenize(content or "")
        if tokens:
            chunks.append(
                {
                    "id": chunk_id,
                    "document": content or "",
                    "metadata": metadata or {},
                    "tokens": tokens,
                }
            )

    if not chunks:
        return chunks, None
    return chunks, BM25Okapi([chunk["tokens"] for chunk in chunks])


def _lexical_search(query: str, allowed_document_ids: list[int], limit: int):
    """Return BM25-ranked chunks from the same document scope as dense search."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    chunks, bm25 = _get_bm25_index(
        tuple(sorted(set(allowed_document_ids))),
        collection.count(),
    )
    if not chunks or bm25 is None:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked = sorted(
        range(len(chunks)),
        key=lambda index: (-float(scores[index]), index),
    )

    return [
        {
            "id": chunks[index]["id"],
            "document": chunks[index]["document"],
            "metadata": chunks[index]["metadata"],
            "distance": None,
        }
        for index in ranked[:limit]
        if float(scores[index]) != 0
    ]


def _reciprocal_rank_fusion(dense_results, lexical_results, limit: int):
    """Combine semantic and exact-term rankings without comparing unlike scores."""
    scores = {}
    dense_ranks = {}
    lexical_ranks = {}
    rows_by_id = {}

    for results, ranks in (
        (dense_results, dense_ranks),
        (lexical_results, lexical_ranks),
    ):
        for rank, row in enumerate(results, start=1):
            chunk_id = row["id"]
            ranks[chunk_id] = rank
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (60 + rank)
            rows_by_id.setdefault(chunk_id, row)

    ranked_ids = sorted(
        scores,
        key=lambda chunk_id: (
            -scores[chunk_id],
            dense_ranks.get(chunk_id, float("inf")),
            lexical_ranks.get(chunk_id, float("inf")),
        ),
    )[:limit]
    selected = [rows_by_id[chunk_id] for chunk_id in ranked_ids]

    return {
        "ids": [[row["id"] for row in selected]],
        "documents": [[row["document"] for row in selected]],
        "metadatas": [[row["metadata"] for row in selected]],
        "distances": [[row["distance"] for row in selected]],
    }


def semantic_search(
    query: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
    document_id: int | None = None,
):
    empty_results = _empty_results()

    if n_results < 1:
        raise ValueError("n_results must be greater than zero")

    # Authentication is still required.
    if user_id is None:
        return empty_results

    # All authenticated users can search across all shared documents.
    allowed_document_ids = get_all_document_ids()
    if not allowed_document_ids:
        return empty_results

    is_global_search = document_id is None and filename is None

    # Preserve the existing single-document filter behavior.
    if document_id is not None:
        if document_id not in allowed_document_ids:
            return empty_results
        allowed_document_ids = [document_id]

    elif filename:
        resolved_id = get_document_id_by_filename(filename)
        if resolved_id is None or resolved_id not in allowed_document_ids:
            return empty_results
        allowed_document_ids = [resolved_id]

    query_embedding = generate_embedding(query)

    candidate_k = max(n_results * 4, 20)
    dense_results = search_chunks(
        query_embedding=query_embedding,
        n_results=candidate_k,
        allowed_document_ids=allowed_document_ids,
    )
    dense_rows = []
    for chunk_id, document, metadata, distance in zip(
        (dense_results.get("ids") or [[]])[0],
        (dense_results.get("documents") or [[]])[0],
        (dense_results.get("metadatas") or [[]])[0],
        (dense_results.get("distances") or [[]])[0],
    ):
        dense_rows.append(
            {
                "id": chunk_id,
                "document": document or "",
                "metadata": metadata or {},
                "distance": distance,
            }
        )

    lexical_rows = _lexical_search(
        query=query,
        allowed_document_ids=allowed_document_ids,
        limit=candidate_k,
    )
    results = _reciprocal_rank_fusion(
        dense_rows,
        lexical_rows,
        limit=candidate_k,
    )

    if is_global_search:
        return _diversify_global_results(results, n_results)

    return {
        "ids": [results["ids"][0][:n_results]],
        "documents": [results["documents"][0][:n_results]],
        "metadatas": [results["metadatas"][0][:n_results]],
        "distances": [results["distances"][0][:n_results]],
    }
