import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()


def get_jira_client() -> requests.Session:
    """Create a Jira session using the shared service account from .env"""
    jira_url  = os.getenv("JIRA_URL")
    email     = os.getenv("JIRA_SERVICE_EMAIL")
    api_token = os.getenv("JIRA_SERVICE_TOKEN")

    if not all([jira_url, email, api_token]):
        raise EnvironmentError(
            "Missing Jira config. Set JIRA_URL, JIRA_SERVICE_EMAIL, "
            "JIRA_SERVICE_TOKEN in your .env file."
        )

    session = requests.Session()
    session.auth = HTTPBasicAuth(email, api_token)   # type: ignore
    session.headers.update({
        "Accept":       "application/json",
        "Content-Type": "application/json",
    })
    return session