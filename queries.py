from jira import JIRA
from models import JiraIssue
from config import JIRA_URL


def get_my_open_issues(client: JIRA, max_results: int = 20) -> list[JiraIssue]:
    """Get open issues assigned to the current user."""
    jql = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
    issues = client.search_issues(jql, maxResults=max_results)
    return [_map_issue(issue) for issue in issues]


def get_issues_by_project(client: JIRA, project_key: str, max_results: int = 20) -> list[JiraIssue]:
    """Get open issues for a specific project."""
    jql = f"project = {project_key} AND statusCategory != Done ORDER BY updated DESC"
    issues = client.search_issues(jql, maxResults=max_results)
    return [_map_issue(issue) for issue in issues]


def _map_issue(issue) -> JiraIssue:
    """Map a raw Jira issue to our clean JiraIssue model."""
    return JiraIssue(
        key=issue.key,
        summary=issue.fields.summary,
        status=issue.fields.status.name,
        priority=issue.fields.priority.name if issue.fields.priority else "N/A",
        assignee=issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
        issue_type=issue.fields.issuetype.name if issue.fields.issuetype else "N/A",
        updated=issue.fields.updated[:10],
        url=f"{JIRA_URL}/browse/{issue.key}"
    )