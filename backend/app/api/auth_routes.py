"""MindPulse Backend — Auth API Routes."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services import users
from app.core.auth import decode_access_token

router = APIRouter()
bearer_scheme = HTTPBearer()


class SignupRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class AuthResponse(BaseModel):
    user: dict
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    if len(req.password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters"
        )
    user = users.create_user(req.email, req.username, req.password, req.display_name)
    if not user:
        raise HTTPException(status_code=409, detail="Email or username already exists")
    token_data = users.login(req.email, req.password)
    if not token_data:
        raise HTTPException(status_code=500, detail="Signup succeeded but login failed")
    return AuthResponse(**token_data)


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    result = users.login(req.email_or_username, req.password)
    if not result:
        raise HTTPException(
            status_code=401, detail="Invalid email/username or password"
        )
    return AuthResponse(**result)


@router.get("/auth/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = int(payload.get("sub", 0))
    user = users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
