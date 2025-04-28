import pytest
from fastapi.testclient import TestClient
from ..routes.auth_routes import router
from ..models.user import User
from ..services.auth_service import AuthService

@pytest.mark.asyncio
async def test_register(client, test_user):
    response = client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == test_user["email"]
    assert data["full_name"] == test_user["full_name"]
    assert "password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user):
    # Premier enregistrement
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    
    # Tentative de second enregistrement avec le même email
    response = client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": "different_password",
            "full_name": "Different Name"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login(client, test_user):
    # Créer l'utilisateur
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    
    # Tester la connexion
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    # Créer l'utilisateur
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    
    # Tester la connexion avec un mauvais mot de passe
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user["email"],
            "password": "wrong_password"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_forgot_password(client, test_user):
    # Créer l'utilisateur
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    
    # Tester la demande de réinitialisation
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    assert response.status_code == 200
    assert "reset token" in response.json()["message"].lower()

@pytest.mark.asyncio
async def test_reset_password(client, test_user):
    # Créer l'utilisateur
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
        }
    )
    
    # Obtenir le token de réinitialisation
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    reset_token = response.json()["reset_token"]
    
    # Tester la réinitialisation du mot de passe
    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "new_password123"
        }
    )
    assert response.status_code == 200
    assert "password updated" in response.json()["message"].lower()
    
    # Vérifier que le nouveau mot de passe fonctionne
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user["email"],
            "password": "new_password123"
        }
    )
    assert response.status_code == 200 