from search_service import semantic_search
from llm_service import generate_answer


def retrieve_context(query: str, n_results: int = 5):

    results = semantic_search(query, n_results)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    context_parts = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):
        context_parts.append(
            f"[Source {i}]\n"
            f"Filename: {metadata.get('filename')}\n"
            f"Chunk: {metadata.get('chunk_index')}\n"
            f"Content:\n{document}"
        )

    return "\n\n".join(context_parts)


def ask_question(question: str, n_results: int = 5):

    context = retrieve_context(question, n_results)

    answer = generate_answer(
        question=question,
        context=context,
    )

    return {
        "answer": answer,
        "context": context,
    }