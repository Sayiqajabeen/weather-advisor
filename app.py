import streamlit as st

from src.weather import get_weather
from src.advisor import get_advice

st.set_page_config(page_title="AI Weather Advisor", page_icon="🌦️", layout="centered")

st.title("🌦️ AI Weather Advisor")



@st.cache_data(ttl=600, show_spinner=False)
def cached_weather(city: str) -> dict:
    """Cache weather for 10 minutes so the page does not call the API on every rerun."""
    return get_weather(city)


# ---------- Sidebar ----------
clicked_example = None

with st.sidebar:
    st.header("Location")
    city = st.text_input("Enter city", value="Lahore").strip()

    st.markdown("---")
    st.subheader("Try asking")
    examples = [
        "Is this weather suitable for traveling?",
        "Is this weather suitable for outdoor activities?",
        "What should I wear today?",
        "Can I spray pesticide on my crops today?",
        "What precautions should I take in this weather?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            clicked_example = ex

    st.markdown("---")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---------- Current weather ----------
if not city:
    st.info("Enter a city name in the sidebar to get started.")
    st.stop()

try:
    w = cached_weather(city)
except ValueError as e:
    st.error(str(e))
    st.stop()

st.subheader(f"Current weather in {w['city']}, {w['country']}")
st.write(f"**{w['description'].title()}** (feels like {w['feels_like']:.1f} °C)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temperature", f"{w['temperature']:.1f} °C")
c2.metric("Humidity", f"{w['humidity']} %")
c3.metric("Wind", f"{w['wind_speed']} m/s")
c4.metric("Rain (1h)", f"{w['rain_1h']} mm")

st.markdown("---")

# ---------- Chat ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))


def handle_question(question: str):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Checking weather and guidelines..."):
            try:
                result = get_advice(city, question, weather=w)
                answer, sources = result["answer"], result["sources"]
            except Exception as e:
                answer, sources = f"Sorry, something went wrong: {e}", []
        st.markdown(answer)
        if sources:
            st.caption("Sources: " + ", ".join(sources))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )


question = st.chat_input("Ask a weather question...")
if clicked_example:
    question = clicked_example

if question:
    handle_question(question)
