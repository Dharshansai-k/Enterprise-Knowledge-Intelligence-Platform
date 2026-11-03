
from embedding_service import generate_embedding
from chroma_service import collection
import numpy as np

query = "What is the BTech CGPA?"

chunk_ids = ["21", "22", "23"]

data = collection.get(
    ids=chunk_ids,
    include=["documents", "embeddings"]
)

query_embedding = np.array(generate_embedding(query))

for chunk_id, document, embedding in zip(
    data["ids"],
    data["documents"],
    data["embeddings"]
):
    chunk_embedding = np.array(embedding)

    cosine_similarity = np.dot(
        query_embedding, chunk_embedding
    ) / (
        np.linalg.norm(query_embedding)
        * np.linalg.norm(chunk_embedding)
    )

    print("\nChunk:", chunk_id)
    print("Cosine similarity:", round(float(cosine_similarity), 4))
    print("Contains BTech CGPA:", "B.Tech" in document and "CGPA" in document)
