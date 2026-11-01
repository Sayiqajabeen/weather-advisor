import time

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.config import GROQ_API_KEY, GROQ_MODEL
from src.weather import get_weather, format_weather, get_forecast, format_forecast
from src.retriever import retrieve_relevant, format_context

MAX_HISTORY = 8        # how many previous messages (user + assistant) the LLM can see
FORECAST_TTL = 600     # cache a city's forecast for 10 minutes

SYSTEM_PROMPT = """You are a helpful Weather Advisor assistant.

You are given:
1. CURRENT WEATHER: live data for one specific city (the Location line tells you which).
2. FORECAST: a day-by-day forecast for the same city for the next few days.
3. KNOWLEDGE BASE: guideline excerpts retrieved for the user's question.
4. The earlier conversation, so you can remember what the user told you.

Rules:
- For questions about right now or today, use CURRENT WEATHER.
- For questions about tomorrow, a weekday (like Wednesday), or the coming days, use the FORECAST. Match the day using the weekday and date written on each forecast line; the first line tells you what today is.
- The forecast covers only the next 5 days or so. If the user asks about a day beyond it, say that the forecast is not available that far ahead.
- Present forecast values as expected or forecast values, not as certain facts.
- Base advice on the weather data and the knowledge base excerpts. Compare the numbers (temperature, humidity, wind, rain) with the thresholds in the guidelines.
- When giving weather advice, mention the city name it is for.
- Give practical, specific advice. Keep the answer short and easy to read (use short bullet points when helpful).
- For weather questions, start with a one-line verdict or direct answer.
- If the user shares personal details (like their name) or asks about something said earlier in the conversation, answer from the conversation history. Do not give weather advice for such messages.
- If the knowledge base does not cover something, say so honestly instead of making things up.
- Never invent weather numbers. Use only the data provided.
- For health emergencies, remind the user to contact local emergency services.
- Reply in the same language as the user's question."""

HUMAN_PROMPT = """CURRENT WEATHER:
{weather}

FORECAST:
{forecast}

KNOWLEDGE BASE:
{context}

USER QUESTION:
{question}"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", HUMAN_PROMPT),
    ]
)

EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract a city name from a user's message. "
            "Reply with ONLY the city name in English letters (for example: Beijing, Hafizabad, Karachi). "
            "The message may be in English, Urdu or Roman Urdu. "
            "If the message does not mention any city, reply with exactly: NONE",
        ),
        ("human", "{question}"),
    ]
)

_llm = None
_extractor = None
_forecast_cache: dict[str, tuple[float, str]] = {}


def get_llm():
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing. Check your .env file.")
        _llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.3)
    return _llm


def get_extractor_llm():
    """A separate LLM with temperature 0 so city extraction is consistent."""
    global _extractor
    if _extractor is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing. Check your .env file.")
        _extractor = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)
    return _extractor


def extract_city(question: str) -> str | None:
    """Return the city mentioned in the question, or None if there is no city."""
    try:
        response = (EXTRACT_PROMPT | get_extractor_llm()).invoke({"question": question})
    except Exception:
        return None  # if extraction fails, fall back to the sidebar city

    text = (response.content or "").strip().strip(".\"'` ")
    if not text or text.upper() == "NONE" or len(text) > 40 or "\n" in text:
        return None
    return text


def get_forecast_text(city: str) -> str:
    """Forecast as plain text, cached for a few minutes. Never raises."""
    key = city.strip().lower()
    now = time.time()

    cached = _forecast_cache.get(key)
    if cached and now - cached[0] < FORECAST_TTL:
        return cached[1]

    try:
        text = format_forecast(get_forecast(city))
    except ValueError:
        return "Forecast data is not available right now."

    _forecast_cache[key] = (now, text)
    return text


def build_history(history: list[dict] | None) -> list[tuple[str, str]]:
    """Turn the UI messages into (role, text) pairs, keeping only the most recent ones."""
    if not history:
        return []
    pairs = []
    for m in history[-MAX_HISTORY:]:
        role = "human" if m["role"] == "user" else "ai"
        pairs.append((role, m["content"]))
    return pairs


def get_advice(
    city: str,
    question: str,
    weather: dict | None = None,
    history: list[dict] | None = None,
) -> dict:
    """Full RAG pipeline: weather API + forecast + retrieval + LLM (with chat memory).

    `city` is the default (sidebar) city. If the question names another city,
    the weather and forecast for that city are used instead.
    `history` is the earlier chat (list of {"role", "content"}), NOT including the current question.
    """
    # 1. Decide which city to use, then get its live weather and forecast
    asked_city = extract_city(question)
    target_city = asked_city or city

    if weather is None or target_city.strip().lower() != city.strip().lower():
        weather = get_weather(target_city)
    weather_text = format_weather(weather)
    forecast_text = get_forecast_text(target_city)

    # 2. Retrieval: the question first, plus a little weather context
    search_query = (
        f"{question} (weather: {weather['description']}, {weather['temperature']}°C)"
    )
    docs = retrieve_relevant(search_query)
    context = format_context(docs)

    # 3. LLM (with earlier conversation)
    chain = prompt | get_llm()
    try:
        response = chain.invoke(
            {
                "weather": weather_text,
                "forecast": forecast_text,
                "context": context,
                "question": question,
                "history": build_history(history),
            }
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