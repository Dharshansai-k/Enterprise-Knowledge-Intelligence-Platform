import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL_NAME = os.getenv("LLM_MODEL")


def generate_answer(question: str, context: str) -> str:

    prompt = f"""
You are EKIP, an enterprise knowledge assistant.

Answer the user's question using ONLY the provided context.

If the answer cannot be found in the context, say:
"I couldn't find that information in the provided documents."

Do not invent information.

Context:
{context}

User Question:
{question}
"""

    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
    )

    return response.output_text