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
    if not METRICS_FILE.exists():
        _write(METRICS_FILE, {"next_id": 1, "entries_by_user": {}})
    _run_migrations()
    print("  ✅ Storage ready.")


def _run_migrations():
    """Safely migrate persisted user and metric data."""
    with _lock:
        data    = _read(USERS_FILE)
        changed = False
        for u in data["users"].values():
            if "manager_email" not in u:
                u["manager_email"] = ""
                changed = True
        if changed:
            _write(USERS_FILE, data)
            print("  ✅ Migration: added manager_email to existing users.")

        metrics_data = _read(METRICS_FILE)
        if "entries" in metrics_data:
            entries_by_user = {}
            for entry_id, entry in metrics_data["entries"].items():
                user_entries = entries_by_user.setdefault(str(entry["user_id"]), {})
                user_entries[entry_id] = entry
            _write(METRICS_FILE, {
                "next_id": metrics_data.get("next_id", 1),
                "entries_by_user": entries_by_user,
            })
            print("  ✅ Migration: grouped metric entries by user.")


def _read(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ── Users ──────────────────────────────────────────────────────────────────

def get_all_users() -> list:
    return list(_read(USERS_FILE)["users"].values())


def get_user_by_id(user_id: int) -> dict | None:
    return _read(USERS_FILE)["users"].get(str(user_id))


def get_user_by_email(email: str) -> dict | None:
    for u in _read(USERS_FILE)["users"].values():
        if u["email"].lower() == email.strip().lower():
            return u
    return None


def create_user(name: str, email: str, role: str,
                password_hash: str,
                manager_email: str = "") -> dict:
    with _lock:
        data = _read(USERS_FILE)
        uid  = data["next_id"]
        user = {
            "id":                 uid,
            "name":               name,
            "email":              email.strip().lower(),
            "role":               role,
            "password_hash":      password_hash,
            "manager_email":      manager_email.strip().lower()
                                  if manager_email else "",
            "created_at":         datetime.utcnow().isoformat(),
            "jira_authenticated": False,
            "jira_url":           None,
            "jira_email":         None,
            "jira_api_token":     None,
        }
        data["users"][str(uid)] = user
        data["next_id"]         = uid + 1
        _write(USERS_FILE, data)
        return user


def update_user(user_id: int, name: str, email: str,
                role: str, manager_email: str | None = None) -> dict | None:
    with _lock:
        data = _read(USERS_FILE)
        user = data["users"].get(str(user_id))
        if not user:
            return None
        user["name"]       = name
        user["email"]      = email.strip().lower()
        user["role"]       = role
        user["updated_at"] = datetime.utcnow().isoformat()
        # Only update manager_email if explicitly provided
        if manager_email is not None:
            user["manager_email"] = manager_email.strip().lower() \
                                    if manager_email else ""
        # Ensure field exists for old records
        if "manager_email" not in user:
            user["manager_email"] = ""
        data["users"][str(user_id)] = user
        _write(USERS_FILE, data)
        return user


def set_password(user_id: int, password_hash: str) -> bool:
    with _lock:
        data = _read(USERS_FILE)
        if str(user_id) not in data["users"]:
            return False
        data["users"][str(user_id)]["password_hash"] = password_hash
        _write(USERS_FILE, data)
        return True


def delete_user(user_id: int) -> bool:
    with _lock:
        udata = _read(USERS_FILE)
        if str(user_id) not in udata["users"]:
            return False
        del udata["users"][str(user_id)]
        _write(USERS_FILE, udata)
        mdata = _read(METRICS_FILE)
        mdata["entries_by_user"].pop(str(user_id), None)
        _write(METRICS_FILE, mdata)
        return True


def get_user_entry_count(user_id: int) -> int:
    data = _read(METRICS_FILE)
    return len(data["entries_by_user"].get(str(user_id), {}))


# ── Jira Auth ──────────────────────────────────────────────────────────────

def save_jira_auth(user_id: int, jira_url: str,
                   jira_email: str, jira_api_token: str) -> dict | None:
    with _lock:
        data = _read(USERS_FILE)
        user = data["users"].get(str(user_id))
        if not user:
            return None
        user["jira_url"]           = jira_url
        user["jira_email"]         = jira_email
        user["jira_api_token"]     = jira_api_token
        user["jira_authenticated"] = True
        user["jira_auth_at"]       = datetime.utcnow().isoformat()
        data["users"][str(user_id)] = user
        _write(USERS_FILE, data)
        return user


def clear_jira_auth(user_id: int) -> dict | None:
    with _lock:
        data = _read(USERS_FILE)
        user = data["users"].get(str(user_id))
        if not user:
            return None
        user["jira_url"]           = None
        user["jira_email"]         = None
        user["jira_api_token"]     = None
        user["jira_authenticated"] = False
        data["users"][str(user_id)] = user
        _write(USERS_FILE, data)
        return user


# ── Reportees (auto-derived from manager_email set during signup) ──────────

def get_reportees(manager_id: int) -> list:
    """
    Returns all users whose manager_email matches this manager's email.
    No manual assignment needed — automatically derived from signup data.
    """
    data    = _read(USERS_FILE)
    manager = data["users"].get(str(manager_id))
    if not manager:
        return []
    manager_email = manager.get("email", "").strip().lower()
    return [
        u for u in data["users"].values()
        if u.get("manager_email", "").strip().lower() == manager_email
        and u["id"] != manager_id
    ]


# ── Metric Entries ─────────────────────────────────────────────────────────

def get_entries_by_user(user_id: int) -> list:
    data = _read(METRICS_FILE)
    return list(data["entries_by_user"].get(str(user_id), {}).values())


def get_entry_by_id(user_id: int, entry_id: int) -> dict | None:
    data = _read(METRICS_FILE)
    return data["entries_by_user"].get(str(user_id), {}).get(str(entry_id))


def create_entry(user_id: int, metrics: dict,
                 notes: str = "") -> dict:
    with _lock:
        data  = _read(METRICS_FILE)
        eid   = data["next_id"]
        now   = datetime.utcnow()
        entry = {
            "id":        eid,
            "user_id":   user_id,
            "date":      now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            **metrics,
            "notes":     notes,
        }
        data["entries_by_user"].setdefault(str(user_id), {})[str(eid)] = entry
        data["next_id"] = eid + 1
        _write(METRICS_FILE, data)
        return entry


def update_entry(user_id: int, entry_id: int, metrics: dict,
                 notes: str = "") -> dict | None:
    with _lock:
        data  = _read(METRICS_FILE)
        entry = data["entries_by_user"].get(str(user_id), {}).get(str(entry_id))
        if not entry:
            return None
        entry.update({**metrics, "notes": notes,
                      "updated_at": datetime.utcnow().isoformat()})
        _write(METRICS_FILE, data)
        return entry


def delete_entry(user_id: int, entry_id: int) -> bool:
    with _lock:
        data = _read(METRICS_FILE)
        entries = data["entries_by_user"].get(str(user_id), {})
        if str(entry_id) not in entries:
            return False
        del entries[str(entry_id)]
        _write(METRICS_FILE, data)
        return True