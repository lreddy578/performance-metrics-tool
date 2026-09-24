# Achiever's Scorecard
## Objective, Current Design, Vision and Support

### Slide 1: Title
Achiever's Scorecard
Project overview | September 2026

### Slide 2: Objective and Goal
- Create one practical workspace for SDET performance metrics and Jira work visibility.
- Reduce manual reporting with user-specific assigned and reported counts.
- Give contributors, managers and administrators role-appropriate views.
- Keep the solution simple now while establishing a path to production scale.

### Slide 3: Current Design
- FastAPI backend with modular auth, metrics, storage and Jira services.
- Static HTML/CSS/JavaScript frontend with no build step.
- JSON files currently store users, sessions and metric entries.
- Role-aware pages: user, manager, dashboard, admin and Jira assignments.

### Slide 4: Jira Experience Today
- Numeric cards for stories, defects, bugs, tests, test plans and test executions.
- Counts include Completed, Done, Accepted, Closed and Released statuses.
- Business Stories use the Release Version[Dropdown] filter; other types do not require it.
- Each card has a matching Jira search link and expandable counts by space.

### Slide 5: Next Steps and Vision
- Move persistence from JSON to PostgreSQL with migrations and backups.
- Add automated backend, API-contract and browser tests in CI.
- Add Jira caching, retry/timeout handling and configurable field/status mappings.
- Expand into trend reporting, exports, comparisons and production deployment.

### Slide 6: Needs and Support
- Jira admin: confirm field IDs, issue types, statuses and API permissions.
- Product: finalize metric definitions, targets, periods and visibility rules.
- Security: review secrets, admin controls and the Jira PAT model.
- Infrastructure: provide hosting, HTTPS, database, backups and monitoring.
- Users: provide representative data and acceptance-test participants.

### Slide 7: Success Measures
- Users can validate Jira counts directly from the application.
- Managers spend less time assembling recurring performance reports.
- Metric and Jira data are consistent, auditable and easy to explain.
- The application can scale from pilot usage to a supported production service.
