from search_service import semantic_search
from llm_service import generate_answer


def retrieve_context(query: str, n_results: int = 5):
    results = semantic_search(query, n_results)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    context_parts = []
    sources = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):
        filename = metadata.get("filename", "Unknown")
        chunk_index = metadata.get("chunk_index", "Unknown")
        document_id = metadata.get("document_id", "Unknown")

        context_parts.append(
            f"[Source {i}]\n"
            f"Filename: {filename}\n"
            f"Chunk: {chunk_index}\n"
            f"Content:\n{document}"
        )

        sources.append({
            "filename": filename,
            "chunk_index": chunk_index,
            "document_id": document_id,
        })

    return "\n\n".join(context_parts), sources


def ask_question(question: str, n_results: int = 5):
    context, sources = retrieve_context(question, n_results)

    answer = generate_answer(
        question=question,
        context=context,
    )

    return {
        "answer": answer,
        "sources": sources,
        "context": context,
    }