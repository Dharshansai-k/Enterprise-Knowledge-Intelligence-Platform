
import chromadb
from embedding_service import generate_embedding

client = chromadb.PersistentClient(path="../chroma_db")

collections = {
    "LIVE": client.get_collection("ekip_documents"),
    "STAGING": client.get_collection("ekip_documents_staging_v1"),
}

# Questions grounded in the documents' known content.
tests = [
    {
        "question": "What is the SGPA mentioned in P2.pdf?",
        "document_id": 6,
    },
    {
        "question": "What information is provided about Elementary Biology?",
        "document_id": 6,
    },
    {
        "question": "What is the pre-university course CGPA?",
        "document_id": 12,
    },
]

for test in tests:
    question = test["question"]
    document_id = test["document_id"]
    embedding = generate_embedding(question)

    print("\n" + "=" * 80)
    print("QUESTION:", question)
    print("DOCUMENT ID:", document_id)

    for label, collection in collections.items():
        print(f"\n--- {label} ---")

        result = collection.query(
            query_embeddings=[embedding],
            n_results=3,
            where={"document_id": document_id},
            include=["documents", "metadatas", "distances"],
        )

        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        if not documents:
            print("No results.")
            continue

        for rank, (text, metadata, distance) in enumerate(
            zip(documents, metadatas, distances), start=1
        ):
            print(
                f"\nRank {rank} | Distance: {distance:.4f} | "
                f"Document ID: {metadata.get('document_id')} | "
                f"Filename: {metadata.get('filename')} | "
                f"Chunk: {metadata.get('chunk_index')}"
            )
            print(text[:500].replace("\n", " "))
