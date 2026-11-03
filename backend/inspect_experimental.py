import chromadb

client = chromadb.PersistentClient(path="../chroma_db")

collection = client.get_collection(
    name="ekip_documents_experimental_all_v3"
)

for document_id in [5, 6, 10, 12]:

    print("\n" + "=" * 70)
    print(f"DOCUMENT ID: {document_id}")
    print("=" * 70)

    results = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )

    for content, metadata in zip(
        results["documents"],
        results["metadatas"],
    ):
        print(
            f"\nChunk {metadata['chunk_index']} "
            f"| Section: {metadata['section']}"
        )
        print("-" * 50)
        print(content)