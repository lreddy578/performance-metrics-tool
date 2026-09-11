from pydantic import BaseModel
from typing  import Optional


class RegisterRequest(BaseModel):
    name:     str
    email:    str
    role:     str = "SDET"
    password: str
    manager_email: str = ""

class LoginRequest(BaseModel):
    email:    str
    password: str


class SetPasswordRequest(BaseModel):
    password: str


class UserCreate(BaseModel):
    name:     str
    email:    str
    role:     str = "SDET"
    password: str
    manager_email: str = ""


class UserUpdate(BaseModel):
    name:     str
    email:    str
    role:     str
    password: Optional[str] = None
    manager_email: str = ""


class JiraAuthRequest(BaseModel):
    jira_url:       str
    jira_email:     str
    jira_api_token: str


class MetricEntryCreate(BaseModel):
    user_stories_completed:  Optional[float] = None
    valid_defects:           Optional[float] = None
    invalid_defects:         Optional[float] = None
    p0_defects_leaked:       Optional[float] = None
    complex_stories:         Optional[float] = None
    volunteer_opportunities: Optional[float] = None
    demo_opportunities:      Optional[float] = None
    notes:                   str = ""

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetWithTokenRequest(BaseModel):
    token: str
    password: str