import pytest
from ..services.auth_service import AuthService
from ..models.user import User
from ..database import get_db

@pytest.mark.asyncio
async def test_create_user(db, test_user):
    auth_service = AuthService(db)
    user = await auth_service.create_user(
        email=test_user["email"],
        password=test_user["password"],
        full_name=test_user["full_name"]
    )
    assert user.email == test_user["email"]
    assert user.full_name == test_user["full_name"]
    assert user.hashed_password != test_user["password"]

@pytest.mark.asyncio
async def test_authenticate_user(db, test_user):
    auth_service = AuthService(db)
    # Créer l'utilisateur
    await auth_service.create_user(
        email=test_user["email"],
        password=test_user["password"],
        full_name=test_user["full_name"]
    )
    # Tester l'authentification
    user = await auth_service.authenticate_user(
        email=test_user["email"],
        password=test_user["password"]
    )
    assert user is not None
    assert user.email == test_user["email"]

@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db, test_user):
    auth_service = AuthService(db)
    # Créer l'utilisateur
    await auth_service.create_user(
        email=test_user["email"],
        password=test_user["password"],
        full_name=test_user["full_name"]
    )
    # Tester l'authentification avec un mauvais mot de passe
    user = await auth_service.authenticate_user(
        email=test_user["email"],
        password="wrongpassword"
    )
    assert user is None

@pytest.mark.asyncio
async def test_create_access_token(db, test_user):
    auth_service = AuthService(db)
    # Créer l'utilisateur
    user = await auth_service.create_user(
        email=test_user["email"],
        password=test_user["password"],
        full_name=test_user["full_name"]
    )
    # Créer le token
    token = auth_service.create_access_token(user)
    assert token is not None
    assert isinstance(token, str)

@pytest.mark.asyncio
async def test_get_current_user(db, test_user):
    auth_service = AuthService(db)
    # Créer l'utilisateur
    user = await auth_service.create_user(
        email=test_user["email"],
        password=test_user["password"],
        full_name=test_user["full_name"]
    )
    # Créer le token
    token = auth_service.create_access_token(user)
    # Récupérer l'utilisateur à partir du token
    current_user = await auth_service.get_current_user(token)
    assert current_user is not None
    assert current_user.email == test_user["email"]

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db):
    auth_service = AuthService(db)
    with pytest.raises(Exception):
        await auth_service.get_current_user("invalid_token") 