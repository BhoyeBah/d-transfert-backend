from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    return await auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await auth_service.login(
        db, payload.matricule, payload.phone, payload.password
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await auth_service.refresh_tokens(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> None:
    await auth_service.request_password_reset(db, payload.matricule, payload.phone)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> None:
    await auth_service.reset_password(
        db, payload.matricule, payload.phone, payload.otp_code, payload.new_password
    )
