$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$docPath = Join-Path $root 'Performance_Metrics_Tool_Technology_Document.docx'
$pptPath = Join-Path $root 'Performance_Metrics_Tool_Overview.pptx'

function Add-WordText($doc, [string]$text, [object]$style = 'Normal') {
    $p = $doc.Paragraphs.Add()
    $p.Style = $style
    $p.Range.Text = $text
    $p.Range.InsertParagraphAfter()
}
function Add-WordHeading($doc, [string]$text, [int]$level = 1) {
    $style = if ($level -eq 1) { 'Heading 1' } elseif ($level -eq 2) { 'Heading 2' } else { 'Heading 3' }
    Add-WordText $doc $text $style
}
function Add-WordBullet($doc, [string]$text) {
    $p = $doc.Paragraphs.Add()
    $p.Style = 'List Bullet'
    $p.Range.Text = $text
    $p.Range.InsertParagraphAfter()
}
function Add-WordTable($doc, [string[]]$headers, [object[][]]$rows) {
    $table = $doc.Tables.Add($doc.Paragraphs.Add().Range, $rows.Count + 1, $headers.Count)
    $table.Style = 'Table Grid'
    for ($c = 0; $c -lt $headers.Count; $c++) { $table.Cell(1, $c + 1).Range.Text = $headers[$c] }
    for ($r = 0; $r -lt $rows.Count; $r++) {
        for ($c = 0; $c -lt $headers.Count; $c++) { $table.Cell($r + 2, $c + 1).Range.Text = [string]$rows[$r][$c] }
    }
    $doc.Paragraphs.Add() | Out-Null
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Add()

$title = $doc.Paragraphs.Add()
$title.Range.Text = "Achiever's Scorecard"
$title.Range.Style = 'Title'
$title.Range.InsertParagraphAfter()
$subtitle = $doc.Paragraphs.Add()
$subtitle.Range.Text = 'Technology and Solution Design Document'
$subtitle.Range.Style = 'Subtitle'
$subtitle.Range.InsertParagraphAfter()
Add-WordText $doc 'Prepared: September 2026'
Add-WordText $doc 'Purpose: Provide a complete technical reference for the current application, its Jira integration, operating model, and future direction.'

Add-WordHeading $doc '1. Executive Summary'
Add-WordText $doc "Achiever's Scorecard is a lightweight web application for collecting and reviewing SDET performance metrics. It combines a FastAPI backend, browser-based HTML/CSS/JavaScript pages, JSON file persistence, bearer-token sessions, role-aware views, and Jira assignment metrics."
Add-WordText $doc 'The current Jira experience presents numeric counts for stories, defects, bugs, tests, test plans, and test executions. Each card has a Jira search link and an expandable count by project/space. Counts are restricted to Completed, Done, Accepted, Closed, and Released statuses.'

Add-WordHeading $doc '2. Objective and Goals'
Add-WordBullet $doc 'Create a single, accessible place for individual contributors, managers, and administrators to record and review performance data.'
Add-WordBullet $doc 'Reduce manual Jira reporting by calculating user-specific assigned and reported work counts.'
Add-WordBullet $doc 'Give managers visibility into team metrics and reportee relationships.'
Add-WordBullet $doc 'Keep the initial solution simple to run locally and easy to evolve toward production infrastructure.'
Add-WordBullet $doc 'Provide traceable Jira search links so users can validate the numbers against Jira.'

Add-WordHeading $doc '3. Current Architecture'
Add-WordText $doc 'The system follows a small modular service architecture. FastAPI owns HTTP routing and dependency injection. Domain services hold metrics and Jira logic. Storage provides a JSON-backed persistence boundary. Static frontend pages call the API using JavaScript and browser local storage for the session token.'
Add-WordTable $doc @('Layer','Current implementation','Responsibility') @(
    @('Presentation','Static HTML, CSS, JavaScript','Login, metric entry, dashboards, administration, Jira cards and filters'),
    @('API','FastAPI 0.111.0','Routes, request validation, authentication dependencies, JSON responses'),
    @('Business services','metrics_service.py, jira_service.py','Metric configuration, Jira JQL construction, counts, search links, space aggregation'),
    @('Persistence','storage.py and data/*.json','Users, metric entries, sessions, migrations, CRUD operations'),
    @('Authentication','auth.py','Password hashing, bearer session creation, expiration, deletion'),
    @('External integration','Jira REST API v3 via requests','Issue counts, project/space aggregation, Jira search URLs')
)

Add-WordHeading $doc '4. Technology Details'
Add-WordHeading $doc '4.1 Backend', 2
Add-WordBullet $doc 'Python 3.13.9 environment is currently used.'
Add-WordBullet $doc 'FastAPI provides the application and API framework.'
Add-WordBullet $doc 'Uvicorn runs the application locally with: uvicorn app:app --reload.'
Add-WordBullet $doc 'Pydantic models validate registration, login, password, Jira authentication, and metric-entry payloads.'
Add-WordBullet $doc 'python-dotenv loads environment configuration from .env.'
Add-WordBullet $doc 'requests performs outbound Jira REST calls.'
Add-WordBullet $doc 'SQLAlchemy and database drivers are listed as future-ready dependencies but are not the current persistence path.'
Add-WordHeading $doc '4.2 Frontend', 2
Add-WordBullet $doc 'The frontend is server-served static HTML through FastAPI FileResponse and StaticFiles.'
Add-WordBullet $doc 'Pages include login, user metrics, dashboard, manager, admin, Jira authentication, Jira assignments, and password reset.'
Add-WordBullet $doc 'Vanilla JavaScript uses fetch, URLSearchParams, localStorage, and DOM rendering; no frontend build step is required.'
Add-WordBullet $doc 'The Jira assignments page supports release/date filters, numeric cards, Jira search links, and expandable space-level counts.'
Add-WordHeading $doc '4.3 Dependencies', 2
Add-WordTable $doc @('Package','Role') @(
    @('fastapi','Web framework and API routing'),
    @('uvicorn[standard]','ASGI development/runtime server'),
    @('requests','Jira REST API client'),
    @('python-dotenv','Environment variable loading'),
    @('pydantic','Request and data validation'),
    @('python-jose[cryptography]','Available JWT-related dependency'),
    @('passlib[bcrypt], bcrypt','Available password-security dependencies'),
    @('python-multipart','Form/multipart support'),
    @('sqlalchemy, psycopg2-binary','Database migration path; not current JSON storage')
)

Add-WordHeading $doc '5. Application Workflows'
Add-WordHeading $doc '5.1 Authentication', 2
Add-WordText $doc 'Users register or log in through the authentication endpoints. A session token is stored by the browser and sent as Authorization: Bearer <token>. The backend resolves the token to a user ID, loads the user from JSON storage, and removes expired sessions. Sensitive fields are removed from normal user responses.'
Add-WordHeading $doc '5.2 Metric entry and review', 2
Add-WordText $doc 'Users enter configured metrics such as completed stories, valid defects, invalid defects, leaked P0 defects, complex stories, volunteer opportunities, and demo opportunities. Entries are timestamped and associated with the user. Managers review reportee data and dashboards compare values against role targets.'
Add-WordHeading $doc '5.3 Jira assignments', 2
Add-WordText $doc 'The assignments endpoint authenticates the app session, identifies the logged-in user email, and queries Jira with an administrative PAT configured through environment variables. The UI displays counts for Stories Assigned, Defects Assigned, Defects Reported, Bugs Assigned, Bugs Reported, Tests Assigned, Test Plans Assigned, and Test Executions Assigned.'

Add-WordHeading $doc '6. Jira Integration and Query Rules'
Add-WordText $doc 'The Jira service builds a separate JQL query for each card and reuses that query for the count, the space breakdown, and the Jira search link. This keeps the displayed number and the drill-through search aligned.'
Add-WordHeading $doc '6.1 Status rule', 2
Add-WordText $doc 'Every assignment count is restricted to the following statuses:'
Add-WordBullet $doc 'Completed'
Add-WordBullet $doc 'Done'
Add-WordBullet $doc 'Accepted'
Add-WordBullet $doc 'Closed'
Add-WordBullet $doc 'Released'
Add-WordHeading $doc '6.2 Release / Fix Version filter', 2
Add-WordText $doc 'The UI exposes one field named Release / Fix Version. Its value is interpreted as the Jira custom field below and is applied only to Business Story queries because the other issue types may not have this field populated:'
Add-WordText $doc '"Release Version[Dropdown]" = "<value entered by the user>"'
Add-WordText $doc 'Defects use issuetype = "Defect". Bugs use issuetype = "Bug Task". Reported cards use reporter = "<user email>"; assigned cards use assignee = "<user email>". Date filters remain available for all types.'
Add-WordHeading $doc '6.3 Example queries', 2
Add-WordText $doc 'Business Story assigned count:'
Add-WordText $doc 'assignee = "user@example.com" AND issuetype = "Business Story" AND status IN ("Completed", "Done", "Accepted", "Closed", "Released") AND "Release Version[Dropdown]" = "NE.R.1.0.0"'
Add-WordText $doc 'Defect assigned count:'
Add-WordText $doc 'assignee = "user@example.com" AND issuetype = "Defect" AND status IN ("Completed", "Done", "Accepted", "Closed", "Released")'

Add-WordHeading $doc '7. API Surface'
Add-WordTable $doc @('Endpoint','Method','Purpose') @(
    @('/api/auth/register','POST','Create an account and session'),
    @('/api/auth/login','POST','Authenticate a user'),
    @('/api/auth/logout','POST','Delete the current session'),
    @('/api/auth/me','GET','Return the authenticated user profile'),
    @('/api/auth/forgot-password','POST','Generate a one-time reset link'),
    @('/api/auth/reset-password','POST','Reset a password with a token'),
    @('/api/metrics','GET/POST','Read or create metric entries'),
    @('/api/metrics/{id}','PATCH/DELETE','Update or delete a metric entry'),
    @('/api/metrics/team','GET','Return manager team metrics'),
    @('/api/jira/assignments','GET','Return filtered Jira counts, links, and space breakdowns'),
    @('/admin/users','GET/PATCH/DELETE','Admin user management')
)

Add-WordHeading $doc '8. Data and Configuration'
Add-WordText $doc 'Current persistence is file-based and intended for a small local or pilot deployment. data/users.json stores user profiles and Jira connection metadata. data/metrics.json stores metric entries. data/sessions.json stores active sessions. Writes are protected by a threading lock and JSON migrations add missing fields to older user records.'
Add-WordText $doc 'Jira configuration is loaded from environment variables such as JIRA_SERVER_URL, JIRA_EMAIL, and JIRA_API_TOKEN. Secrets should not be committed to source control. The current Jira design uses one configured administrative PAT to query on behalf of users.'

Add-WordHeading $doc '9. Security and Operational Considerations'
Add-WordBullet $doc 'Use HTTPS and a production-grade secret manager before external deployment.'
Add-WordBullet $doc 'Replace the simple local password/session approach with a hardened identity provider or signed, rotated tokens for production.'
Add-WordBullet $doc 'Avoid logging Jira tokens, reset tokens, or raw authorization headers.'
Add-WordBullet $doc 'Restrict Jira query access and validate that users can request only their own assignment data.'
Add-WordBullet $doc 'Move JSON persistence to PostgreSQL or another transactional database for concurrent users, backups, and reporting.'
Add-WordBullet $doc 'Add automated tests for JQL construction, authorization, pagination, status filtering, and response-key consistency.'

Add-WordHeading $doc '10. Current Design and User Experience'
Add-WordText $doc 'The current design is intentionally compact and operational: role-specific navigation, card-based metric summaries, filters at the top of the Jira page, and progressive disclosure for space breakdowns. The Jira page keeps the primary view numeric while allowing users to expand a card when they need project-level detail. Search links provide an audit path back to Jira.'

Add-WordHeading $doc '11. Next Steps and Vision'
Add-WordBullet $doc 'Introduce a real database and migrations while preserving the service interfaces.'
Add-WordBullet $doc 'Add automated tests and CI checks for backend behavior and frontend contract keys.'
Add-WordBullet $doc 'Add Jira request caching, rate-limit handling, timeout/retry policy, and clearer upstream error messages.'
Add-WordBullet $doc 'Move Jira issue type names, status mappings, and custom field identifiers into validated configuration.'
Add-WordBullet $doc 'Add trend charts, period comparisons, exportable reports, and manager-level summaries.'
Add-WordBullet $doc 'Improve accessibility with keyboard-complete controls, semantic landmarks, and automated browser checks.'
Add-WordBullet $doc 'Prepare containerized deployment and environment-specific configuration for staging and production.'

Add-WordHeading $doc '12. Needs and Support Required'
Add-WordBullet $doc 'Jira administrator confirmation of the Release Version[Dropdown] field, issue-type names, status names, and API permissions.'
Add-WordBullet $doc 'Product-owner agreement on metric definitions, targets, reporting periods, and manager visibility rules.'
Add-WordBullet $doc 'Security review of authentication, secret storage, admin permissions, and the administrative Jira PAT model.'
Add-WordBullet $doc 'Infrastructure support for hosting, HTTPS, backups, monitoring, and a production database.'
Add-WordBullet $doc 'Representative Jira test data and named users for acceptance testing.'

Add-WordHeading $doc '13. Repository Guide'
Add-WordTable $doc @('File/Folder','Description') @(
    @('app.py','FastAPI application, pages, auth endpoints, metric endpoints, startup bootstrap'),
    @('auth.py','Session storage, password hashing and verification'),
    @('storage.py','JSON persistence, migrations, user/reportee and metric operations'),
    @('metrics_service.py','Metric definitions, labels and targets'),
    @('jira_service.py','Jira API client, JQL, counts, links and space breakdowns'),
    @('jira_routes.py','Jira assignments API route'),
    @('models.py','Pydantic request models'),
    @('frontend/','Static user, manager, admin, dashboard and Jira pages'),
    @('data/','Runtime JSON data files')
)
Add-WordText $doc 'End of document.'
$doc.SaveAs2($docPath, 16)
$doc.Close()
$word.Quit()

function Set-PptText($shape, [string]$text, [int]$fontSize = 22, [bool]$bold = $false) {
    $shape.TextFrame.TextRange.Text = $text
    $shape.TextFrame.TextRange.Font.Size = $fontSize
    $shape.TextFrame.TextRange.Font.Name = 'Aptos'
    $shape.TextFrame.TextRange.Font.Bold = $bold
    $shape.TextFrame.MarginLeft = 14
    $shape.TextFrame.MarginRight = 14
    $shape.TextFrame.MarginTop = 8
    $shape.TextFrame.MarginBottom = 8
}
function Add-PptSlide($presentation, [string]$title, [string[]]$bullets, [string]$accent = '1F4E79') {
    $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, 12)
    $bg = $slide.Shapes.AddShape(1, 0, 0, 960, 540)
    $bg.Fill.ForeColor.RGB = 0xF5F7FA
    $bg.Line.Visible = 0
    $bar = $slide.Shapes.AddShape(1, 0, 0, 960, 72)
    $bar.Fill.ForeColor.RGB = [Convert]::ToInt32($accent, 16)
    $bar.Line.Visible = 0
    $titleShape = $slide.Shapes.AddTextbox(1, 26, 14, 900, 45)
    Set-PptText $titleShape $title 28 $true
    $titleShape.TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
    $body = $slide.Shapes.AddTextbox(1, 48, 105, 860, 370)
    $body.TextFrame.TextRange.Text = (($bullets | ForEach-Object { "• $_" }) -join "`r`n")
    $body.TextFrame.TextRange.Font.Name = 'Aptos'
    $body.TextFrame.TextRange.Font.Size = 22
    $body.TextFrame.TextRange.Font.Color.RGB = 0x172B4D
    $body.TextFrame.WordWrap = -1
    $body.TextFrame.MarginLeft = 8
    $body.TextFrame.MarginRight = 8
    return $slide
}

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = $true
$presentation = $ppt.Presentations.Add()
$presentation.PageSetup.SlideWidth = 960
$presentation.PageSetup.SlideHeight = 540
$slide = $presentation.Slides.Add(1, 12)
$bg = $slide.Shapes.AddShape(1, 0, 0, 960, 540)
$bg.Fill.ForeColor.RGB = 0xF5F7FA
$bg.Line.Visible = 0
$band = $slide.Shapes.AddShape(1, 0, 0, 960, 540)
$band.Fill.ForeColor.RGB = 0x1F4E79
$band.Fill.Transparency = 0.04
$band.Line.Visible = 0
$main = $slide.Shapes.AddTextbox(1, 65, 130, 820, 100)
Set-PptText $main "Achiever's Scorecard" 40 $true
$main.TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
$sub = $slide.Shapes.AddTextbox(1, 68, 250, 780, 100)
Set-PptText $sub 'Objective, current design, vision and support needed' 25 $false
$sub.TextFrame.TextRange.Font.Color.RGB = 0xE8F1F8
$foot = $slide.Shapes.AddTextbox(1, 68, 440, 780, 40)
Set-PptText $foot 'Project overview | September 2026' 16 $false
$foot.TextFrame.TextRange.Font.Color.RGB = 0xD6E5F0

Add-PptSlide $presentation '1. Objective and Goal' @(
    'Create one practical workspace for SDET performance metrics and Jira work visibility.',
    'Reduce manual reporting by returning user-specific assigned and reported counts.',
    'Give contributors, managers and administrators role-appropriate views.',
    'Keep the solution simple to operate now while establishing a path to production scale.'
) | Out-Null
Add-PptSlide $presentation '2. Current Design' @(
    'FastAPI backend with modular auth, metrics, storage and Jira services.',
    'Static HTML/CSS/JavaScript frontend with no build step.',
    'JSON files currently store users, sessions and metric entries.',
    'Role-aware pages: user, manager, dashboard, admin and Jira assignments.'
) | Out-Null
Add-PptSlide $presentation '3. Jira Experience Today' @(
    'Numeric cards for stories, defects, bugs, tests, test plans and test executions.',
    'Counts include Completed, Done, Accepted, Closed and Released statuses.',
    'Business Stories use the Release Version[Dropdown] filter; other types do not require it.',
    'Each card has a matching Jira search link and expandable counts by space.'
) | Out-Null
Add-PptSlide $presentation '4. Next Steps and Vision' @(
    'Move persistence from JSON to PostgreSQL with migrations and backups.',
    'Add automated backend, API-contract and browser tests in CI.',
    'Add Jira caching, retry/timeout handling and configurable field/status mappings.',
    'Expand into trend reporting, exports, comparisons and production deployment.'
) | Out-Null
Add-PptSlide $presentation '5. Needs and Support' @(
    'Jira admin: confirm field IDs, issue types, statuses and API permissions.',
    'Product: finalize metric definitions, targets, periods and visibility rules.',
    'Security: review secrets, admin controls and the Jira PAT model.',
    'Infrastructure: provide hosting, HTTPS, database, backups and monitoring.',
    'Users: provide representative data and acceptance-test participants.'
) | Out-Null
Add-PptSlide $presentation '6. Success Measures' @(
    'Users can validate their Jira counts directly from the application.',
    'Managers spend less time assembling recurring performance reports.',
    'Metric and Jira data are consistent, auditable and easy to explain.',
    'The application can scale from pilot usage to a supported production service.'
) | Out-Null
$presentation.SaveAs($pptPath)
$presentation.Close()
$ppt.Quit()
Write-Output "Created: $docPath"
Write-Output "Created: $pptPath"
