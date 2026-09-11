# Performance Metrics Tool
## Technology and Solution Design Document

**Prepared:** September 2026

## 1. Executive Summary

Performance Metrics Tool is a lightweight web application for collecting and reviewing SDET performance metrics. It combines a FastAPI backend, browser-based HTML/CSS/JavaScript pages, JSON file persistence, bearer-token sessions, role-aware views, and Jira assignment metrics.

The Jira experience presents numeric counts for stories, defects, bugs, tests, test plans, and test executions. Each card has a Jira search link and an expandable count by project/space. Counts are restricted to Completed, Done, Accepted, Closed, and Released statuses.

## 2. Objective and Goals

- Create one practical workspace for individual contributors, managers, and administrators to record and review performance data.
- Reduce manual Jira reporting by calculating user-specific assigned and reported work counts.
- Give managers visibility into team metrics and reportee relationships.
- Keep the initial solution simple to run locally and easy to evolve toward production scale.
- Provide traceable Jira search links so users can validate numbers against Jira.

## 3. Current Architecture

| Layer | Current implementation | Responsibility |
|---|---|---|
| Presentation | Static HTML, CSS, JavaScript | Login, metric entry, dashboards, administration, Jira cards and filters |
| API | FastAPI 0.111.0 | Routes, request validation, authentication dependencies, JSON responses |
| Business services | `metrics_service.py`, `jira_service.py` | Metric configuration, Jira JQL, counts, links, space aggregation |
| Persistence | `storage.py`, `data/*.json` | Users, metric entries, sessions, migrations, CRUD operations |
| Authentication | `auth.py` | Password hashing, bearer sessions, expiration, deletion |
| Integration | Jira REST API v3 via `requests` | Issue counts, project/space aggregation, Jira search URLs |

## 4. Technology Details

### Backend

- Python 3.13.9 environment.
- FastAPI provides the application and API framework.
- Uvicorn runs the app locally with `uvicorn app:app --reload`.
- Pydantic models validate registration, login, password, Jira authentication, and metric-entry payloads.
- `python-dotenv` loads `.env` configuration.
- `requests` performs outbound Jira REST calls.
- SQLAlchemy/database drivers are listed as a future migration path, not the current persistence mechanism.

### Frontend

- Server-served static HTML through FastAPI `FileResponse` and `StaticFiles`.
- Vanilla JavaScript uses `fetch`, `URLSearchParams`, `localStorage`, and DOM rendering.
- No frontend build step is required.
- Pages include login, user metrics, dashboard, manager, admin, Jira authentication, Jira assignments, and password reset.
- Jira assignments supports date filters, one Release / Fix Version filter, numeric cards, Jira search links, and expandable space counts.

### Dependencies

`fastapi==0.111.0`, `uvicorn[standard]`, `requests`, `python-dotenv==1.0.1`, `pydantic`, `sqlalchemy`, `python-jose[cryptography]`, `passlib[bcrypt]`, `bcrypt==3.2.2`, and `python-multipart`.

## 5. Application Workflows

### Authentication

Users register or log in through the authentication endpoints. A session token is stored by the browser and sent as `Authorization: Bearer <token>`. The backend resolves the token to a user ID, loads the user from JSON storage, and removes expired sessions. Sensitive fields are removed from normal user responses.

### Metric entry and review

Users enter configured metrics such as completed stories, valid defects, invalid defects, leaked P0 defects, complex stories, volunteer opportunities, and demo opportunities. Entries are timestamped and associated with the user. Managers review reportee data and dashboards compare values against role targets.

### Jira assignments

The assignments endpoint identifies the logged-in user email and queries Jira with the configured administrative PAT. The UI displays counts for Stories Assigned, Defects Assigned, Defects Reported, Bugs Assigned, Bugs Reported, Tests Assigned, Test Plans Assigned, and Test Executions Assigned.

## 6. Jira Integration and Query Rules

Every card has its own JQL query. The same query is used for the count, space breakdown, and Jira search link so the displayed number and drill-through result remain aligned.

All counts include these statuses:

- Completed
- Done
- Accepted
- Closed
- Released

The UI exposes one field named **Release / Fix Version**. Its value is applied only to Business Story queries because other issue types may not have that field populated:

```jql
"Release Version[Dropdown]" = "<value entered by the user>"
```

Defects use `issuetype = "Defect"`. Bugs use `issuetype = "Bug Task"`. Assigned cards use `assignee = "<user email>"`; reported cards use `reporter = "<user email>"`. Date filters remain available for all types.

Example Business Story query:

```jql
assignee = "user@example.com" AND issuetype = "Business Story" AND status IN ("Completed", "Done", "Accepted", "Closed", "Released") AND "Release Version[Dropdown]" = "NE.R.1.0.0"
```

Example Defect query:

```jql
assignee = "user@example.com" AND issuetype = "Defect" AND status IN ("Completed", "Done", "Accepted", "Closed", "Released")
```

## 7. API Surface

- `POST /api/auth/register` - create an account and session.
- `POST /api/auth/login` - authenticate a user.
- `POST /api/auth/logout` - delete the current session.
- `GET /api/auth/me` - return the authenticated profile.
- `POST /api/auth/forgot-password` and `POST /api/auth/reset-password` - password reset flow.
- `GET/POST /api/metrics` - read or create metric entries.
- `PATCH/DELETE /api/metrics/{id}` - update or delete an entry.
- `GET /api/metrics/team` - return manager team metrics.
- `GET /api/jira/assignments` - return filtered Jira counts, links, queries, and space breakdowns.
- Admin user endpoints - manage users and roles.

## 8. Data and Configuration

Current persistence is file-based and intended for a small local or pilot deployment. `data/users.json` stores user profiles and Jira connection metadata. `data/metrics.json` stores metric entries. `data/sessions.json` stores active sessions. Writes use a threading lock and startup migrations add missing fields to older user records.

Jira configuration is loaded from environment variables such as `JIRA_SERVER_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`. Secrets should never be committed to source control. The current Jira design uses one configured administrative PAT to query on behalf of users.

## 9. Security and Operations

- Use HTTPS and a production secret manager before external deployment.
- Replace the local password/session approach with a hardened identity provider or signed, rotated tokens for production.
- Avoid logging Jira tokens, reset tokens, or authorization headers.
- Restrict Jira query access so users can request only their own assignment data.
- Move JSON persistence to PostgreSQL for concurrency, backups, and reporting.
- Add automated tests for JQL construction, authorization, pagination, status filtering, and response-key consistency.

## 10. Current Design

The current design is compact and operational: role-specific navigation, card-based metric summaries, filters at the top of the Jira page, and progressive disclosure for space breakdowns. The primary Jira view is numeric, while each card can expand to show project-level counts. Search links provide an audit path back to Jira.

## 11. Next Steps and Vision

- Move persistence from JSON to PostgreSQL with migrations and backups.
- Add automated backend, API-contract, and browser tests in CI.
- Add Jira caching, rate-limit handling, timeout/retry policy, and clearer upstream errors.
- Move Jira issue types, statuses, and custom fields into validated configuration.
- Add trend charts, period comparisons, exportable reports, and manager summaries.
- Improve accessibility and add automated browser checks.
- Prepare containerized staging and production deployment.

## 12. Needs and Support

- Jira administrator confirmation of the Release Version field, issue types, statuses, and API permissions.
- Product-owner agreement on metric definitions, targets, periods, and visibility rules.
- Security review of authentication, secret storage, admin permissions, and the administrative PAT model.
- Infrastructure support for hosting, HTTPS, backups, monitoring, and a production database.
- Representative Jira data and named users for acceptance testing.

## 13. Repository Guide

| File/folder | Description |
|---|---|
| `app.py` | FastAPI application, pages, auth, metrics, startup bootstrap |
| `auth.py` | Session storage, password hashing and verification |
| `storage.py` | JSON persistence, migrations, users/reportees and metrics |
| `metrics_service.py` | Metric definitions, labels, and targets |
| `jira_service.py` | Jira client, JQL, counts, links, and space breakdowns |
| `jira_routes.py` | Jira assignments API route |
| `models.py` | Pydantic request models |
| `frontend/` | Static user, manager, admin, dashboard, and Jira pages |
| `data/` | Runtime JSON data files |
