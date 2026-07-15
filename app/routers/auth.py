from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import CurrentUser, get_current_user
from app.core.rate_limit import limiter
from app.repositories import platform_setting_repository, user_repository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    PublicPlatformSettingsResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/platform-settings", response_model=PublicPlatformSettingsResponse)
async def platform_settings(db: AsyncSession = Depends(get_db)) -> PublicPlatformSettingsResponse:
    setting = await platform_setting_repository.get(db)
    if setting is None:
        setting = await platform_setting_repository.create_default(db)
        await db.commit()
    return PublicPlatformSettingsResponse(supported_currencies=setting.supported_currencies)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    return await auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await auth_service.login(db, payload.matricule, payload.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await auth_service.refresh_tokens(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
    authorization: str | None = Header(default=None),
) -> None:
    # get_current_user a déjà validé le token (signature, expiration, non-révoqué) ; on
    # récupère la valeur brute ici pour en extraire le jti et le révoquer explicitement.
    access_token = (authorization or "").removeprefix("Bearer ")
    await auth_service.logout(db, access_token, payload.refresh_token)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> None:
    await auth_service.request_password_reset(db, payload.matricule)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def reset_password(
    request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> None:
    await auth_service.reset_password(db, payload.matricule, payload.otp_code, payload.new_password)


@router.get("/me", response_model=MeResponse)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MeResponse:
    user = await user_repository.get_by_id(db, current_user.id)
    assert user is not None
    return MeResponse(
        id=current_user.id,
        company_id=current_user.company_id,
        matricule=user.matricule,
        full_name=user.full_name,
        is_owner=current_user.is_owner,
        is_super_admin=current_user.is_super_admin,
        permissions=sorted(current_user.permissions),
    )
