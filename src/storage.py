import hashlib
import hmac
import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg

DB_PATH = Path("data/chat_history.db")  # used only when DATABASE_URL is not set
PBKDF2_ITERATIONS = 200_000
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")

# SQLite uses "?" for values, Postgres uses "%s"
PH = "%s" if USE_POSTGRES else "?"

_initialized = False


def _connect():
    """Open a connection to Neon (Postgres) or to the local SQLite file."""
    if USE_POSTGRES:
        return psycopg.connect(DATABASE_URL, connect_timeout=15)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _execute(sql: str, params: tuple = (), fetch: str | None = None):
    """Run one SQL statement. fetch can be None, 'one' or 'all'."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = None
        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _is_duplicate_error(e: Exception) -> bool:
    """True if the error means 'this username already exists'."""
    if isinstance(e, sqlite3.IntegrityError):
        return True
    return USE_POSTGRES and isinstance(e, psycopg.errors.UniqueViolation)


def _clean(user_name: str) -> str:
    """'Sayiqa ' and 'sayiqa' count as the same user."""
    return user_name.strip().lower()


def init_db():
    """Create the tables if they do not exist yet (runs only once per app start)."""
    global _initialized
    if _initialized:
        return

    id_column = "BIGSERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

    _execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _execute(
        f"""
        CREATE TABLE IF NOT EXISTS messages (
            id {id_column},
            user_name TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_name)")
    _initialized = True


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
def _hash_password(password: str, salt: bytes) -> str:
    """Slow, salted hash. The real password is never stored."""
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return digest.hex()


def create_user(username: str, password: str):
    """Create a new account. Raises ValueError with a clear message if something is wrong."""
    name = _clean(username)
    if not USERNAME_RE.match(name):
        raise ValueError(
            "Username must be 3 to 20 characters: lowercase letters, numbers or underscore."
        )
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    salt = os.urandom(16)
    try:
        _execute(
            f"INSERT INTO users (username, salt, password_hash) VALUES ({PH}, {PH}, {PH})",
            (name, salt.hex(), _hash_password(password, salt)),
        )
    except Exception as e:
        if _is_duplicate_error(e):
            raise ValueError("This username is already taken.")
        raise


def verify_user(username: str, password: str) -> bool:
    """Return True if the username and password match."""
    row = _execute(
        f"SELECT salt, password_hash FROM users WHERE username = {PH}",
        (_clean(username),),
        fetch="one",
    )
    if row is None:
        return False

    salt_hex, stored_hash = row
    attempt = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(attempt, stored_hash)


# ---------------------------------------------------------------------------
# Chat messages (saved per username)
# ---------------------------------------------------------------------------
def save_message(user_name: str, role: str, content: str):
    """Save one chat message. role is 'user' or 'assistant'."""
    _execute(
        f"INSERT INTO messages (user_name, role, content) VALUES ({PH}, {PH}, {PH})",
        (_clean(user_name), role, content),
    )


def load_messages(user_name: str, limit: int = 50) -> list[dict]:
    """Return the most recent `limit` messages of a user, oldest first."""
    rows = _execute(
        f"SELECT role, content FROM messages WHERE user_name = {PH} "
        f"ORDER BY id DESC LIMIT {PH}",
        (_clean(user_name), limit),
        fetch="all",
    )
    rows = list(rows)
    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def clear_messages(user_name: str):
    """Delete all saved messages of a user."""
    _execute(
        f"DELETE FROM messages WHERE user_name = {PH}", (_clean(user_name),)
    ) 
    