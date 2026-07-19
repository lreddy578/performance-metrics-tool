import os
from datetime import timedelta, datetime

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from auth import (hash_password, verify_password, create_access_token,
                  get_current_user, CurrentUser, ACCESS_TOKEN_EXPIRE_MINUTES)
import storage
from jira_client import get_jira_client
from jira_service import (get_all_issues_for_year, calculate_metrics_from_issues)
from metrics_service import METRICS_CONFIG
from models import RegisterRequest, LoginRequest, Token, MetricInput, UserUpdate

load_dotenv()
storage.init_storage()

app = FastAPI(title="Performance Metrics Tool", version="4.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

jira = get_jira_client()


# ── Pages ──────────────────────────────────────────────────────────────────

@app.get("/")
def serve_login():
    return FileResponse("frontend/login.html")

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("frontend/dashboard.html")

@app.get("/manager")
def serve_manager():
    return FileResponse("frontend/manager.html")


# ── Auth ───────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=Token)
def register(req: RegisterRequest):
    if storage.get_user_by_email(req.email):
        raise HTTPException(status_code=400,
                            detail="Email already registered.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 6 characters.")

    user  = storage.create_user(
        email         = req.email,
        display_name  = req.display_name,
        password_hash = hash_password(req.password),
        role          = req.role,
    )
    token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":           user["id"],
            "email":        user["email"],
            "display_name": user["display_name"],
            "role":         user["role"],
            "is_manager":   user["is_manager"],
            "manager_id":   user["manager_id"],
        },
    }


@app.post("/auth/login", response_model=Token)
def login(req: LoginRequest):
    user = storage.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401,
                            detail="Invalid email or password.")

    token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":           user["id"],
            "email":        user["email"],
            "display_name": user["display_name"],
            "role":         user["role"],
            "is_manager":   user["is_manager"],
            "manager_id":   user["manager_id"],
        },
    }


@app.get("/auth/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    user = storage.get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "id":           user["id"],
        "email":        user["email"],
        "display_name": user["display_name"],
        "role":         user["role"],
        "is_manager":   user["is_manager"],
        "manager_id":   user["manager_id"],
    }


# ── Metrics ────────────────────────────────────────────────────────────────

@app.get("/api/metrics/my")
def get_my_metrics(
    year:         int       = Query(default=2025),
    current_user: CurrentUser = Depends(get_current_user),
):
    config = METRICS_CONFIG.get(current_user.role, METRICS_CONFIG["SDET"])
    saved  = storage.get_user_metrics(current_user.id, year)
    return [{
        **m,
        "actual_value": saved.get(m["name"], {}).get("actual_value"),
        "comment":      saved.get(m["name"], {}).get("comment", ""),
    } for m in config]


@app.post("/api/metrics/save")
def save_my_metric(
    metric:       MetricInput,
    current_user: CurrentUser = Depends(get_current_user),
):
    saved = storage.save_metric(
        current_user.id, metric.year,
        metric.metric_name, metric.actual_value,
        metric.comment,
    )
    return {
        "success": True,
        "metric":  metric.metric_name,
        "value":   saved["actual_value"],
        "comment": saved["comment"],
    }


@app.get("/api/metrics/team")
def get_team(
    year:         int       = Query(default=2025),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.is_manager:
        raise HTTPException(status_code=403, detail="Manager role required.")
    team   = storage.get_team_members(current_user.id)
    result = []
    for member in team:
        config = METRICS_CONFIG.get(member["role"], METRICS_CONFIG["SDET"])
        saved  = storage.get_user_metrics(member["id"], year)
        result.append({
            "user": {
                "id":    member["id"],
                "name":  member["display_name"],
                "email": member["email"],
                "role":  member["role"],
            },
            "metrics": [{
                **m,
                "actual_value": saved.get(m["name"], {}).get("actual_value"),
                "comment":      saved.get(m["name"], {}).get("comment", ""),
            } for m in config],
        })
    return result


# ── Jira ───────────────────────────────────────────────────────────────────

@app.post("/api/jira/sync-metrics")
def sync_jira_metrics(
    year:         int       = Query(default=2025),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        issues     = get_all_issues_for_year(jira, current_user.email, year)
        calculated = calculate_metrics_from_issues(issues)
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"Jira fetch failed: {str(e)}")
    for metric_name, value in calculated.items():
        storage.save_metric(current_user.id, year, metric_name, value)
    return {
        "success":      True,
        "issues_found": len(issues),
        "metrics":      calculated,
    }


@app.get("/api/jira/debug")
def debug_jira_issues(
    email: str = Query(...),
    year:  int = Query(default=2025),
):
    try:
        issues = get_all_issues_for_year(jira, email, year)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jira error: {str(e)}")

    type_counts, status_counts, priority_counts = {}, {}, {}
    for i in issues:
        t = i["issue_type"] or "—"
        s = i["status"]     or "—"
        p = i["priority"]   or "—"
        type_counts[t]     = type_counts.get(t, 0) + 1
        status_counts[s]   = status_counts.get(s, 0) + 1
        priority_counts[p] = priority_counts.get(p, 0) + 1

    return {
        "total_issues": len(issues),
        "issue_types":  type_counts,
        "statuses":     status_counts,
        "priorities":   priority_counts,
        "sample":       issues[:3],
    }


# ── Admin ──────────────────────────────────────────────────────────────────

@app.get("/admin/users")
def list_users():
    data = storage.get_all_users()
    # Never expose password_hash
    return [
        {k: v for k, v in u.items() if k != "password_hash"}
        for u in data["users"].values()
    ]


@app.patch("/admin/users/{user_id}")
def update_user(user_id: int, update: UserUpdate):
    kwargs = {k: v for k, v in update.dict().items() if v is not None}
    user   = storage.update_user(user_id, **kwargs)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "success":    True,
        "user_id":    user["id"],
        "role":       user["role"],
        "is_manager": user["is_manager"],
        "manager_id": user["manager_id"],
    }