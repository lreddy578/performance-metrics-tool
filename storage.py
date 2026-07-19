import json
from datetime import datetime
from pathlib import Path
from threading import Lock

DATA_DIR     = Path("data")
USERS_FILE   = DATA_DIR / "users.json"
METRICS_FILE = DATA_DIR / "metrics.json"

_lock = Lock()


def init_storage():
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        _write(USERS_FILE, {"next_id": 1, "users": {}})
        print("  ✅ Created data/users.json")
    if not METRICS_FILE.exists():
        _write(METRICS_FILE, {"metrics": {}})
        print("  ✅ Created data/metrics.json")
    print("  ✅ JSON storage ready.")


# ── I/O ────────────────────────────────────────────────────────────────────

def _read(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ── Users ──────────────────────────────────────────────────────────────────

def get_all_users() -> dict:
    return _read(USERS_FILE)


def get_user_by_id(user_id: int) -> dict | None:
    return get_all_users()["users"].get(str(user_id))


def get_user_by_email(email: str) -> dict | None:
    for u in get_all_users()["users"].values():
        if u["email"].lower() == email.lower():
            return u
    return None


def create_user(email: str, display_name: str,
                password_hash: str, role: str = "SDET") -> dict:
    with _lock:
        data = get_all_users()
        uid  = data["next_id"]
        user = {
            "id":            uid,
            "email":         email,
            "display_name":  display_name,
            "password_hash": password_hash,
            "role":          role,
            "is_manager":    0,
            "manager_id":    None,
            "created_at":    datetime.utcnow().isoformat(),
        }
        data["users"][str(uid)] = user
        data["next_id"]         = uid + 1
        _write(USERS_FILE, data)
        return user


def update_user(user_id: int, **kwargs) -> dict | None:
    with _lock:
        data = get_all_users()
        user = data["users"].get(str(user_id))
        if not user:
            return None
        for k, v in kwargs.items():
            if k in {"role", "is_manager", "manager_id", "display_name"}:
                user[k] = v
        data["users"][str(user_id)] = user
        _write(USERS_FILE, data)
        return user


def get_team_members(manager_id: int) -> list:
    return [
        u for u in get_all_users()["users"].values()
        if u.get("manager_id") == manager_id
    ]


# ── Metrics ────────────────────────────────────────────────────────────────

def get_user_metrics(user_id: int, year: int) -> dict:
    """Returns {metric_name: {actual_value, comment, updated_at}}"""
    data = _read(METRICS_FILE)
    return data["metrics"].get(str(user_id), {}).get(str(year), {})


def save_metric(user_id: int, year: int, metric_name: str,
                actual_value: float, comment: str = "") -> dict:
    with _lock:
        data  = _read(METRICS_FILE)
        uid   = str(user_id)
        yr    = str(year)
        data["metrics"].setdefault(uid, {}).setdefault(yr, {})
        entry = {
            "actual_value": actual_value,
            "comment":      comment,
            "updated_at":   datetime.utcnow().isoformat(),
        }
        data["metrics"][uid][yr][metric_name] = entry
        _write(METRICS_FILE, data)
        return entry