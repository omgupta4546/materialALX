from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    
class UserResponse(BaseModel):
    user_id: str
    name: str
    role: Optional[str]
    cpse: Optional[str]
    permissions: List[str]
