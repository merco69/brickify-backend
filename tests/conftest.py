import pytest
import asyncio
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
from main import app
from database import Database
from services.storage_service import StorageService
from subscription import SubscriptionService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..database import Base, get_db
from ..config import settings

# Configuration du chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest_plugins = ["pytest_asyncio"]

# Configuration de la base de données de test
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def event_loop():
    """Crée une nouvelle boucle d'événements pour chaque test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_firebase_auth():
    with patch('firebase_admin.auth') as mock_auth:
        mock_auth.verify_id_token.return_value = {
            "uid": "test_user_id",
            "email": "test@example.com"
        }
        yield mock_auth

@pytest.fixture
def mock_storage_service():
    with patch('services.storage_service.StorageService') as mock_storage:
        mock_instance = mock_storage.return_value
        mock_instance.upload_model.return_value = "test_url"
        mock_instance.get_model_url.return_value = "signed_test_url"
        yield mock_instance

@pytest.fixture
def mock_database():
    with patch('database.Database') as mock_db:
        mock_instance = mock_db.return_value
        mock_instance.check_and_deduct_tokens.return_value = True
        mock_instance.create_model.return_value = "test_model_id"
        mock_instance.get_model.return_value = {
            "id": "test_model_id",
            "uid": "test_user_id",
            "input_image_url": "test_input_url",
            "lego_image_url": "test_lego_url",
            "instructions": "test_instructions",
            "created_at": "2024-04-11T00:00:00"
        }
        mock_instance.get_user_models.return_value = [{
            "id": "test_model_id",
            "uid": "test_user_id",
            "input_image_url": "test_input_url",
            "lego_image_url": "test_lego_url",
            "instructions": "test_instructions",
            "created_at": "2024-04-11T00:00:00"
        }]
        yield mock_instance

@pytest.fixture
def mock_subscription_service():
    with patch('subscription.SubscriptionService') as mock_sub:
        mock_instance = mock_sub.return_value
        mock_instance.can_add_model.return_value = True
        mock_instance.get_subscription_info.return_value = {
            "type": "free",
            "models_remaining": 5
        }
        yield mock_instance

@pytest.fixture
def mock_legoizer():
    with patch('legoizer.Legoizer') as mock_lego:
        mock_instance = mock_lego.return_value
        mock_instance.process_image.return_value = (b"test_lego_image", "test_instructions")
        yield mock_instance

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_token"}

@pytest.fixture(scope="session")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }

@pytest.fixture
def test_image():
    return {
        "file": ("test_image.jpg", b"fake image content", "image/jpeg")
    } 