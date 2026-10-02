from rag_service import ask_question


question = "What programming languages are mentioned in the document?"

result = ask_question(question, n_results=3)

print("\n===== ANSWER =====\n")
print(result["answer"])

print("\n===== SOURCES =====\n")
print(result["context"])