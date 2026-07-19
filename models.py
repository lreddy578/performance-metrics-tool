from pydantic import BaseModel
from typing  import Optional


class RegisterRequest(BaseModel):
    email:        str
    password:     str
    display_name: str
    role:         str = "SDET"


class LoginRequest(BaseModel):
    email:    str
    password: str


class Token(BaseModel):
    access_token: str
    token_type:   str
    user:         dict


class MetricInput(BaseModel):
    metric_name:  str
    actual_value: float
    year:         int
    comment:      str = ""


class UserUpdate(BaseModel):
    role:       Optional[str] = None
    is_manager: Optional[int] = None
    manager_id: Optional[int] = None