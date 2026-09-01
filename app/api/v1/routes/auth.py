from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    UserPublic,
    UserVerification,
    TokenResponse,
    TokenPayload,
)
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    """Créer un compte (touriste, guide ou prestataire)."""
    return await user_service.register_user(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Connexion par email et mot de passe."""
    return await user_service.login_user(data)


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: TokenPayload = Depends(get_current_user)):
    """Profil de l'utilisateur connecté."""
    return await user_service.get_user_by_id(current_user.sub)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UpdateProfileRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Mettre à jour son profil."""
    return await user_service.update_profile(current_user.sub, data)


@router.get("/verify/{user_id}", response_model=UserVerification)
async def verify_card(user_id: str):
    """Vérification publique d'une carte FasoViva à partir du QR code (sans authentification)."""
    return await user_service.verify_user_card(user_id)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Changer son mot de passe."""
    await user_service.change_password(current_user.sub, data.current_password, data.new_password)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: TokenPayload = Depends(get_current_user)):
    """Supprimer son compte (§47 Confidentialité et gouvernance des données)."""
    await user_service.delete_account(current_user.sub)
