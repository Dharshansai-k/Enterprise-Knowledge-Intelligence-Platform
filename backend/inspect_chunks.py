import chromadb

client = chromadb.PersistentClient(path="../chroma_db")

collection = client.get_collection(
    name="ekip_documents"
)

for document_id in [5, 6]:

    print(f"\nDOCUMENT {document_id}")

    results = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )

    for chunk_id, content, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
    ):
        print("\nChunk ID:", chunk_id)
        print("Chunk index:", metadata["chunk_index"])
        print("Content length:", len(content))
        print("Content:\n", content)