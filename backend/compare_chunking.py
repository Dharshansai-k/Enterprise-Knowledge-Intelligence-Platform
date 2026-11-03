
import chromadb

from embedding_service import generate_embedding
from chroma_service import collection as live_collection

CHROMA_PATH = "../chroma_db"
EXPERIMENTAL_NAME = "ekip_documents_experimental_v2"

client = chromadb.PersistentClient(path=CHROMA_PATH)

experimental_collection = client.get_collection(
    name=EXPERIMENTAL_NAME
)

DOCUMENT_ID = 12
TOP_K = 5

QUERIES = [
    "What is the BTech CGPA?",
    "What is the pre-university course CGPA?",
    "Which programming languages are mentioned?",
]


def search_collection(target_collection, query):
    embedding = generate_embedding(query)

    results = target_collection.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        where={"document_id": DOCUMENT_ID},
        include=["documents", "metadatas", "distances"],
    )

    return results


def display_results(label, results):
    print(f"\n{label}")

    for rank, (chunk_id, metadata, distance) in enumerate(
        zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        ),
        start=1,
    ):
        print(
            f"Rank {rank}: ID={chunk_id} | "
            f"Section={metadata.get('section', 'N/A')} | "
            f"Distance={distance:.4f}"
        )


def main():
    print("========== CHUNKING COMPARISON ==========")

    for query in QUERIES:
        print("\n" + "=" * 60)
        print("QUERY:", query)

        live_results = search_collection(
            live_collection, query
        )

        experimental_results = search_collection(
            experimental_collection, query
        )

        display_results("ORIGINAL CHUNKING", live_results)
        display_results("EXPERIMENTAL CHUNKING", experimental_results)


if __name__ == "__main__":
    main()
