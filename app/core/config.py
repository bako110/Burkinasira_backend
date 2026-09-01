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

    # Assistant IA — optionnel : tant qu'aucune clé n'est fournie, l'assistant
    # répond avec un message clair indiquant qu'il n'est pas encore activé.
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    
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
