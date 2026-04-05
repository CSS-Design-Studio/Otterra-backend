from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email_or_phone: str
    password: str

class TokenResponse(BaseModel):
    access_token : str
    refresh_token : str
    token_type : str = "bearer"

class OAuthCallBackRequest(BaseModel):
    provider: str # "google", "apple"
    id_token: str
    

