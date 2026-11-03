
from rank_bm25 import BM25Okapi
from chroma_service import collection
from search_service import semantic_search
import re

USER_ID = 1
TOP_K = 5
RRF_K = 60

TEST_CASES = [
    {
        "question": "What is the SGPA for PUC-2 SEM-1?",
        "document_id": 6,
        "relevant_chunk_ids": ["7"],
    },
    {
        "question": "What is the pre-university course CGPA?",
        "document_id": 10,
        "relevant_chunk_ids": ["14"],
    },
    {
        "question": "Which machine learning algorithms are mentioned?",
        "document_id": 10,
        "relevant_chunk_ids": ["15", "16"],
    },
    {
        "question": "What is the BTech CGPA?",
        "document_id": 12,
        "relevant_chunk_ids": ["21"],
    },
    {
        "question": "Which programming languages are mentioned?",
        "document_id": 12,
        "relevant_chunk_ids": ["21", "22"],
    },
]


def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


def get_dense_results(query, document_id):
    results = semantic_search(
        query=query,
        n_results=TOP_K,
        user_id=USER_ID,
        document_id=document_id,
    )

    return results["ids"][0]


def get_bm25_results(query, document_id):
    data = collection.get(
        where={"document_id": document_id},
        include=["documents"],
    )

    chunk_ids = data["ids"]
    documents = data["documents"]

    if not chunk_ids:
        return []

    tokenized_corpus = [
        tokenize(document) for document in documents
    ]

    bm25 = BM25Okapi(tokenized_corpus)

    scores = bm25.get_scores(tokenize(query))

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )

    return [
        chunk_ids[i]
        for i in ranked_indices[:TOP_K]
    ]


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

    return [
        chunk_id
        for chunk_id, score in sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                bm25_ranks.get(item[0], float("inf")),
            ),
        )[:TOP_K]
    ]


def calculate_metrics(retrieved_ids, relevant_ids):
    relevant_ids = set(relevant_ids)

    relevant_retrieved = [
        chunk_id
        for chunk_id in retrieved_ids
        if chunk_id in relevant_ids
    ]

    precision = len(relevant_retrieved) / TOP_K

    recall = (
        len(relevant_retrieved) / len(relevant_ids)
        if relevant_ids else 0
    )

    hit_rate = 1 if relevant_retrieved else 0

    reciprocal_rank = 0

    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            reciprocal_rank = 1 / rank
            break

    return {
        "precision": precision,
        "recall": recall,
        "hit_rate": hit_rate,
        "mrr": reciprocal_rank,
    }


def evaluate_method(method_name, test_cases):
    totals = {
        "precision": 0,
        "recall": 0,
        "hit_rate": 0,
        "mrr": 0,
    }

    print(f"\n========== {method_name} ==========\n")

    for index, test_case in enumerate(test_cases, start=1):

        query = test_case["question"]
        document_id = test_case["document_id"]
        relevant_ids = test_case["relevant_chunk_ids"]

        if method_name == "DENSE":
            retrieved_ids = get_dense_results(
                query, document_id
            )

        elif method_name == "BM25":
            retrieved_ids = get_bm25_results(
                query, document_id
            )

        else:
            dense_ids = get_dense_results(
                query, document_id
            )

            bm25_ids = get_bm25_results(
                query, document_id
            )

            retrieved_ids = reciprocal_rank_fusion(
                dense_ids, bm25_ids
            )

        metrics = calculate_metrics(
            retrieved_ids,
            relevant_ids,
        )

        print(f"Test {index}: {query}")
        print("Retrieved:", retrieved_ids)
        print("Relevant:", relevant_ids)
        print(f"Precision@{TOP_K}: {metrics['precision']:.2f}")
        print(f"Recall@{TOP_K}: {metrics['recall']:.2f}")
        print(f"Hit Rate@{TOP_K}: {metrics['hit_rate']}")
        print(f"MRR: {metrics['mrr']:.2f}")
        print("-" * 45)

        for metric in totals:
            totals[metric] += metrics[metric]

    count = len(test_cases)

    averages = {
        metric: value / count
        for metric, value in totals.items()
    }

    return averages


def main():

    dense = evaluate_method("DENSE", TEST_CASES)
    bm25 = evaluate_method("BM25", TEST_CASES)
    hybrid = evaluate_method("HYBRID RRF", TEST_CASES)

    print("\n========== FINAL COMPARISON ==========\n")

    print(
        f"{'Metric':<18}"
        f"{'Dense':<12}"
        f"{'BM25':<12}"
        f"{'Hybrid':<12}"
    )

    print("-" * 54)

    for metric in ["precision", "recall", "hit_rate", "mrr"]:
        print(
            f"{metric:<18}"
            f"{dense[metric]:<12.2f}"
            f"{bm25[metric]:<12.2f}"
            f"{hybrid[metric]:<12.2f}"
        )


if __name__ == "__main__":
    main()
