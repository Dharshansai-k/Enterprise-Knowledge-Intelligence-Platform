
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
        "Answer the user's question using ONLY facts explicitly stated "
        "in the supplied document context. "

        "Read all supplied source chunks before answering. "
        "Information relevant to a question may appear across multiple "
        "chunks, so combine those chunks when they clearly refer to "
        "the same fact or subject. "

        "For questions about marks, grades, CGPA, dates, names, or other "
        "specific facts, carefully locate the exact value and its "
        "associated label in the context. Do not confuse values belonging "
        "to different education levels or subjects. "

        "If the context clearly supports the answer, answer directly and "
        "preserve the exact value and its meaning. "

        "If the context does not contain enough evidence to answer, "
        "explicitly state that the information could not be found in the "
        "provided documents. Never guess or invent an answer. "

        "For list questions, include every relevant item supported by "
        "the context. Preserve project names and other names exactly "
        "as written. Do not merge unrelated facts or projects. "

        "Use concise, clear language and bullet points when appropriate."
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
