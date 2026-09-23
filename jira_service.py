import os
import requests
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote


@dataclass
class UserAssignments:
    username: str
    stories_assigned: int
    defects_assigned: int
    defects_reported: int
    bugs_assigned: int
    bugs_reported: int
    test_tasks_assigned: int
    test_plans_assigned: int
    test_executions_assigned: int
    user_stories_total: int
    valid_defects_total: int
    invalid_defects_total: int
    p0_defects_total: int
    metric_search_links: dict
    metric_space_breakdowns: dict
    search_links: dict
    space_breakdowns: dict
    queries: dict
    queries: dict


class JiraService:
    ALLOWED_STATUSES = ("Completed", "Done", "Accepted", "Closed", "Released")

    def __init__(self, server_url: str, email: str, api_token: str):
        self.base_url = server_url.rstrip("/")
        self.auth = (email, api_token)
        self._issue_type_names = None

    def _search_count(self, jql: str) -> int:
        """Count matching issues via /rest/api/3/search/jql, which has no 'total' field and must be paginated."""
        encoded_jql = quote(jql, safe='')
        base = f"{self.base_url}/rest/api/3/search/jql?jql={encoded_jql}&maxResults=100&fields=id"
        count = 0
        next_page_token = None
        while True:
            url = base if not next_page_token else f"{base}&nextPageToken={quote(next_page_token, safe='')}"
            resp = requests.get(url, auth=self.auth)
            if resp.status_code == 400:
                return 0
            resp.raise_for_status()
            data = resp.json()
            count += len(data.get("issues", []))
            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        return count

    def _count_by_space(self, jql: str) -> list:
        """Tally matching issues per project ('space'), returned as a list of {space, count} sorted by count desc."""
        encoded_jql = quote(jql, safe='')
        base = f"{self.base_url}/rest/api/3/search/jql?jql={encoded_jql}&maxResults=100&fields=project"
        counts = {}
        next_page_token = None
        while True:
            url = base if not next_page_token else f"{base}&nextPageToken={quote(next_page_token, safe='')}"
            resp = requests.get(url, auth=self.auth)
            if resp.status_code == 400:
                return []
            resp.raise_for_status()
            data = resp.json()
            for issue in data.get("issues", []):
                project = issue.get("fields", {}).get("project", {})
                space = project.get("name") or project.get("key") or "Unknown"
                counts[space] = counts.get(space, 0) + 1
            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        return sorted(
            ({"space": space, "count": count} for space, count in counts.items()),
            key=lambda item: item["count"],
            reverse=True,
        )

    def _search_issues(self, jql: str) -> list:
        encoded_jql = quote(jql, safe='')
        base = f"{self.base_url}/rest/api/3/search/jql?jql={encoded_jql}&maxResults=100&fields=summary,status,project,issuetype"
        issues = []
        next_page_token = None
        while True:
            url = base if not next_page_token else f"{base}&nextPageToken={quote(next_page_token, safe='')}"
            resp = requests.get(url, auth=self.auth)
            if resp.status_code == 400:
                return []
            resp.raise_for_status()
            data = resp.json()
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                project = fields.get("project") or {}
                status = fields.get("status") or {}
                issue_type = fields.get("issuetype") or {}
                key = issue.get("key", "")
                issues.append({
                    "key": key,
                    "summary": fields.get("summary", ""),
                    "status": status.get("name", ""),
                    "space": project.get("name") or project.get("key") or "Unknown",
                    "type": issue_type.get("name", "Unknown"),
                    "url": f"{self.base_url}/browse/{key}" if key else "",
                })
            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        return issues

    def _issues_by_type(self, issues: list, assignee: str, extra: str) -> list:
        grouped = {}
        for issue in issues:
            issue_type = issue.get("type") or "Unknown"
            grouped.setdefault(issue_type, []).append(issue)
        return [
            {
                "type": issue_type,
                "count": len(items),
                "items": items,
                "search_url": self._jira_search_url(f'{assignee} AND issuetype = "{issue_type}"{extra}'),
            }
            for issue_type, items in sorted(grouped.items())
        ]

    def _jira_search_url(self, jql: str) -> str:
        return f"{self.base_url}/issues/?jql={quote(jql, safe='')}"

    @staticmethod
    def _count_issue_types(issues: list, issue_type_names: set[str]) -> int:
        return sum(1 for issue in issues if issue.get("type") in issue_type_names)

    @staticmethod
    def _space_counts_for_types(issues: list, issue_type_names: set[str]) -> list:
        counts = {}
        for issue in issues:
            if issue.get("type") not in issue_type_names:
                continue
            space = issue.get("space") or "Unknown"
            counts[space] = counts.get(space, 0) + 1
        return sorted(
            ({"space": space, "count": count} for space, count in counts.items()),
            key=lambda item: item["count"],
            reverse=True,
        )

    def _get_issue_type_names(self) -> set:
        if self._issue_type_names is None:
            url = f"{self.base_url}/rest/api/3/issuetype"
            resp = requests.get(url, auth=self.auth)
            resp.raise_for_status()
            self._issue_type_names = {item.get("name", "") for item in resp.json()}
        return self._issue_type_names

    def _issue_type_clause(self, candidates: list[str], fallback: str) -> str:
        issue_type_names = self._get_issue_type_names()
        for candidate in candidates:
            if candidate in issue_type_names:
                return f'issuetype = "{candidate}"'
        return f'issuetype = "{fallback}"'

    def get_user_assignments(
        self,
        user_email: str,
        label: Optional[str] = None,
        fix_version: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> UserAssignments:
        assignee = f'assignee = "{user_email}"'
        reporter = f'reporter = "{user_email}"'

        extra = self._build_extra_filters(fix_version or label, None, start_date, end_date)
        status_filter = ' AND status IN ("Completed", "Done", "Accepted", "Closed", "Released")'
        cancelled_filter = ' AND status IN ("Cancelled", "Canceled")'

        def query(subject: str, issue_type: str) -> str:
            issue_extra = extra if issue_type == "Business Story" else self._build_extra_filters(
                None, None, start_date, end_date
            )
            return f'{subject} AND issuetype = "{issue_type}"{status_filter}{issue_extra}'

        def count(subject: str, issue_type: str) -> int:
            return self._search_count(query(subject, issue_type))

        assigned_metric_queries = {
            "user_stories_total": " OR ".join(
                f'{assignee} AND issuetype = "{issue_type}"{status_filter}{extra}'
                for issue_type in ("Test", "Test Plan", "Business Story", "Defect", "Bug Task")
            ),
        }
        valid_defects_query = " OR ".join(
            f'{reporter} AND issuetype = "{issue_type}"{extra}'
            for issue_type in ("Defect", "Bug Task")
        )
        invalid_defects_query = " OR ".join(
            f'{reporter} AND issuetype = "{issue_type}"{cancelled_filter}{extra}'
            for issue_type in ("Defect", "Bug Task")
        )
        p0_statuses = '("Completed", "Done", "Accepted", "Closed", "Released", "DEFECT", "Resolved")'
        p0_team_projects = 'project in ("PF A-Team", "PF B-Hive", "PF Purpose Accelerators", "PF Blackbirds", "PF Deep Divers", "PF Ravens", "PF Scrubbing Bubbles", "PF What\'s Kraken", "PF Problem Management")'
        p0_common = f'issuetype = "Defect" AND "Priority[Dropdown]" = "P0 - Resolve Immediately" AND status IN {p0_statuses}'
        p0_defects_query = (
            f'({p0_team_projects} AND "PF Application" IN (QFX, MyAccount) '
            f'AND {p0_common} AND "Incident Number" IS NOT EMPTY{extra}) '
            f'OR (project = "PF Firefighters" AND {p0_common}{extra})'
        )
        metric_queries = {
            "user_stories_total": assigned_metric_queries["user_stories_total"],
            "valid_defects_total": valid_defects_query,
            "invalid_defects_total": invalid_defects_query,
            "p0_defects_total": p0_defects_query,
        }

        queries = {
            "stories_assigned": query(assignee, "Business Story"),
            "defects_assigned": query(assignee, "Defect"),
            "defects_reported": query(reporter, "Defect"),
            "bugs_assigned": query(assignee, "Bug Task"),
            "bugs_reported": query(reporter, "Bug Task"),
            "test_tasks_assigned": query(assignee, "Test"),
            "test_plans_assigned": query(assignee, "Test Plan"),
            "test_executions_assigned": query(assignee, "Test Execution"),
        }
        search_links = {
            key: self._jira_search_url(value) for key, value in queries.items()
        }
        metric_search_links = {
            key: self._jira_search_url(value) for key, value in metric_queries.items()
        }
        space_breakdowns = {
            "stories_assigned": self._count_by_space(query(assignee, "Business Story")),
            "defects_assigned": self._count_by_space(query(assignee, "Defect")),
            "defects_reported": self._count_by_space(query(reporter, "Defect")),
            "bugs_assigned": self._count_by_space(query(assignee, "Bug Task")),
            "bugs_reported": self._count_by_space(query(reporter, "Bug Task")),
            "test_tasks_assigned": self._count_by_space(query(assignee, "Test")),
            "test_plans_assigned": self._count_by_space(query(assignee, "Test Plan")),
            "test_executions_assigned": self._count_by_space(query(assignee, "Test Execution")),
        }
        metric_space_breakdowns = {
            key: self._count_by_space(value.replace(" OR ", " OR "))
            for key, value in metric_queries.items()
        }

        return UserAssignments(
            username=user_email,
            stories_assigned=count(assignee, "Business Story"),
            defects_assigned=count(assignee, "Defect"),
            defects_reported=count(reporter, "Defect"),
            bugs_assigned=count(assignee, "Bug Task"),
            bugs_reported=count(reporter, "Bug Task"),
            test_tasks_assigned=count(assignee, "Test"),
            test_plans_assigned=count(assignee, "Test Plan"),
            test_executions_assigned=count(assignee, "Test Execution"),
            user_stories_total=self._search_count(metric_queries["user_stories_total"]),
            valid_defects_total=self._search_count(metric_queries["valid_defects_total"]),
            invalid_defects_total=self._search_count(metric_queries["invalid_defects_total"]),
            p0_defects_total=self._search_count(metric_queries["p0_defects_total"]),
            metric_search_links=metric_search_links,
            metric_space_breakdowns=metric_space_breakdowns,
            search_links=search_links,
            space_breakdowns=space_breakdowns,
            queries=queries,
        )

    @staticmethod
    def _build_extra_filters(
        label: Optional[str],
        fix_version: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> str:
        """Build additional ' AND ...' JQL clauses for label, fix version, and created-date range filters."""
        clauses = []
        if label:
            clauses.append(f'"Release Version[Dropdown]" = "{label}"')
        if fix_version:
            clauses.append(f'fixVersion = "{fix_version}"')
        if start_date:
            clauses.append(f'created >= "{start_date}"')
        if end_date:
            clauses.append(f'created <= "{end_date}"')
        return "".join(f" AND {clause}" for clause in clauses)