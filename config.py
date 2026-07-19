import os
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Validate required config
if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
    raise EnvironmentError("Missing one or more required environment variables: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN")