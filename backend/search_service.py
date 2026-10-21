
from embedding_service import generate_embedding
from chroma_service import search_chunks
from document_service import get_user_document_ids


def semantic_search(
    query: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
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

    # If a filename is supplied, resolve it only among this user's documents.
    if filename:
        from document_service import get_user_document_id_by_filename

        document_id = get_user_document_id_by_filename(
            user_id=user_id,
            filename=filename,
        )

        if document_id is None:
            return empty_results

        allowed_document_ids = [document_id]

    query_embedding = generate_embedding(query)

    return search_chunks(
        query_embedding=query_embedding,
        n_results=n_results,
        allowed_document_ids=allowed_document_ids,
    )
