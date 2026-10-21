
from search_service import semantic_search
from llm_service import generate_answer


def retrieve_context(
    query: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
):
    results = semantic_search(
        query=query,
        n_results=n_results,
        user_id=user_id,
        filename=filename,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    context_parts = []
    sources = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1,
    ):
        filename_value = metadata.get("filename", "Unknown")
        chunk_index = metadata.get("chunk_index", "Unknown")
        document_id = metadata.get("document_id", "Unknown")

        context_parts.append(
            f"[Source {i}]\n"
            f"Filename: {filename_value}\n"
            f"Chunk: {chunk_index}\n"
            f"Content:\n{document}"
        )

        sources.append({
            "filename": filename_value,
            "chunk_index": chunk_index,
            "document_id": document_id,
        })

    return "\n\n".join(context_parts), sources


def ask_question(
    question: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
):
    context, sources = retrieve_context(
        query=question,
        n_results=n_results,
        user_id=user_id,
        filename=filename,
    )

    if not context:
        return {
            "answer": (
                "I couldn't find relevant content in the selected "
                "document. Please check the document name or try "
                "a different question."
            ),
            "sources": [],
            "context": "",
        }

    answer = generate_answer(
        question=question,
        context=context,
    )

    return {
        "answer": answer,
        "sources": sources,
        "context": context,
    }
