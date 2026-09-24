SDET_ROLE = "SDET"
QA_LEAD_ROLE = "QA Lead"

ROLE_METRICS_CONFIG = {
    SDET_ROLE: [
        {"name": "user_stories_completed", "label": "User Stories / Tasks / Tests / Test Plans Completed", "target": 40, "weightage": 45},
        {"name": "valid_defects", "label": "Valid Defects Identified", "target": 80, "weightage": 18},
        {"name": "invalid_defects", "label": "Invalid Defects Identified", "target": 5, "weightage": -2},
        {"name": "volunteer_opportunities", "label": "Voluntary Opportunities", "target": 5, "weightage": 5},
        {"name": "p0_defects_leaked", "label": "P0 Defects Leaked to Production (Hot Fix)", "target": 2, "weightage": -15},
        {"name": "complex_stories", "label": "Complex Stories (More Than One Component)", "target": 12, "weightage": 10},
        {"name": "demo_opportunities", "label": "Demo Opportunities", "target": 12, "weightage": 5},
    ],
    QA_LEAD_ROLE: [
        {"name": "user_stories_completed", "label": "User Stories / Tasks / Tests / Test Plans Completed", "target": 45, "weightage": 35},
        {"name": "valid_defects", "label": "Valid Defects Identified", "target": 95, "weightage": 13},
        {"name": "invalid_defects", "label": "Invalid Defects Identified", "target": 3, "weightage": -2},
        {"name": "initiatives_proposed", "label": "Initiatives Proposed for Problem Solving", "target": 4, "weightage": 10},
        {"name": "p0_defects_leaked", "label": "P0 Defects Leaked to Production (Hot Fix)", "target": 1, "weightage": -25},
        {"name": "complex_stories", "label": "Complex Stories (More Than Two Components)", "target": 12, "weightage": 10},
        {"name": "demo_opportunities", "label": "Demo Opportunities", "target": 20, "weightage": 5},
    ],
}

def get_metrics_for_role(role: str) -> list[dict]:
    """Return the scorecard for a role, defaulting legacy roles to SDET."""
    return ROLE_METRICS_CONFIG.get(role, ROLE_METRICS_CONFIG[SDET_ROLE])
