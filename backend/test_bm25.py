
from rank_bm25 import BM25Okapi
from chroma_service import collection
import re

# Fetch chunks belonging to document 12
data = collection.get(
    where={"document_id": 12},
    include=["documents", "metadatas"]
)

chunk_ids = data["ids"]
documents = data["documents"]


def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


# Prepare corpus for BM25
tokenized_corpus = [
    tokenize(document) for document in documents
]

bm25 = BM25Okapi(tokenized_corpus)

queries = [
    "What is the BTech CGPA?",
    "Bachelor of Technology BTech Computer Science CGPA score",
    "Find the CGPA value specifically for Bachelor of Technology BTech",
]

for query in queries:
    tokenized_query = tokenize(query)

    scores = bm25.get_scores(tokenized_query)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    print("\nQuery:", query)
    print("BM25 ranking:")

    for rank, index in enumerate(ranked_indices, start=1):
        print(
            f"Rank {rank}: Chunk {chunk_ids[index]} "
            f"| Score: {scores[index]:.4f}"
        )
