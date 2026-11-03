
from search_service import semantic_search

USER_ID = 1
TOP_K = 5

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
        "question": "Bachelor of Technology BTech Computer Science CGPA score",
        "document_id": 12,
        "relevant_chunk_ids": ["21"],
    },
    {
        "question": "Which programming languages are mentioned?",
        "document_id": 12,
        "relevant_chunk_ids": ["21", "22"],
    },
]


def evaluate_case(test_case):
    results = semantic_search(
        query=test_case["question"],
        n_results=TOP_K,
        user_id=USER_ID,
        document_id=test_case["document_id"],
    )

    retrieved_ids = results["ids"][0]
    relevant_ids = set(test_case["relevant_chunk_ids"])

    relevant_retrieved = [
        chunk_id for chunk_id in retrieved_ids
        if chunk_id in relevant_ids
    ]

    # Precision@K: relevant results / requested K
    precision = len(relevant_retrieved) / TOP_K

    # Recall@K: relevant results found / total relevant results
    recall = len(relevant_retrieved) / len(relevant_ids)

    # Hit Rate@K
    hit_rate = 1 if relevant_retrieved else 0

    # Mean Reciprocal Rank
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
        "retrieved_ids": retrieved_ids,
        "relevant_retrieved": relevant_retrieved,
        "distances": results["distances"][0],
    }


def main():
    totals = {
        "precision": 0,
        "recall": 0,
        "hit_rate": 0,
        "mrr": 0,
    }

    print("\n========== RETRIEVAL EVALUATION ==========\n")

    for index, test_case in enumerate(TEST_CASES, start=1):
        result = evaluate_case(test_case)

        print(f"Test {index}: {test_case['question']}")
        print(f"Retrieved IDs: {result['retrieved_ids']}")
        print(f"Distances: {result['distances']}")
        print(f"Relevant IDs: {result['relevant_retrieved']}")
        print(f"Precision@{TOP_K}: {result['precision']:.2f}")
        print(f"Recall@{TOP_K}: {result['recall']:.2f}")
        print(f"Hit Rate@{TOP_K}: {result['hit_rate']}")
        print(f"MRR: {result['mrr']:.2f}")
        print("-" * 45)

        for metric in totals:
            totals[metric] += result[metric]

    count = len(TEST_CASES)

    print("\n========== OVERALL RESULTS ==========\n")
    print(f"Mean Precision@{TOP_K}: {totals['precision'] / count:.2f}")
    print(f"Mean Recall@{TOP_K}: {totals['recall'] / count:.2f}")
    print(f"Hit Rate@{TOP_K}: {totals['hit_rate'] / count:.2f}")
    print(f"MRR: {totals['mrr'] / count:.2f}")
    print("\n========== QUERY VARIANT EXPERIMENT ==========\n")

    QUERY_VARIANTS = [
        "What is the BTech CGPA?",
        "Bachelor of Technology BTech Computer Science CGPA score",
        "Find the CGPA value specifically for Bachelor of Technology (B.Tech).",
    ]

    for query in QUERY_VARIANTS:
        results = semantic_search(
            query=query,
            n_results=TOP_K,
            user_id=USER_ID,
            document_id=12,
        )

        print("\nQuery:", query)
        print("Retrieved IDs:", results["ids"][0])
        print("Distances:", results["distances"][0])




if __name__ == "__main__":
    main()
