from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from src.config import GROQ_API_KEY, GROQ_MODEL
from src.weather import get_weather, format_weather
from src.retriever import retrieve_relevant, format_context

SYSTEM_PROMPT = """You are a helpful Weather Advisor assistant.

You are given:
1. CURRENT WEATHER: live data for the user's city.
2. KNOWLEDGE BASE: guideline excerpts retrieved for the user's question.

Rules:
- Base your advice on the current weather data and the knowledge base excerpts.
- Compare the live numbers (temperature, humidity, wind, rain) with the thresholds in the guidelines.
- Give practical, specific advice. Keep the answer short and easy to read (use short bullet points when helpful).
- Start with a one-line verdict (for example: suitable, not suitable, or take precautions).
- If the knowledge base does not cover something, say so honestly instead of making things up.
- Never invent weather numbers. Use only the data provided.
- For health emergencies, remind the user to contact local emergency services.
- Reply in the same language as the user's question."""

HUMAN_PROMPT = """CURRENT WEATHER:
{weather}

KNOWLEDGE BASE:
{context}

USER QUESTION:
{question}"""

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)]
)

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing. Check your .env file.")
        _llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.3)
    return _llm


def get_advice(city: str, question: str, weather: dict | None = None) -> dict:
    """Full RAG pipeline: weather API + retrieval + LLM."""
    # 1. Live weather (reuse it if the UI already fetched it)
    if weather is None:
        weather = get_weather(city)
    weather_text = format_weather(weather)

    # 2. Retrieval: the question first, plus a little weather context
    search_query = (
        f"{question} (weather: {weather['description']}, {weather['temperature']}°C)"
    )
    docs = retrieve_relevant(search_query)
    context = format_context(docs)

    # 3. LLM
    chain = prompt | get_llm()
    try:
        response = chain.invoke(
            {"weather": weather_text, "context": context, "question": question}
        )
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "rate limit" in msg:
            raise ValueError(
                "The AI service is busy (rate limit reached). Please wait a minute and try again."
            )
        raise

    sources = sorted(
        {d.metadata.get("source", "unknown").replace("\\", "/").split("/")[-1] for d in docs}
    )

    return {
        "answer": response.content,
        "weather": weather,
        "sources": sources,
    }