import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from backend/.env")

client = Groq(api_key=api_key)

MODEL_NAME = "openai/gpt-oss-20b"



def contextualize_question(
    question: str,
    conversation_history: list | None = None
) -> str:
    """
    Convert a follow-up question into a standalone retrieval query.
    Conversation history is used only to resolve references.
    """

    history = conversation_history or []

    if not history:
        return question

    history_text = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in history
        if item.get("role") in {"user", "assistant"}
        and item.get("content")
    )

    if not history_text:
        return question

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You rewrite follow-up questions into standalone "
                    "document retrieval queries. Use conversation history "
                    "only to resolve references such as 'second semester', "
                    "'that subject', or 'the previous one'. "
                    "Preserve the user's intended meaning. Do not answer "
                    "the question, add facts, or invent entities. "
                    "If the question is already standalone, return it "
                    "unchanged. Return only the rewritten question."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Conversation history:\n{history_text}\n\n"
                    f"Current question:\n{question}"
                ),
            },
        ],
        max_completion_tokens=200,
        temperature=0,
        reasoning_effort="low",
    )

    rewritten = (
        response.choices[0].message.content or ""
    ).strip()

    if not rewritten:
        return question

    # Avoid unexpectedly long or malformed retrieval queries.
    if len(rewritten) > 1000:
        return question

    print("\n--- QUERY CONTEXTUALIZATION ---")
    print("Original:", question)
    print("Rewritten:", rewritten)
    print("--- END QUERY CONTEXTUALIZATION ---\n")

    return rewritten



def generate_answer(
    question: str,
    context: str,
    conversation_history: list | None = None
) -> str:

    conversation_history = conversation_history or []

    system_prompt = (
        "You are EKIP, a document-grounded knowledge assistant. "
        "Answer the user's question using ONLY facts explicitly stated "
        "in the supplied document context. "

        "Use conversation history only to understand references, "
        "pronouns, and follow-up questions. Conversation history is "
        "not a source of factual evidence. "

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

        "For each factual claim, cite the supporting context using its "
        "exact label, for example [Source 1] or [Source 2]. "
        "Never cite a source that does not support the claim. "
        "Use concise, clear language and bullet points when appropriate."
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add recent conversation history.
    for item in conversation_history:
        role = item.get("role")
        content = item.get("content", "")

        if role in {"user", "assistant"} and content:
            messages.append({
                "role": role,
                "content": content
            })

    # Current question and retrieved document context.
    user_prompt = (
        f"Document context:\n{context}\n\n"
        f"Current question:\n{question}"
    )

    messages.append({
        "role": "user",
        "content": user_prompt
    })

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_completion_tokens=4096,
        temperature=0.2,
        reasoning_effort="low",
    )

    choice = response.choices[0]
    message = choice.message
    answer = (message.content or "").strip()

    print("\n--- GROQ DEBUG ---")
    print("Model:", MODEL_NAME)
    print("Finish reason:", choice.finish_reason)
    print("Usage:", response.usage)
    print("Answer:", answer)
    print("--- END GROQ DEBUG ---\n")

    if not answer:
        raise RuntimeError(
            "The LLM returned an empty answer. "
            f"Finish reason: {choice.finish_reason}"
        )

    return answer



def generate_follow_up_questions(
    question: str,
    context: str,
    answer: str
) -> list[str]:
    """
    Generate 2-3 follow-up questions grounded in retrieved document context.
    """

    if not context or not context.strip():
        return []

    if not answer or not answer.strip():
        return []

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """
You generate useful follow-up questions for a document question-answering system.

Rules:
- Generate 2 or 3 short, relevant follow-up questions.
- Use ONLY information available in the provided document context.
- Questions must be answerable using the provided context.
- Questions should help the user explore related details.
- Do not repeat the original question.
- Do not assume facts that are not in the context.
- Return valid JSON in exactly this format:
  {"questions": ["Question 1?", "Question 2?"]}
"""
                },
                {
                    "role": "user",
                    "content": f"""
Original question:
{question}

Retrieved document context:
{context}

Generated answer:
{answer}

Generate follow-up questions.
"""
                }
            ],
            max_completion_tokens=300,
            temperature=0.3,
            reasoning_effort="low",
        )

        content = response.choices[0].message.content or ""
        content = content.strip()

        # Extract JSON even if the model adds surrounding text.
        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            return []

        data = json.loads(content[start:end + 1])
        questions = data.get("questions", [])

        if not isinstance(questions, list):
            return []

        # Validate and limit the suggestions.
        cleaned_questions = []

        for item in questions:
            if isinstance(item, str):
                item = item.strip()

                if (
                    item
                    and item.lower() != question.strip().lower()
                    and item not in cleaned_questions
                ):
                    cleaned_questions.append(item)

            if len(cleaned_questions) == 3:
                break

        return cleaned_questions

    except Exception as e:
        print(f"Follow-up question generation failed: {e}")
        return []
