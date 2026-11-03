
from rank_bm25 import BM25Okapi
from chroma_service import collection
from search_service import semantic_search
import re

USER_ID = 1
DOCUMENT_ID = 12
TOP_K = 5
RRF_K = 60

queries = [
    "What is the BTech CGPA?",
    "Bachelor of Technology BTech Computer Science CGPA score",
    "Find the CGPA value specifically for Bachelor of Technology BTech",
]


def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


# Load document chunks for BM25
data = collection.get(
    where={"document_id": DOCUMENT_ID},
    include=["documents"]
)

chunk_ids = data["ids"]
documents = data["documents"]

bm25 = BM25Okapi([
    tokenize(document) for document in documents
])


def reciprocal_rank_fusion(dense_ids, bm25_ids):
    scores = {}
    bm25_ranks = {}

    for rank, chunk_id in enumerate(bm25_ids, start=1):
        bm25_ranks[chunk_id] = rank

    for ranking in [dense_ids, bm25_ids]:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0) + (
                1 / (RRF_K + rank)
            )

    return sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            bm25_ranks.get(item[0], float("inf"))
        )
    )

for query in queries:

    # Dense retrieval
    dense_results = semantic_search(
        query=query,
        n_results=TOP_K,
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
    )

    dense_ids = dense_results["ids"][0]

    # BM25 retrieval
    bm25_scores = bm25.get_scores(tokenize(query))

    bm25_ranking = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )

    bm25_ids = [
        chunk_ids[i]
        for i in bm25_ranking[:TOP_K]
    ]

    # Hybrid retrieval
    hybrid_results = reciprocal_rank_fusion(
        dense_ids,
        bm25_ids
    )

    print("\nQuery:", query)
    print("Dense:", dense_ids)
    print("BM25:", bm25_ids)

    print("Hybrid ranking:")
    for rank, (chunk_id, score) in enumerate(
        hybrid_results[:TOP_K], start=1
    ):
        print(
            f"Rank {rank}: Chunk {chunk_id} "
            f"| RRF Score: {score:.6f}"
        )
