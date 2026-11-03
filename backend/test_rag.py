
from rag_service import retrieve_context

USER_ID = 1

query = "What programming languages are mentioned in the document?"

context, sources = retrieve_context(
    query=query,
    n_results=3,
    user_id=USER_ID,
)

print("\n===== RETRIEVED CONTEXT =====\n")
print(context)

print("\n===== SOURCES =====\n")
for source in sources:
    print(source)
