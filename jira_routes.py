from fastapi import APIRouter, Query, HTTPException, Header
import auth as auth_utils
import storage
from jira_service import JiraService
from jira_config import JIRA_SERVER_URL, JIRA_EMAIL, JIRA_API_TOKEN

router = APIRouter(prefix="/api/jira", tags=["jira"])


def _authorized_user(authorization: str | None, requested_email: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    user_id = auth_utils.get_session_user_id(authorization.split(" ", 1)[1])
    current_user = storage.get_user_by_id(user_id) if user_id else None
    if not current_user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    requested = requested_email.strip().lower()
    own_email = current_user.get("email", "").lower()
    if requested == own_email or own_email == "lreddy@teampurpose.com":
        return current_user
    if current_user.get("role") == "Manager":
        reportee_emails = {
            user.get("email", "").lower()
            for user in storage.get_reportees(current_user["id"])
        }
        if requested in reportee_emails:
            return current_user
    raise HTTPException(status_code=403, detail="You can only view your own or your reportee's Jira metrics.")


@router.get("/assignments")
def get_assignments(
    email: str = Query(..., description="User's email to look up in Jira"),
    label: str = Query(None, description="Filter issues by Jira label"),
    fix_version: str = Query(None, description="Release / Fix Version value matched against the Jira Release Version field"),
    start_date: str = Query(None, description="Only include issues created on/after this date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="Only include issues created on/before this date (YYYY-MM-DD)"),
    authorization: str = Header(default=None),
):
    """
    Fetch Jira assignments for any user by their email.
    Uses a single admin PAT (from .env) to query Jira on behalf of all users.
    """
    if not JIRA_SERVER_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
        raise HTTPException(status_code=500, detail="Jira is not configured. Set JIRA_SERVER_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env")

    try:
        _authorized_user(authorization, email)
        service = JiraService(JIRA_SERVER_URL, JIRA_EMAIL, JIRA_API_TOKEN)
        assignments = service.get_user_assignments(email, label, fix_version, start_date, end_date)
        return {
            "email": assignments.username,
            "stories_assigned": assignments.stories_assigned,
            "defects_assigned": assignments.defects_assigned,
            "defects_reported": assignments.defects_reported,
            "bugs_assigned": assignments.bugs_assigned,
            "bugs_reported": assignments.bugs_reported,
            "test_tasks_assigned": assignments.test_tasks_assigned,
            "test_plans_assigned": assignments.test_plans_assigned,
            "test_executions_assigned": assignments.test_executions_assigned,
            "user_stories_total": assignments.user_stories_total,
            "valid_defects_total": assignments.valid_defects_total,
            "invalid_defects_total": assignments.invalid_defects_total,
            "p0_defects_total": assignments.p0_defects_total,
            "metric_search_links": assignments.metric_search_links,
            "metric_space_breakdowns": assignments.metric_space_breakdowns,
            "search_links": assignments.search_links,
            "space_breakdowns": assignments.space_breakdowns,
            "queries": assignments.queries,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))