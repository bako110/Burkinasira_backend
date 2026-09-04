from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'application Tourisme Burkina"""
    
    # MongoDB - REQUIS: À définir via variables d'environnement
    MONGODB_URL: str
    DATABASE_NAME: str
    
    # Application - REQUIS: À définir via variables d'environnement
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    
    # API - REQUIS: À définir via variables d'environnement
    API_V1_PREFIX: str
    
    # Sécurité & JWT - REQUIS: À définir via variables d'environnement
    SECRET_KEY: str
    
    # CORS - REQUIS: À définir via variables d'environnement
    # Utilisez "*" pour accepter toutes les origines ou liste séparée par virgules
    ALLOWED_ORIGINS: str

    # Stockage des médias (images/vidéos) sur le disque du serveur
    UPLOAD_DIR: str = "uploads"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # URL publique du site web (front) — sert à construire les liens des emails
    # (ex: réinitialisation de mot de passe).
    PUBLIC_WEB_URL: str = "https://burkinasira.com"

    # Envoi d'emails (SMTP). Tant que EMAIL_HOST est vide, aucun email n'est
    # envoyé (l'inscription et le "mot de passe oublié" fonctionnent quand même,
    # l'échec est simplement journalisé).
    EMAIL_HOST: Optional[str] = None
    EMAIL_PORT: int = 587
    EMAIL_USER: Optional[str] = None
    EMAIL_PASS: Optional[str] = None
    # Adresse d'expéditeur. Par défaut on réutilise EMAIL_USER (utile avec Gmail
    # qui exige que le From soit l'adresse authentifiée).
    EMAIL_FROM: Optional[str] = None
    EMAIL_USE_TLS: bool = True  # STARTTLS sur le port 587 ; False + port 465 = SSL direct

    @property
    def email_from_addr(self) -> Optional[str]:
        return self.EMAIL_FROM or self.EMAIL_USER

    @property
    def email_enabled(self) -> bool:
        return bool(self.EMAIL_HOST and self.email_from_addr)

    # Assistant IA — optionnel : tant qu'aucune clé n'est fournie, l'assistant
    # répond avec un message clair indiquant qu'il n'est pas encore activé.
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    # Connexion Google (Sign in with Google) — optionnel : tant qu'aucun client ID
    # n'est fourni, l'endpoint /auth/google renvoie 503. Liste séparée par des
    # virgules : on met le Web client ID ET l'Android client ID (l'app native
    # signe le id_token avec l'un ou l'autre selon la plateforme).
    GOOGLE_CLIENT_IDS: Optional[str] = None

    @property
    def google_client_ids(self) -> list:
        if not self.GOOGLE_CLIENT_IDS or not self.GOOGLE_CLIENT_IDS.strip():
            return []
        return [cid.strip() for cid in self.GOOGLE_CLIENT_IDS.split(",") if cid.strip()]

    @property
    def cors_origins(self) -> list:
        """Convertit ALLOWED_ORIGINS en liste. Si vide ou *, accepte toutes les origines"""
        if not self.ALLOWED_ORIGINS or self.ALLOWED_ORIGINS.strip() == "":
            return ["*"]
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
