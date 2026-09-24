import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path

SESSIONS_FILE   = Path("data/sessions.json")
SESSION_TTL_HRS = 8
_sessions: dict = {}

SUPER_VIEWER_EMAILS = {
    "jamose@teampurpose.com",
}


def is_super_viewer(user: dict) -> bool:
    return user.get("email", "").strip().lower() in SUPER_VIEWER_EMAILS


def load_sessions():
    global _sessions
    if SESSIONS_FILE.exists():
        try:
            raw = json.loads(
                SESSIONS_FILE.read_text(encoding="utf-8"))
            now = datetime.utcnow().isoformat()
            # Drop expired sessions on load
            _sessions = {k: v for k, v in raw.items()
                         if v.get("expires_at", "") > now}
        except Exception:
            _sessions = {}


def _save():
    SESSIONS_FILE.parent.mkdir(exist_ok=True)
    SESSIONS_FILE.write_text(
        json.dumps(_sessions, indent=2), encoding="utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h    = hashlib.sha256(
        f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, h = hashed.split(":", 1)
        computed = hashlib.sha256(
            f"{salt}{plain}".encode()).hexdigest()
        return secrets.compare_digest(computed, h)
    except Exception:
        return False


def create_session(user_id: int) -> str:
    token   = secrets.token_urlsafe(32)
    expires = (datetime.utcnow()
               + timedelta(hours=SESSION_TTL_HRS)).isoformat()
    _sessions[token] = {
        "user_id":    user_id,
        "expires_at": expires,
    }
    _save()
    return token


def get_session_user_id(token: str) -> int | None:
    sess = _sessions.get(token)
    if not sess:
        return None
    if sess["expires_at"] < datetime.utcnow().isoformat():
        del _sessions[token]
        _save()
        return None
    return int(sess["user_id"])


def delete_session(token: str):
    if token in _sessions:
        del _sessions[token]
        _save()