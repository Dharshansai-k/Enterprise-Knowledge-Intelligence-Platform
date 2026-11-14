from collections import OrderedDict

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
):
    context, sources = retrieve_context(
        query=question,
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
        grouped_documents[key]["chunks"].append(source["chunk_index"])
    documents_used = list(grouped_documents.values())

    if not context:
        return {
            "answer": "I couldn't find relevant content in the selected documents.",
            "sources": [],
            "documents_used": [],
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
        "documents_used": documents_used,
        "context": context,
        "has_sufficient_evidence": has_sufficient_evidence,
    }
