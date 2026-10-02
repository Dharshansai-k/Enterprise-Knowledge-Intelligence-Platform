from embedding_service import generate_embedding
from chroma_service import search_chunks


def semantic_search(query: str, n_results: int = 5):
    query_embedding = generate_embedding(query)

    results = search_chunks(
        query_embedding=query_embedding,
        n_results=n_results,
    )

    return results