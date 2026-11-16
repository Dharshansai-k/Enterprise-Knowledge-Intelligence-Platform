from collections import OrderedDict
from search_service import semantic_search
from llm_service import (
    generate_answer,
    contextualize_question,
    generate_follow_up_questions,
)


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

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    context_parts = []
    sources = []

    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        metadata = metadata or {}
        filename_value = metadata.get("filename", "Unknown")
        chunk_index = metadata.get("chunk_index", "Unknown")
        source_document_id = metadata.get("document_id", "Unknown")

        source_number = len(sources) + 1
        context_parts.append(
            f"[Source {source_number}]\n"
            f"Filename: {filename_value}\n"
            f"Document ID: {source_document_id}\n"
            f"Chunk: {chunk_index}\n"
            f"Content:\n{document}"
        )

        source = {
            "source_number": source_number,
            "filename": filename_value,
            "chunk_index": chunk_index,
            "document_id": source_document_id,
            "distance": float(distance) if distance is not None else None,
        }
        sources.append(source)

    return (
        "\n\n".join(context_parts),
        sources,
    )




def ask_question(
    question: str,
    n_results: int = 3,
    user_id: int | None = None,
    filename: str | None = None,
    document_id: int | None = None,
    conversation_history: list | None = None,
):
    conversation_history = conversation_history or []

    # The frontend saves the current user question before calling /ask.
    # Exclude that question from history to avoid sending it twice.
    history_for_context = conversation_history

    if (
        history_for_context
        and history_for_context[-1].get("role") == "user"
        and history_for_context[-1].get("content", "").strip() == question.strip()
    ):
        history_for_context = history_for_context[:-1]

    # Rewrite follow-up questions into standalone retrieval queries.
    retrieval_query = contextualize_question(
        question=question,
        conversation_history=history_for_context,
    )

    print("Original question:", question)
    print("Retrieval query:", retrieval_query)

    # Retrieve using the contextualized query.
    context, sources = retrieve_context(
        query=retrieval_query,
        n_results=n_results,
        user_id=user_id,
        filename=filename,
        document_id=document_id,
    )

    grouped_documents = OrderedDict()

    for source in sources:
        key = str(source["document_id"])

        if key not in grouped_documents:
            grouped_documents[key] = {
                "document_id": source["document_id"],
                "filename": source["filename"],
                "chunks": [],
            }

        grouped_documents[key]["chunks"].append(
            source["chunk_index"]
        )

    documents_used = list(grouped_documents.values())

    if not context:
        return {
            "answer": "I couldn't find relevant content in the selected documents.",
            "sources": [],
            "documents_used": [],
            "context": "",
            "has_sufficient_evidence": False,
        }

    # Generate the answer using the original question.
    answer = generate_answer(
        question=question,
        context=context,
        conversation_history=history_for_context,
    )
    suggested_questions = generate_follow_up_questions(
        question=question,
        context=context,
        answer=answer,
    )
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
        phrase in answer_lower
        for phrase in refusal_phrases
    )

    return {
        "answer": answer,
        "sources": sources,
        "documents_used": documents_used,
        "context": context,
        "has_sufficient_evidence": has_sufficient_evidence,
        "suggested_questions": suggested_questions,
    }
