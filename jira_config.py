import os
from dotenv import load_dotenv

load_dotenv()

JIRA_SERVER_URL = os.getenv("JIRA_SERVER_URL", "https://your-domain.atlassian.net")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")