import ollama


MODEL_NAME = "llama3.2"


def generate_answer(question: str, context: str) -> str:

    prompt = f"""
You are EKIP, an enterprise knowledge assistant.

Answer the user's question using ONLY the information provided
in the context below.

If the answer cannot be found in the context, say:
"I couldn't find that information in the provided documents."

Do not invent or assume information.

Context:
{context}

User Question:
{question}

Provide a clear and concise answer.
"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]