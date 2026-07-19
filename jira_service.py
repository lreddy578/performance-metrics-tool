import os
from requests import Session

JIRA_URL = os.getenv("JIRA_URL", "")

# ── Jira issue classification sets ────────────────────────────────────────
STORY_TYPES    = {"Story", "User Story", "Feature", "Task"}
BUG_TYPES      = {"Bug", "Defect", "Issue"}
DONE_STATUSES  = {"Done", "Closed", "Resolved", "Complete", "Completed"}
INVALID_STATUS = {"Won't Fix", "Won't Do", "Invalid",
                  "Duplicate", "Rejected", "Not a Bug"}
P0_PRIORITY    = {"Critical", "Blocker", "P0", "Highest"}


def search_issues(client: Session, jql: str, max_results: int = 50) -> list:
    """
    POST /rest/api/3/search/jql
      ↳ Current Atlassian Cloud endpoint (CHANGE-2046)
      ↳ Uses cursor-based pagination — no startAt allowed
    """
    url     = f"{JIRA_URL}/rest/api/3/search/jql"
    payload = {
        "jql":        jql,
        "maxResults": max_results,
        # ✅ No startAt — /search/jql uses cursor pagination, not offset
        "fields": [
            "summary",
            "status",
            "priority",
            "issuetype",
            "assignee",
            "updated",
            "customfield_10016",    # story points
        ],
    }

    resp = client.post(url, json=payload)

    # ── Rich error — shows Jira's exact message ───────────────────────────
    if not resp.ok:
        try:
            body     = resp.json()
            messages = body.get("errorMessages", [])
            errors   = body.get("errors", {})
            detail   = (
                "; ".join(messages) if messages
                else str(errors)    if errors
                else resp.text[:300]
            )
        except Exception:
            detail = resp.text[:300]
        raise Exception(f"Jira {resp.status_code}: {detail}")

    issues = []
    for issue in resp.json().get("issues", []):
        f = issue.get("fields", {})
        issues.append({
            "key":        issue["key"],
            "summary":    f.get("summary", ""),
            "status":     f.get("status",    {}).get("name", ""),
            "priority":   f.get("priority",  {}).get("name", ""),
            "issue_type": f.get("issuetype", {}).get("name", ""),
            "assignee":   (f.get("assignee") or {}).get("displayName", ""),
            "updated":    f.get("updated", ""),
            "url":        f"{JIRA_URL}/browse/{issue['key']}",
            "points":     f.get("customfield_10016"),
        })
    return issues


def get_my_issues(client: Session, user_email: str,
                  max_results: int = 50) -> list:
    """Open issues assigned to a specific user."""
    jql = (
        f'assignee = "{user_email}" '
        f'AND statusCategory != Done '
        f'ORDER BY updated DESC'
    )
    return search_issues(client, jql, max_results)


def get_issues_by_project(client: Session, project_key: str,
                           max_results: int = 20) -> list:
    """Open issues for a specific project."""
    jql = (
        f'project = "{project_key}" '
        f'AND statusCategory != Done '
        f'ORDER BY updated DESC'
    )
    return search_issues(client, jql, max_results)


def get_all_issues_for_year(client: Session, user_email: str,
                             year: int, max_results: int = 500) -> list:
    """Fetch ALL issues (open + closed) assigned to user for a given year."""
    jql = (
        f'assignee = "{user_email}" '
        f'AND updated >= "{year}-01-01" '
        f'AND updated <= "{year}-12-31" '
        f'ORDER BY updated DESC'
    )
    return search_issues(client, jql, max_results)


def _to_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def calculate_metrics_from_issues(issues: list) -> dict:
    """
    Calculate performance metric values from a list of Jira issues.
    Returns { metric_name: count }.
    """
    stories = [i for i in issues if i["issue_type"] in STORY_TYPES]
    bugs    = [i for i in issues if i["issue_type"] in BUG_TYPES]

    stories_done    = len([i for i in stories
                           if i["status"] in DONE_STATUSES])
    valid_bugs      = len([i for i in bugs
                           if i["status"] not in INVALID_STATUS])
    invalid_bugs    = len([i for i in bugs
                           if i["status"] in INVALID_STATUS])
    p0_leaked       = len([i for i in bugs
                           if i["priority"] in P0_PRIORITY])
    complex_stories = len([
        i for i in stories
        if _to_float(i.get("points")) >= 8
        and i["status"] in DONE_STATUSES
    ])

    return {
        "user_stories_completed": stories_done,
        "valid_defects":          valid_bugs,
        "invalid_defects":        invalid_bugs,
        "p0_defects_leaked":      p0_leaked,
        "complex_stories":        complex_stories,
    }