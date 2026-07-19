# jira_auto = True  → shown in "Jira Metrics" section of Tab 1 (read-only)
# jira_auto = False → shown in "Manual Metrics" section of Tab 1 (editable)
# Tab 2 always shows ALL 7 metrics as editable

METRICS_CONFIG = {
    "SDET": [
        {
            "name":      "user_stories_completed",
            "label":     "Total User Stories Completed",
            "target":    40,
            "weightage": 45,
            "jira_auto": True,
        },
        {
            "name":      "valid_defects",
            "label":     "Total Valid Defects Identified",
            "target":    80,
            "weightage": 18,
            "jira_auto": True,
        },
        {
            "name":      "invalid_defects",
            "label":     "Total Invalid Defects Identified",
            "target":    5,
            "weightage": -2,
            "jira_auto": True,
        },
        {
            "name":      "p0_defects_leaked",
            "label":     "Defects Leaked to Production (P0 Hot Fix)",
            "target":    2,
            "weightage": -15,
            "jira_auto": True,
        },
        {
            "name":      "complex_stories",
            "label":     "Complex Stories (Points 8+)",
            "target":    12,
            "weightage": 10,
            "jira_auto": True,
        },
        {
            "name":      "volunteer_opportunities",
            "label":     "Total Voluntary Opportunities",
            "target":    5,
            "weightage": 5,
            "jira_auto": False,
        },
        {
            "name":      "demo_opportunities",
            "label":     "Total Demo Opportunities",
            "target":    12,
            "weightage": 5,
            "jira_auto": False,
        },
    ]
}