import streamlit as st

from src.weather import get_weather
from src.advisor import get_advice
from src.storage import (
    init_db,
    create_user,
    verify_user,
    load_messages,
    save_message,
    clear_messages,
)

st.set_page_config(page_title="AI Weather Advisor", page_icon="🌦️", layout="centered")

init_db()  # creates the tables on first run

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def log_in(username: str):
    st.session_state.user = username.strip().lower()
    st.session_state.messages = load_messages(st.session_state.user)


def log_out():
    st.session_state.user = None
    st.session_state.messages = []


# ---------- Login / Sign-up screen ----------
if st.session_state.user is None:
    st.title("🌦️ AI Weather Advisor")
    st.caption("Log in to save your chat history.")

    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Log in")
        if login_submit:
            if verify_user(login_user, login_pass):
                log_in(login_user)
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with signup_tab:
        with st.form("signup_form"):
            new_user = st.text_input(
                "Choose a username", help="3 to 20 characters: letters, numbers, underscore"
            )
            new_pass = st.text_input(
                "Choose a password", type="password", help="At least 8 characters"
            )
            new_pass2 = st.text_input("Confirm password", type="password")
            signup_submit = st.form_submit_button("Create account")
        if signup_submit:
            if new_pass != new_pass2:
                st.error("Passwords do not match.")
            else:
                try:
                    create_user(new_user, new_pass)
                    log_in(new_user)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.caption("Tip: do not reuse an important password from another website.")
    st.stop()  # nothing below runs until the user is logged in

# ---------- Main app (logged in) ----------
user = st.session_state.user

st.title("🌦️ AI Weather Advisor")
st.caption("Live weather + RAG knowledge base = practical, context-aware advice")


@st.cache_data(ttl=600, show_spinner=False)
def cached_weather(city: str) -> dict:
    """Cache weather for 10 minutes so the page does not call the API on every rerun."""
    return get_weather(city)


# ---------- Sidebar ----------
clicked_example = None

with st.sidebar:
    st.write(f"Logged in as **{user}**")
    if st.button("Log out"):
        log_out()
        st.rerun()

    st.markdown("---")
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
        clear_messages(user)
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
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def handle_question(question: str):
    history = list(st.session_state.messages)  # earlier chat, without the current question

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Checking weather and guidelines..."):
            try:
                result = get_advice(city, question, weather=w, history=history)
                answer, ok = result["answer"], True
            except ValueError as e:
                answer, ok = str(e), False
            except Exception as e:
                answer, ok = f"Sorry, something went wrong: {e}", False
        st.markdown(answer)

    # Only successful answers are remembered and saved (errors are not)
    if ok:
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.messages.append({"role": "assistant", "content": answer})
        save_message(user, "user", question)
        save_message(user, "assistant", answer)


question = st.chat_input("Ask a weather question...")
if clicked_example:
    question = clicked_example

if question:
    handle_question(question)