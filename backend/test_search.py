from search_service import semantic_search


query = "What programming languages and technologies are mentioned?"

results = semantic_search(query, n_results=3)

for i, document in enumerate(results["documents"][0]):
    print("\n--- Result", i + 1, "---")
    print(document)

print("\nMetadata:")
for metadata in results["metadatas"][0]:
    print(metadata)