# 🌦️ AI Weather Advisor

A RAG-powered weather chatbot that combines **live weather and forecast data** with a **knowledge base of safety and lifestyle guidelines** to give practical, context-aware advice. Users log in, and their chat history is saved per account.

🔗 **Live demo:** [https://weather-advisor-habsy7dwqz8qeyfsfdr2uc.streamlit.app/](https://weather-advisor-habsy7dwqz8qeyfsfdr2uc.streamlit.app/)

> Note: The app is hosted on Streamlit Community Cloud's free tier. If it has been idle, it may show a "wake up" button. Click it and wait a minute.

---

## Overview

Standard weather apps show raw numbers (temperature, humidity, wind) and leave the interpretation to you. AI Weather Advisor goes one step further: you ask a question in plain language, and it answers using the live weather (or forecast) for the city you mention, plus relevant guidelines retrieved from a knowledge base.

**Example questions**
- "Is this weather suitable for traveling?"
- "What should I wear today?"
- "Will it rain tomorrow?"
- "What will be the temperature in Karachi on Wednesday?"
- "Can I spray pesticide on my crops today?"
- "Hafizabad ka mausam kaisa hai?" (Roman Urdu works too)

## Features

- **Any city, worldwide:** name a city in your question, or set a default city in the sidebar
- **Current weather and 5-day forecast** (temperature, humidity, wind, rain)
- **RAG knowledge base** covering heatwaves, floods and rain, farming, travel, clothing, and outdoor activities
- **Conversational chatbot with memory:** it remembers what you told it earlier in the chat
- **User accounts:** sign up and log in with a username and password
- **Persistent chat history:** saved per user in a cloud database, so your chat is still there next time you log in
- **Multilingual replies:** the model answers in the language of the question
- **Friendly error handling** for invalid cities, wrong logins, and API rate limits

## How it works

```
User question
      │
      ├──► LLM extracts the city (or uses the sidebar city)
      │          ├──► OpenWeatherMap: current weather + 5-day forecast
      │          └──► FAISS vector search: relevant guideline chunks
      │
      ▼
 Prompt (weather + forecast + guidelines + chat history + question)
      │
      ▼
   LLM (Groq)
      │
      ▼
 Answer shown to the user and saved to the database
```

## Tech stack

| Component | Technology |
|---|---|
| UI and app logic | Streamlit |
| RAG framework | LangChain |
| Vector store | FAISS |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (runs locally) |
| LLM | Groq API |
| Weather data | OpenWeatherMap API (free tier) |
| Database | Neon (serverless Postgres) in the cloud, SQLite locally |
| Authentication | Username and password (PBKDF2 salted hashing) |
| Deployment | Streamlit Community Cloud |

## Project structure

```
weather-advisor/
├── app.py                  # Streamlit UI (login, chat, weather)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit settings
├── data/
│   └── knowledge_base/     # RAG documents (.md)
└── src/
    ├── config.py           # Loads API keys and settings
    ├── weather.py          # Current weather and forecast (OpenWeatherMap)
    ├── ingest.py           # Loads docs, chunks them, builds the FAISS index
    ├── retriever.py        # Loads the index and retrieves relevant chunks
    ├── advisor.py          # City detection, RAG pipeline and LLM call
    └── storage.py          # Accounts and chat history (Postgres or SQLite)
```

The FAISS index (`vectorstore/`) is generated automatically on first run, so it is not stored in the repository.

## Run locally

**1. Clone the repository**

```bash
git clone https://github.com/Sayiqajabeen/weather-advisor.git
cd weather-advisor
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Add your API keys**

Create a `.env` file in the project root:

```
OPENWEATHER_API_KEY=your_openweathermap_key
GROQ_API_KEY=your_groq_key
DATABASE_URL="your_neon_postgres_connection_string"
```

`DATABASE_URL` is optional. If it is missing, the app stores accounts and chat in a local SQLite file (`data/chat_history.db`).

Get free keys here:
- OpenWeatherMap: https://openweathermap.org/api
- Groq: https://console.groq.com/keys
- Neon (Postgres): https://neon.com

**5. Run the app**

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The first run downloads the embedding model and builds the index, so it may take a minute.

## Deployment

The app is deployed on **Streamlit Community Cloud** directly from this GitHub repository. Secrets are stored in the app's **Secrets** settings (never committed to the repo):

```toml
OPENWEATHER_API_KEY = "your_openweathermap_key"
GROQ_API_KEY = "your_groq_key"
DATABASE_URL = "your_neon_postgres_connection_string"
```

## Privacy and security

- Passwords are never stored in plain text. They are hashed with a random salt (PBKDF2-SHA256).
- Chat messages are saved in the database as plain text, so please do not share sensitive personal information in the chat.
- This is a learning and portfolio project. Please do not reuse an important password from another website. There is no password reset feature.

## Limitations

- The knowledge base contains general guidelines and is **not official medical or government advice**. For emergencies, contact local emergency services.
- The forecast covers about 5 days, in daily summaries (not exact hours).
- The free LLM tier has rate limits, so heavy use may temporarily return a "busy" message.
- Refreshing the page logs you out, and you need to log in again.

## Future improvements

- "Remember me" login
- Hourly forecast and air quality data
- Expand the knowledge base with local advisories (for example PMD and NDMA)
- Password reset by email

## Author

**Sayiqa**
GitHub: [@Sayiqajabeen](https://github.com/Sayiqajabeen)