
from search_service import semantic_search
from llm_service import generate_answer


def retrieve_context(
    query: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
    document_id: int | None = None,
):
    results = semantic_search(
        query=query,
        n_results=n_results,
        user_id=user_id,
        filename=filename,
        document_id=document_id,
    )
    print("Query:", query)
    print("Retrieved distances:", results.get("distances", [[]])[0])
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    print("\n--- RETRIEVED CHUNKS ---")

    for i, (document, distance) in enumerate(
        zip(documents, distances),
        start=1,
    ):
        print(f"\nChunk {i} | Distance: {distance:.4f}")
        print(document[:700])

    print("--- END CHUNKS ---\n")

    context_parts = []
    sources = []


    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):

        filename_value = metadata.get("filename", "Unknown")
        chunk_index = metadata.get("chunk_index", "Unknown")
        document_id = metadata.get("document_id", "Unknown")

        source_number = len(sources) + 1

        context_parts.append(
            f"[Source {source_number}]\n"
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
    document_id: int | None = None
):
    context, sources = retrieve_context(
        query=question,
        n_results=n_results,
        user_id=user_id,
        filename=filename,
        document_id=document_id,
    )

    if not context:
        return {
            "answer": "I couldn't find relevant content in the selected document.",
            "sources": [],
            "context": "",
            "has_sufficient_evidence": False,
        }

    answer = generate_answer(question=question, context=context)

    answer_lower = answer.lower()

    refusal_phrases = [
        "could not be found",
        "couldn't find",
        "couldn’t find",
        "do not contain any information",
        "does not contain any information",
        "not found in the provided documents",
        "not mentioned in the provided documents",
        "insufficient information",
        "no information about",
        "any information about",
        "information is not available",
    ]

    has_sufficient_evidence = not any(
        phrase in answer_lower for phrase in refusal_phrases
    )

    return {
        "answer": answer,
        "sources": sources,
        "context": context,
        "has_sufficient_evidence": has_sufficient_evidence,
    }