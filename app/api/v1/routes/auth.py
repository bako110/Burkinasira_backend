from fastapi import APIRouter, BackgroundTasks, Depends, status
from app.core.security import get_current_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
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
async def register(data: RegisterRequest, background_tasks: BackgroundTasks):
    """Créer un compte (touriste, guide ou prestataire).

    Un email de bienvenue est envoyé en arrière-plan ; son échec éventuel
    n'empêche pas la création du compte."""
    return await user_service.register_user(data, background_tasks)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Connexion par email et mot de passe."""
    return await user_service.login_user(data)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Demander un lien de réinitialisation de mot de passe par email.

    Renvoie toujours 202, que l'email existe ou non (pas d'énumération de comptes).
    """
    await user_service.request_password_reset(data.email, background_tasks)
    return {"message": "Si un compte existe pour cette adresse, un email a été envoyé."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordRequest):
    """Définir un nouveau mot de passe à partir du token reçu par email."""
    await user_service.reset_password(data.token, data.new_password)


@router.post("/google", response_model=TokenResponse)
async def login_google(data: GoogleLoginRequest):
    """Connexion / inscription via un `id_token` Google (Sign in with Google).

    Le client (web ou app) obtient le `id_token` auprès de Google puis l'envoie
    ici. Le serveur en vérifie la signature contre les clés publiques Google,
    puis retrouve ou crée le compte et renvoie un access token BurkinaSira.
    Renvoie 503 tant que `GOOGLE_CLIENT_IDS` n'est pas configuré.
    """
    return await user_service.login_with_google(data)


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


@router.get("/card-token")
async def get_card_token(current_user: TokenPayload = Depends(get_current_user)):
    """Token opaque à encoder dans le QR code de sa propre carte BurkinaSira."""
    return {"card_token": await user_service.get_or_create_card_token(current_user.sub)}


@router.get("/verify/{card_token}", response_model=UserVerification)
async def verify_card(card_token: str):
    """Vérification publique d'une carte BurkinaSira à partir du QR code (sans authentification)."""
    return await user_service.verify_user_card(card_token)


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
