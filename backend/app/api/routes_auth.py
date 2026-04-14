"""
POST /api/auth/register — 注册
POST /api/auth/login    — 登录，返回 JWT
GET  /api/auth/me       — 当前用户信息（需要 token）
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.db.repositories import user as user_repo
from app.services.auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    pool = request.app.state.db_pool
    user = await user_repo.create_user(
        email=body.email,
        password_hash=hash_password(body.password),
        pool=pool,
    )
    if user is None:
        raise HTTPException(status_code=409, detail="Email already registered.")

    token = create_access_token(user["id"])
    return {"token": token, "user_id": user["id"], "email": user["email"]}


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    pool = request.app.state.db_pool
    user = await user_repo.get_user_by_email(body.email, pool)

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user["id"])
    return {"token": token, "user_id": user["id"], "email": user["email"]}


@router.get("/me")
async def me(request: Request, user_id: str = Depends(get_current_user_id)):
    pool = request.app.state.db_pool
    user = await user_repo.get_user_by_id(user_id, pool)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user_id": user["id"], "email": user["email"]}
