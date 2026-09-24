from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import requests as http_requests

import storage
import auth as auth_utils
from metrics_service import ROLE_METRICS_CONFIG, get_metrics_for_role
from models import (UserCreate, UserUpdate, LoginRequest,
                    RegisterRequest, SetPasswordRequest,
                    JiraAuthRequest,
                    MetricEntryCreate,
                    ForgotPasswordRequest, ResetWithTokenRequest)
from jira_routes import router as jira_router

import secrets
from datetime import datetime, timedelta

# ── In-memory password reset tokens { token: {user_id, expires} } ──────────
RESET_TOKENS: dict = {}

load_dotenv()

def is_super_viewer(user: dict) -> bool:
    return auth_utils.is_super_viewer(user)
# ─────────────────────────────────────────────────────────────────────────────

storage.init_storage()
auth_utils.load_sessions()

app = FastAPI(title="Achiever's Scorecard", version="7.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.include_router(jira_router)

# ── Admin email — only this user can access /admin ─────────────────────────
ADMIN_EMAIL = "lreddy@teampurpose.com"  # ← your email (lowercase)


# ── Startup bootstrap ──────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    users = storage.get_all_users()
    has_pw = any(u.get("password_hash") for u in users)
    if not has_pw:
        if not users:
            pw = auth_utils.hash_password("Admin@123")
            storage.create_user("Admin", "admin@local", "Manager", pw)
            print("\n  ✅ Created default account: admin@local")
        else:
            first = users[0]
            storage.set_password(
                first["id"],
                auth_utils.hash_password("Admin@123"))
            print(f"\n  ✅ Set default password for: {first['email']}")
        print("  🔑 Default password: Admin@123")
        print("  ⚠️  Change it immediately in Admin → Reset Password!\n")


# ── Auth Dependencies ──────────────────────────────────────────────────────

def get_current_user(
        authorization: str = Header(default=None)) -> dict:
    if not authorization \
            or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in.")
    token   = authorization.split(" ", 1)[1]
    user_id = auth_utils.get_session_user_id(token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.")
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=401, detail="User not found.")
    return user


def require_admin(
        current_user: dict = Depends(get_current_user)) -> dict:
    """Only the admin email can call these endpoints."""
    if current_user.get("email", "").lower() != ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="Admin access required.")
    return current_user


def safe_user(u: dict) -> dict:
    """Strip sensitive fields before returning to frontend."""
    return {k: v for k, v in u.items()
            if k not in ("password_hash", "jira_api_token")}


# ── Pages ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("frontend/login.html")

@app.get("/login")
def login_page():
    return FileResponse("frontend/login.html")

@app.get("/user")
def user_page():
    return FileResponse("frontend/user.html")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse("frontend/dashboard.html")

@app.get("/admin")
def admin_page():
    # HTML is served publicly — JS inside admin.html guards access
    return FileResponse("frontend/admin.html")

@app.get("/jira-auth")
def jira_auth_page():
    return FileResponse("frontend/jira-auth.html")

@app.get("/jira-assignments")
def jira_assignments_page():
    return FileResponse("frontend/jira-assignments.html")

@app.get("/reset-password")
def reset_password_page():
    return FileResponse("frontend/reset-password.html")


# ── Auth Endpoints ─────────────────────────────────────────────────────────

@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest):
    if not req.name.strip() or not req.email.strip():
        raise HTTPException(status_code=400,
                            detail="Name and email are required.")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 4 characters.")
    if storage.get_user_by_email(req.email):
        raise HTTPException(status_code=400,
                            detail="An account with this email already exists.")
    pw_hash = auth_utils.hash_password(req.password)
    user    = storage.create_user(
        req.name.strip(),
        req.email.strip().lower(),
        req.role,
        pw_hash,
        manager_email=req.manager_email.strip().lower()  # ← NEW
    )
    token = auth_utils.create_session(user["id"])
    response_user = safe_user(user)
    response_user["is_super_viewer"] = is_super_viewer(user)
    return {"token": token, "user": response_user}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = storage.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401,
                            detail="Invalid email or password.")
    pw_hash = user.get("password_hash")
    if not pw_hash:
        raise HTTPException(status_code=401,
                            detail="No password set for this account. "
                                   "Ask your admin to set one.")
    if not auth_utils.verify_password(req.password, pw_hash):
        raise HTTPException(status_code=401,
                            detail="Invalid email or password.")
    token = auth_utils.create_session(user["id"])
    response_user = safe_user(user)
    response_user["is_super_viewer"] = is_super_viewer(user)
    return {"token": token, "user": response_user}

@app.post("/api/auth/logout")
def logout(authorization: str = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        auth_utils.delete_session(authorization.split(" ", 1)[1])
    return {"success": True}

@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    out = safe_user(current_user)
    out["entry_count"] = storage.get_user_entry_count(current_user["id"])
    out["is_super_viewer"] = is_super_viewer(current_user)
    return out

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """
    Generates a one-time reset link.
    Always returns 200 so we don't reveal if an email exists.
    """
    user = storage.get_user_by_email(req.email.strip().lower())
    if not user:
        # Return same response to avoid email enumeration
        return {"reset_url": None,
                "message": "If that email is registered, a reset link was generated."}

    if not user.get("password_hash"):
        raise HTTPException(
            status_code=400,
            detail="This account has no password set. Contact your admin.")

    # Clean up any old token for this user
    for t, v in list(RESET_TOKENS.items()):
        if v["user_id"] == user["id"]:
            del RESET_TOKENS[t]

    token   = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    RESET_TOKENS[token] = {
        "user_id": user["id"],
        "expires": expires.isoformat()
    }
    reset_url = f"/reset-password?token={token}"
    return {"reset_url": reset_url,
            "message": "Reset link generated. Copy it and open in your browser."}


@app.post("/api/auth/reset-password")
def reset_password_with_token(req: ResetWithTokenRequest):
    """Validates reset token and sets the new password."""
    data = RESET_TOKENS.get(req.token)
    if not data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or already used reset link. Please request a new one.")

    expires = datetime.fromisoformat(data["expires"])
    if datetime.utcnow() > expires:
        del RESET_TOKENS[req.token]
        raise HTTPException(
            status_code=400,
            detail="This reset link has expired (1 hour limit). Please request a new one.")

    if not req.password or len(req.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters.")

    storage.set_password(data["user_id"],
                         auth_utils.hash_password(req.password))
    del RESET_TOKENS[req.token]   # one-time use
    return {"success": True, "message": "Password updated! You can now log in."}


@app.get("/api/auth/validate-reset-token/{token}")
def validate_reset_token(token: str):
    """Checks if a reset token is valid and not expired."""
    data = RESET_TOKENS.get(token)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid reset link.")
    expires = datetime.fromisoformat(data["expires"])
    if datetime.utcnow() > expires:
        del RESET_TOKENS[token]
        raise HTTPException(status_code=400, detail="Reset link has expired.")
    return {"valid": True}


# ── Users API (🔒 admin only) ──────────────────────────────────────────────

@app.get("/api/users")
def get_users(admin: dict = Depends(require_admin)):   # ← 🔒 protected
    users = storage.get_all_users()
    result = []
    for u in users:
        s = safe_user(u)
        s["entry_count"]  = storage.get_user_entry_count(u["id"])
        s["has_password"] = bool(u.get("password_hash"))
        result.append(s)
    return result

@app.post("/api/users", status_code=201)
def add_user(req: UserCreate,
             admin: dict = Depends(require_admin)):
    if not req.name.strip() or not req.email.strip():
        raise HTTPException(status_code=400,
                            detail="Name and email are required.")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 4 characters.")
    users = storage.get_all_users()
    if any(u["email"].lower() == req.email.strip().lower() for u in users):
        raise HTTPException(status_code=400,
                            detail="A user with this email already exists.")
    pw_hash = auth_utils.hash_password(req.password)
    user    = storage.create_user(
        req.name.strip(), req.email.strip(), req.role, pw_hash,
        manager_email=req.manager_email   # ← NEW
    )
    return safe_user(user)

@app.put("/api/users/{user_id}")
def edit_user(user_id: int, req: UserUpdate,
              admin: dict = Depends(require_admin)):
    if not req.name.strip() or not req.email.strip():
        raise HTTPException(status_code=400,
                            detail="Name and email are required.")
    users = storage.get_all_users()
    if any(u["email"].lower() == req.email.strip().lower()
           and u["id"] != user_id for u in users):
        raise HTTPException(status_code=400,
                            detail="Another user already has this email.")
    user = storage.update_user(
        user_id, req.name.strip(), req.email.strip(), req.role,
        manager_email=req.manager_email   # ← NEW
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if req.password and len(req.password) >= 4:
        storage.set_password(user_id, auth_utils.hash_password(req.password))
    return safe_user(user)

@app.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: int, req: SetPasswordRequest,
                   admin: dict = Depends(require_admin)):  # ← 🔒 protected
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 4 characters.")
    if not storage.set_password(
            user_id, auth_utils.hash_password(req.password)):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "Password updated."}

@app.delete("/api/users/{user_id}")
def remove_user(user_id: int,
                admin: dict = Depends(require_admin)):  # ← 🔒 protected
    if not storage.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True,
            "message": "User and all their entries deleted."}


# ── Jira Auth (protected — own credentials only) ───────────────────────────

@app.post("/api/users/{user_id}/jira-auth")
def set_jira_auth(user_id: int, req: JiraAuthRequest,
                  current_user: dict = Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403,
            detail="You can only set your own Jira credentials.")
    if not req.jira_url.strip() or not req.jira_email.strip() \
            or not req.jira_api_token.strip():
        raise HTTPException(status_code=400,
                            detail="All Jira fields are required.")
    verify_url = req.jira_url.strip().rstrip("/") + "/rest/api/3/myself"
    try:
        resp = http_requests.get(
            verify_url,
            auth=(req.jira_email.strip(), req.jira_api_token.strip()),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 401:
            raise HTTPException(status_code=400,
                detail="Invalid Jira credentials. Check your email and API token.")
        if resp.status_code == 403:
            raise HTTPException(status_code=400,
                detail="Access forbidden. Try regenerating your token.")
        if resp.status_code == 404:
            raise HTTPException(status_code=400,
                detail="Jira URL not found. Check the URL.")
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=400,
                detail=f"Jira returned HTTP {resp.status_code}.")
    except http_requests.ConnectionError:
        raise HTTPException(status_code=400,
            detail="Cannot reach Jira. Check the URL.")
    except http_requests.Timeout:
        raise HTTPException(status_code=400,
            detail="Jira request timed out.")
    except http_requests.RequestException as e:
        raise HTTPException(status_code=400,
            detail=f"Network error: {str(e)}")

    user = storage.save_jira_auth(
        user_id,
        req.jira_url.strip().rstrip("/"),
        req.jira_email.strip(),
        req.jira_api_token.strip(),
    )
    if user:
        return safe_user(user)
    raise HTTPException(status_code=404, detail="User not found.")

@app.delete("/api/users/{user_id}/jira-auth")
def revoke_jira_auth(user_id: int,
                     current_user: dict = Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403,
            detail="You can only revoke your own Jira credentials.")
    user = storage.clear_jira_auth(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return safe_user(user)


# ── Reportees (protected) ─────────────────────────────────────────────────

@app.get("/api/managers/{manager_id}/reportees")
def get_reportees(manager_id: int,
                  current_user: dict = Depends(get_current_user)):
    if current_user["id"] != manager_id:
        raise HTTPException(status_code=403,
            detail="You can only view your own reportees.")
    manager = storage.get_user_by_id(manager_id)
    if not manager or manager["role"] != "Manager":
        raise HTTPException(status_code=404, detail="Manager not found.")
    reps = storage.get_reportees(manager_id)
    result = []
    for r in reps:
        s = safe_user(r)
        s["entry_count"] = storage.get_user_entry_count(r["id"])
        result.append(s)
    return result

@app.get("/api/dashboard/viewable-users")
def get_dashboard_users(
        current_user: dict = Depends(get_current_user)):
    """
    Super-viewers → all users (except themselves).
    Managers      → auto-derived reportees (signed up with their email).
    Others        → 403.
    """
    if is_super_viewer(current_user):
        users = [u for u in storage.get_all_users()
                 if u["id"] != current_user["id"]]
    elif current_user["role"] == "Manager":
        users = storage.get_reportees(current_user["id"])
    else:
        raise HTTPException(
            status_code=403,
            detail="Dashboard access requires Manager role or special permissions.")
    result = []
    for u in users:
        s = safe_user(u)
        s["entry_count"]  = storage.get_user_entry_count(u["id"])
        s["manager_email"] = u.get("manager_email", "")
        result.append(s)
    return result

# ── Metrics Config ─────────────────────────────────────────────────────────

@app.get("/api/metrics/config")
def get_config():
    return ROLE_METRICS_CONFIG


# ── Metrics (protected — own data only) ───────────────────────────────────

@app.get("/api/metrics/{user_id}")
def get_entries(user_id: int,
                current_user: dict = Depends(get_current_user)):
    # Super-viewers can see anyone's data
    if is_super_viewer(current_user):
        pass
    elif current_user["id"] != user_id:
        if current_user["role"] == "Manager":
            reportees = storage.get_reportees(current_user["id"])
            rep_ids   = [r["id"] for r in reportees]
            if user_id not in rep_ids:
                raise HTTPException(status_code=403,
                    detail="This user is not in your reportees.")
        else:
            raise HTTPException(status_code=403,
                detail="You can only view your own data.")
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    entries = storage.get_entries_by_user(user_id)
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return {"user": safe_user(user), "entries": entries}

@app.post("/api/metrics/{user_id}", status_code=201)
def add_entry(user_id: int, req: MetricEntryCreate,
              current_user: dict = Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403,
            detail="You can only add metrics for yourself.")
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    payload = req.dict()
    notes   = payload.pop("notes", "")
    role_metric_names = {metric["name"] for metric in get_metrics_for_role(user["role"])}
    metrics = {k: v for k, v in payload.items()
               if k in role_metric_names and v is not None}
    if not metrics:
        raise HTTPException(status_code=400,
            detail="Enter at least one metric value.")
    return storage.create_entry(user_id, metrics, notes)

@app.put("/api/metrics/{user_id}/{entry_id}")
def update_entry_route(user_id: int, entry_id: int,
                       req: MetricEntryCreate,
                       current_user: dict = Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403,
            detail="You can only edit your own metrics.")
    entry = storage.get_entry_by_id(user_id, entry_id)
    if not entry or entry["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Entry not found.")
    payload = req.dict()
    notes   = payload.pop("notes", "")
    role_metric_names = {
        metric["name"] for metric in get_metrics_for_role(current_user["role"])
    }
    metrics = {k: v for k, v in payload.items()
               if k in role_metric_names and v is not None}
    return storage.update_entry(user_id, entry_id, metrics, notes)

@app.delete("/api/metrics/{user_id}/{entry_id}")
def delete_entry_route(user_id: int, entry_id: int,
                       current_user: dict = Depends(get_current_user)):
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403,
            detail="You can only delete your own metrics.")
    entry = storage.get_entry_by_id(user_id, entry_id)
    if not entry or entry["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Entry not found.")
    storage.delete_entry(user_id, entry_id)
    return {"success": True}