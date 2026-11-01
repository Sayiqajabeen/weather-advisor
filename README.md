# 🌦️ AI Weather Advisor

A RAG-powered weather chatbot that combines **live weather data** with a **knowledge base of safety and lifestyle guidelines** to give practical, context-aware advice.

🔗 **Live demo:** [https://weather-advisor-habsy7dwqz8qeyfsfdr2uc.streamlit.app/](https://weather-advisor-habsy7dwqz8qeyfsfdr2uc.streamlit.app/)

> Note: The app is hosted on Streamlit Community Cloud's free tier. If it has been idle, it may show a "wake up" button. Click it and wait a minute.

---

## Overview

Standard weather apps show raw numbers (temperature, humidity, wind) and leave the interpretation to you. AI Weather Advisor goes one step further: you enter a city, ask a question in plain language, and it answers using both the current weather and relevant guidelines retrieved from a knowledge base.

**Example questions**
- "Is this weather suitable for traveling?"
- "What precautions should I take in this weather?"
- "What should I wear today?"
- "Can I spray pesticide on my crops today?"
- "Is this weather suitable for outdoor activities?"

## Features

- **Current weather** for any city (temperature, humidity, wind, rain, conditions)
- **RAG knowledge base** covering heatwaves, floods and rain, farming, travel, clothing, and outdoor activities
- **Conversational chatbot** with chat history
- **Context-aware recommendations** that compare live data against guideline thresholds
- **Relevance filtering** so only useful knowledge chunks reach the LLM
- **Source display** showing which knowledge base files were used
- **Multilingual replies** (the model answers in the language of the question)
- **Friendly error handling** for invalid cities, API issues, and rate limits

## How it works

```
User question + city
        │
        ├──► OpenWeatherMap API ──► live weather data
        │
        ├──► FAISS vector search ──► relevant guideline chunks
        │
        ▼
   Prompt (weather + guidelines + question)
        │
        ▼
      LLM (Groq)
        │
        ▼
 Context-aware advice + sources
```

## Tech stack

| Component | Technology |
|---|---|
| UI and app logic | Streamlit |
| RAG framework | LangChain |
| Vector store | FAISS |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (runs locally) |
| LLM | Groq API |
| Weather data | OpenWeatherMap API |
| Deployment | Streamlit Community Cloud |

## Project structure

```
weather-advisor/
├── app.py                  # Streamlit UI
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit settings
├── data/
│   └── knowledge_base/     # RAG documents (.md)
│       ├── heatwave.md
│       ├── floods_rain.md
│       ├── farming.md
│       ├── travel.md
│       ├── clothing.md
│       └── outdoor_activities.md
└── src/
    ├── config.py           # Loads API keys and settings
    ├── weather.py          # OpenWeatherMap API calls
    ├── ingest.py           # Loads docs, chunks them, builds the FAISS index
    ├── retriever.py        # Loads the index and retrieves relevant chunks
    └── advisor.py          # Combines weather + retrieved docs and calls the LLM
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
```

Get free keys here:
- OpenWeatherMap: https://openweathermap.org/api
- Groq: https://console.groq.com/keys

**5. Run the app**

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The first run downloads the embedding model and builds the index, so it may take a minute.

## Deployment

The app is deployed on **Streamlit Community Cloud** directly from this GitHub repository. API keys are stored in the app's **Secrets** settings (never committed to the repo):

```toml
OPENWEATHER_API_KEY = "your_openweathermap_key"
GROQ_API_KEY = "your_groq_key"
```

## Limitations

- The knowledge base contains general guidelines and is **not official medical or government advice**. For emergencies, contact local emergency services.
- Weather data comes from the OpenWeatherMap free tier (current conditions only, no long-range forecast).
- The free LLM tier has rate limits, so heavy use may temporarily return a "busy" message.

## Future improvements

- Add multi-day forecast support
- Expand the knowledge base with local advisories (for example PMD and NDMA)
- Add air quality data
- Add a chat export feature

## Author

**Sayiqa**
GitHub: [@Sayiqajabeen](https://github.com/Sayiqajabeen)
