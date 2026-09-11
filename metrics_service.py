METRICS_CONFIG = [
    {
        "name":     "user_stories_completed",
        "label":    "User Stories Completed",
        "target":   40,
    },
    {
        "name":     "valid_defects",
        "label":    "Valid Defects Identified",
        "target":   80,
    },
    {
        "name":     "invalid_defects",
        "label":    "Invalid Defects Identified",
        "target":   5,
    },
    {
        "name":     "p0_defects_leaked",
        "label":    "P0 Defects Leaked to Production",
        "target":   2,
    },
    {
        "name":     "complex_stories",
        "label":    "Complex Stories (8+ Points)",
        "target":   12,
    },
    {
        "name":     "volunteer_opportunities",
        "label":    "Volunteer Opportunities",
        "target":   5,
    },
    {
        "name":     "demo_opportunities",
        "label":    "Demo Opportunities",
        "target":   12,
    },
]

METRIC_NAMES = [m["name"] for m in METRICS_CONFIG]