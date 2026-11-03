
import chromadb
from embedding_service import generate_embedding

client = chromadb.PersistentClient(path="../chroma_db")

collection = client.get_collection(
    name="ekip_documents_experimental_v2"
)

TEST_CASES = [
    {
        "question": "What is the BTech CGPA?",
        "relevant_section": "EDUCATION",
    },
    {
        "question": "What is the pre-university course CGPA?",
        "relevant_section": "EDUCATION",
    },
    {
        "question": "Which programming languages are mentioned?",
        "relevant_section": "TECHNICAL SKILLS",
    },
]

TOP_K = 5


def evaluate(query, relevant_section):
    embedding = generate_embedding(query)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        where={"document_id": 12},
        include=["metadatas", "distances"],
    )

    sections = [
        metadata["section"]
        for metadata in results["metadatas"][0]
    ]

    relevant_ranks = [
        rank
        for rank, section in enumerate(sections, start=1)
        if section == relevant_section
    ]

    precision = len(relevant_ranks) / TOP_K
    recall = 1.0 if relevant_ranks else 0.0
    hit_rate = 1 if relevant_ranks else 0
    mrr = 1 / relevant_ranks[0] if relevant_ranks else 0

    return {
        "retrieved_sections": sections,
        "precision": precision,
        "recall": recall,
        "hit_rate": hit_rate,
        "mrr": mrr,
    }


def main():
    totals = {
        "precision": 0,
        "recall": 0,
        "hit_rate": 0,
        "mrr": 0,
    }

    print("\n========== EXPERIMENTAL EVALUATION ==========\n")

    for index, test in enumerate(TEST_CASES, start=1):
        result = evaluate(
            test["question"],
            test["relevant_section"],
        )

        print(f"Test {index}: {test['question']}")
        print("Retrieved sections:", result["retrieved_sections"])
        print("Expected section:", test["relevant_section"])
        print(f"Precision@5: {result['precision']:.2f}")
        print(f"Recall@5: {result['recall']:.2f}")
        print(f"Hit Rate@5: {result['hit_rate']}")
        print(f"MRR: {result['mrr']:.2f}")
        print("-" * 45)

        for metric in totals:
            totals[metric] += result[metric]

    print("\n========== OVERALL RESULTS ==========\n")

    for metric, value in totals.items():
        print(f"Mean {metric}: {value / len(TEST_CASES):.2f}")


if __name__ == "__main__":
    main()
