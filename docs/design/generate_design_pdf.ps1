$ErrorActionPreference = 'Stop'

$designDir = Split-Path -Parent $PSCommandPath
$pdfPath = Join-Path $designDir 'Performance_Metrics_Tool_Design_Document.pdf'
$docxPath = Join-Path $designDir 'Performance_Metrics_Tool_Design_Document.docx'
$screenshotsDir = Join-Path $designDir 'screenshots'

function Add-Paragraph($document, [string]$text, [string]$style = 'Normal') {
    $paragraph = $document.Paragraphs.Add()
    $paragraph.Range.Style = $style
    $paragraph.Range.Text = $text
    $paragraph.Range.InsertParagraphAfter()
}

function Add-Heading($document, [string]$text, [int]$level = 1) {
    $style = if ($level -eq 1) { 'Heading 1' } else { 'Heading 2' }
    Add-Paragraph $document $text $style
}

function Add-Bullet($document, [string]$text) {
    $paragraph = $document.Paragraphs.Add()
    $paragraph.Range.Style = 'List Bullet'
    $paragraph.Range.Text = $text
    $paragraph.Range.InsertParagraphAfter()
}

function Add-Screenshot($document, [string]$path, [string]$caption) {
    if (-not (Test-Path $path)) { return }
    $range = $document.Paragraphs.Add().Range
    $picture = $range.InlineShapes.AddPicture($path, $false, $true)
    if ($picture.Width -gt 480) {
        $ratio = 480 / $picture.Width
        $picture.Width = 480
        $picture.Height = $picture.Height * $ratio
    }
    $range.InsertParagraphAfter()
    Add-Paragraph $document $caption 'Caption'
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$document = $word.Documents.Add()

try {
    $document.PageSetup.TopMargin = 54
    $document.PageSetup.BottomMargin = 54
    $document.PageSetup.LeftMargin = 54
    $document.PageSetup.RightMargin = 54

    Add-Paragraph $document "Achiever's Scorecard" 'Title'
    Add-Paragraph $document 'Design Document' 'Subtitle'
    Add-Paragraph $document 'Updated: September 23, 2026'
    Add-Paragraph $document 'This document describes the current architecture, access model, metric storage design, and captured user workflows.'

    Add-Heading $document '1. Architecture and Roles'
    Add-Paragraph $document 'The application is a FastAPI service with static HTML and JavaScript pages. storage.py provides a JSON persistence boundary for users, sessions, and metrics. The frontend calls authenticated API endpoints with a bearer session token.'
    Add-Bullet $document 'All logged-in users can manage only their own metric entries and view their own Jira assignments.'
    Add-Bullet $document 'Managers can use the Dashboard to view reportees derived from the manager_email relationship.'
    Add-Bullet $document 'Configured super-viewers can use the Dashboard to view all other users.'
    Add-Bullet $document 'The Dashboard navigation link is hidden for standard users and is shown only to Managers and super-viewers.'
    Add-Bullet $document 'The API remains the authorization authority: a hidden browser control does not grant access.'

    Add-Heading $document '2. Metric Data Model'
    Add-Paragraph $document 'User profiles are stored in data/users.json. Metrics are stored separately in data/metrics.json using entries_by_user. The outer key is the user ID and the inner key is the globally assigned metric entry ID.'
    Add-Paragraph $document 'Example path: entries_by_user["2"]["5"] represents entry 5 owned by user 2. Each entry also retains user_id as an explicit ownership reference.'
    Add-Bullet $document 'Get user entries: direct read from entries_by_user[user_id].'
    Add-Bullet $document 'Get, update, or delete one entry: direct access using (user_id, entry_id).'
    Add-Bullet $document 'Delete a user: remove the user record and that user bucket of metrics.'
    Add-Bullet $document 'Startup migration converts the prior flat entries structure to entries_by_user when required.'

    Add-Heading $document '3. DynamoDB Migration Path'
    Add-Paragraph $document 'For DynamoDB, store one metric entry per item rather than embedding all entries in one user item. Use user_id as the partition key and entry_id or timestamp as the sort key. This retains efficient per-user queries and direct access to a single entry.'

    Add-Heading $document '4. API and Access Contract'
    Add-Bullet $document 'GET /api/auth/me returns the sanitized user profile, entry_count, and server-derived is_super_viewer.'
    Add-Bullet $document 'GET /api/metrics/{user_id} permits self access, Manager access to reportees, and super-viewer access to any user.'
    Add-Bullet $document 'POST, PUT, and DELETE metric routes permit a user to change only their own entries.'
    Add-Bullet $document 'The Admin panel remains protected by the ADMIN_EMAIL rule.'

    Add-Heading $document '5. Current UI Screenshots'
    $screenshots = @(
        @('00-login.png', 'Figure 1. Sign in and sign up.'),
        @('01-user-mydata-empty.png', 'Figure 2. My Data empty state.'),
        @('02-user-add-metrics-form.png', 'Figure 3. Add metrics form.'),
        @('03-user-mydata-entries.png', 'Figure 4. User metric entries.'),
        @('04-user-jira-assignments.png', 'Figure 5. Jira assignments.'),
        @('05-manager-dashboard-placeholder.png', 'Figure 6. Manager Dashboard placeholder.'),
        @('06-manager-dashboard-full.png', 'Figure 7. Manager Dashboard with reportee data.'),
        @('07-manager-dashboard-collapsed.png', 'Figure 8. Collapsed Dashboard sections.'),
        @('08-manager-weightage-calculator.png', 'Figure 9. Weightage calculator.'),
        @('09-admin-panel.png', 'Figure 10. Admin panel.'),
        @('10-admin-add-user-modal.png', 'Figure 11. Add user dialog.'),
        @('11-manager-jira-show-by-space.png', 'Figure 12. Jira space breakdown.'),
        @('12-jira-auth.png', 'Figure 13. Jira authentication.'),
        @('13-reset-password.png', 'Figure 14. Password reset.'),
        @('14-user-dashboard-hidden.png', 'Figure 15. Latest standard-user view: Dashboard navigation is hidden.')
    )
    foreach ($shot in $screenshots) {
        Add-Screenshot $document (Join-Path $screenshotsDir $shot[0]) $shot[1]
    }

    Add-Heading $document '6. Operational Notes'
    Add-Bullet $document 'JSON persistence is suitable for local development and small pilot use. Use a managed database for concurrent production workloads, backups, and reporting.'
    Add-Bullet $document 'Do not commit Jira tokens, password hashes, or reset tokens.'
    Add-Bullet $document 'Keep SUPER_VIEWERS and ADMIN_EMAIL under controlled configuration as the access model evolves.'

    $document.SaveAs2($docxPath, 16)
    $document.ExportAsFixedFormat($pdfPath, 17)
    Write-Output "Created: $pdfPath"
}
finally {
    $document.Close()
    $word.Quit()
}