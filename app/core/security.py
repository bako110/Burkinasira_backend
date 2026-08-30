from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
import logging

logger = logging.getLogger(__name__)

# Configuration de hashing des mots de passe - argon2 au lieu de bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Bearer token
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Clé secrète pour JWT
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 heures


def hash_password(password: str) -> str:
    """Hasher un mot de passe"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    permissions: List[str] = None,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, datetime]:
    """Créer un JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role.value if isinstance(role, UserRole) else role,
        "permissions": permissions or [],
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def decode_token(token: str) -> TokenPayload:
    """Décoder et valider un JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        permissions: list = payload.get("permissions", [])
        
        if user_id is None or email is None:
            raise credentials_exception
            
        token_data = TokenPayload(
            sub=user_id,
            email=email,
            role=UserRole(role),
            permissions=permissions
        )
    except JWTError:
        raise credentials_exception
    
    return token_data


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenPayload:
    """Récupérer l'utilisateur courant à partir du JWT"""
    token = credentials.credentials
    return decode_token(token)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[TokenPayload]:
    """Récupérer l'utilisateur courant si un token est fourni, sinon None (ex: signalement anonyme)"""
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


def require_role(*allowed_roles: UserRole):
    """Factory pour créer une dépendance de vérification de rôle"""
    async def check_role(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cette action nécessite l'un de ces rôles: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user

    return check_role


async def require_verified_provider(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
) -> TokenPayload:
    """Comme require_role(PROVIDER, ADMIN), mais bloque en plus un compte provider
    dont la vérification (documents) n'a pas encore été approuvée."""
    if current_user.role == UserRole.ADMIN:
        return current_user
    from app.services import user_service  # import différé pour éviter un cycle security <-> services

    user = await user_service.get_user_by_id(current_user.sub)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte professionnel doit être vérifié avant de publier un établissement",
        )
    return current_user


async def require_admin(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Vérifier que l'utilisateur est admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_guide_or_admin(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Vérifier que l'utilisateur est guide ou admin"""
    if current_user.role not in [UserRole.GUIDE, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guide or admin access required"
        )
    return current_user


async def require_verified(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Vérifier que l'utilisateur est vérifié"""
    # Ce sera complété en lisant la BD pour vérifier le flag verifiee
    return current_user
