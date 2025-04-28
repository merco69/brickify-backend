from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
from datetime import timedelta
from jose import JWTError, jwt

from ..services.auth_service import AuthService
from ..models.user_models import User, UserCreate, UserUpdate, SubscriptionTier
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_auth_service() -> AuthService:
    """Dependency pour obtenir une instance du service d'authentification."""
    return AuthService()

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Crée un token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Récupère l'utilisateur actuel à partir du token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await auth_service.db.get_user_by_email(email=email)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=User)
async def register(
    user_create: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Enregistre un nouvel utilisateur."""
    try:
        return await auth_service.register_user(user_create)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authentifie un utilisateur et retourne un token."""
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté."""
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Met à jour les informations de l'utilisateur connecté."""
    updated_user = await auth_service.update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return updated_user

@router.post("/reset-password")
async def reset_password(
    email: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Réinitialise le mot de passe d'un utilisateur."""
    try:
        temp_password = await auth_service.reset_password(email)
        # TODO: Envoyer le mot de passe temporaire par email
        return {"message": "Un mot de passe temporaire a été généré"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/users", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Récupère la liste des utilisateurs (admin seulement)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    return await auth_service.get_all_users(skip, limit)

@router.get("/users/subscription/{tier}", response_model=List[User])
async def get_users_by_subscription(
    tier: SubscriptionTier,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Récupère les utilisateurs par niveau d'abonnement (admin seulement)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    return await auth_service.get_users_by_subscription(tier)

@router.put("/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: str,
    subscription_tier: SubscriptionTier,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Met à jour le niveau d'abonnement d'un utilisateur (admin seulement)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
        
    updated_user = await auth_service.update_subscription(user_id, subscription_tier)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return updated_user 