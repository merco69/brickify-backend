"""Configuration pour les tests"""

import pytest
from unittest.mock import patch
from ..config import Settings, validate_settings

def test_settings_default_values():
    """Test que les valeurs par défaut sont correctement définies"""
    settings = Settings()
    
    assert settings.FIREBASE_CREDENTIALS_PATH == "firebase-credentials.json"
    assert settings.FIREBASE_STORAGE_BUCKET == "brickify-app.appspot.com"
    assert settings.LUMI_API_URL == "https://api.lumi.ai/v1"
    assert settings.BRICKLINK_API_URL == "https://api.bricklink.com/api/store/v1"
    assert settings.CACHE_TTL == 3600
    assert settings.MAX_UPLOAD_SIZE == 10 * 1024 * 1024
    assert settings.ALLOWED_EXTENSIONS == {"jpg", "jpeg", "png"}

def test_settings_from_env():
    """Test que les variables d'environnement sont correctement chargées"""
    env_vars = {
        "LUMI_API_KEY": "test_lumi_key",
        "BRICKLINK_CONSUMER_KEY": "test_consumer_key",
        "BRICKLINK_CONSUMER_SECRET": "test_consumer_secret",
        "BRICKLINK_TOKEN": "test_token",
        "BRICKLINK_TOKEN_SECRET": "test_token_secret"
    }
    
    with patch.dict("os.environ", env_vars):
        settings = Settings()
        
        assert settings.LUMI_API_KEY == "test_lumi_key"
        assert settings.BRICKLINK_CONSUMER_KEY == "test_consumer_key"
        assert settings.BRICKLINK_CONSUMER_SECRET == "test_consumer_secret"
        assert settings.BRICKLINK_TOKEN == "test_token"
        assert settings.BRICKLINK_TOKEN_SECRET == "test_token_secret"

def test_validate_settings_all_present():
    """Test que la validation passe quand toutes les variables sont présentes"""
    env_vars = {
        "LUMI_API_KEY": "test_lumi_key",
        "BRICKLINK_CONSUMER_KEY": "test_consumer_key",
        "BRICKLINK_CONSUMER_SECRET": "test_consumer_secret",
        "BRICKLINK_TOKEN": "test_token",
        "BRICKLINK_TOKEN_SECRET": "test_token_secret"
    }
    
    with patch.dict("os.environ", env_vars):
        # Ne devrait pas lever d'exception
        validate_settings()

def test_validate_settings_missing_vars():
    """Test que la validation échoue quand des variables sont manquantes"""
    env_vars = {
        "LUMI_API_KEY": "test_lumi_key",
        # BRICKLINK_CONSUMER_KEY manquant
        "BRICKLINK_CONSUMER_SECRET": "test_consumer_secret",
        "BRICKLINK_TOKEN": "test_token",
        "BRICKLINK_TOKEN_SECRET": "test_token_secret"
    }
    
    with patch.dict("os.environ", env_vars):
        with pytest.raises(ValueError) as exc_info:
            validate_settings()
        
        assert "BRICKLINK_CONSUMER_KEY" in str(exc_info.value)

def test_settings_case_sensitive():
    """Test que les noms de variables sont sensibles à la casse"""
    env_vars = {
        "lumi_api_key": "test_lumi_key",  # en minuscules
        "BRICKLINK_CONSUMER_KEY": "test_consumer_key"
    }
    
    with patch.dict("os.environ", env_vars):
        settings = Settings()
        
        # La variable en minuscules ne devrait pas être chargée
        assert settings.LUMI_API_KEY is None
        assert settings.BRICKLINK_CONSUMER_KEY == "test_consumer_key"

MOCK_FIREBASE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "test-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9QFxMI8lI5rTR\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9QFxMI8lI5rTR\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9QFxMI8lI5rTR\n-----END PRIVATE KEY-----\n",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
} 