from rag_service import retrieve_context


query = "What programming languages are mentioned in the document?"

context = retrieve_context(query, n_results=3)

print("\n===== RETRIEVED CONTEXT =====\n")
print(context)