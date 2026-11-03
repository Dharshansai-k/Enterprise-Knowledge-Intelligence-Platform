
from embedding_service import generate_embedding
from chroma_service import search_chunks
from document_service import (
    get_user_document_ids,
    get_user_document_id_by_filename,
)


def semantic_search(
    query: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
    document_id: int | None = None,
):
    empty_results = {
        "documents": [[]],
        "metadatas": [[]],
        "ids": [[]],
        "distances": [[]],
    }

    if user_id is None:
        return empty_results

    allowed_document_ids = get_user_document_ids(user_id)
    if not allowed_document_ids:
        return empty_results

    # A specific document ID takes precedence over filename.
    if document_id is not None:
        if document_id not in allowed_document_ids:
            return empty_results

        allowed_document_ids = [document_id]

    elif filename:
        resolved_id = get_user_document_id_by_filename(
            user_id=user_id,
            filename=filename,
        )

        if resolved_id is None:
            return empty_results

        allowed_document_ids = [resolved_id]

    
    query_embedding = generate_embedding(query)

    return search_chunks(
        query_embedding=query_embedding,
        n_results=n_results,
        allowed_document_ids=allowed_document_ids,
    )
