
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from backend/.env")

client = Groq(api_key=api_key)

MODEL_NAME = "openai/gpt-oss-20b"



def generate_answer(question: str, context: str) -> str:
    
    system_prompt = (
        "You are EKIP, a document-grounded knowledge assistant. "
        "Use ONLY facts explicitly stated in the supplied context. "
        "Do not infer features, add explanations, or invent details. "
        "Preserve project names exactly as written in the document. "
        "Do not merge projects or treat a section heading as a separate "
        "project unless the document clearly identifies it as one. "
        "For list questions, include every relevant item supported by "
        "the context. Summarize faithfully without changing the meaning. "
        "If a description is incomplete in the context, state only the "
        "available information. Use concise bullet points."
    )


    user_prompt = (
        f"Document context:\n{context}\n\n"
        f"Question:\n{question}"
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=2048,
        temperature=0.2,
    )

    message = response.choices[0].message
    answer = (message.content or "").strip()

    if not answer:
        raise RuntimeError(
            "The LLM returned an empty answer. "
            f"Finish reason: {response.choices[0].finish_reason}"
        )

    return answer
