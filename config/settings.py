import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

class Settings(BaseSettings):
    # Configuration de l'application
    APP_NAME: str = "Brickify"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    
    # Configuration de la base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./brickify.db")
    
    # Configuration de l'authentification
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuration de Lumi.ai
    LUMI_API_URL: str = os.getenv("LUMI_API_URL", "https://api.lumi.ai")
    LUMI_API_KEY: str = os.getenv("LUMI_API_KEY", "")
    
    # Configuration de BrickLink
    BRICKLINK_API_URL: str = os.getenv("BRICKLINK_API_URL", "https://api.bricklink.com/api/store/v1")
    BRICKLINK_API_KEY: str = os.getenv("BRICKLINK_API_KEY", "")
    BRICKLINK_API_SECRET: str = os.getenv("BRICKLINK_API_SECRET", "")
    BRICKLINK_ACCESS_TOKEN: str = os.getenv("BRICKLINK_ACCESS_TOKEN", "")
    BRICKLINK_ACCESS_TOKEN_SECRET: str = os.getenv("BRICKLINK_ACCESS_TOKEN_SECRET", "")
    
    # Configuration du stockage
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # local, s3, gcs
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "brickify-models")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    
    # Configuration AWS (si utilisation de S3)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-west-1")
    
    # Configuration Google Cloud (si utilisation de GCS)
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Configuration des limites d'abonnement
    SUBSCRIPTION_LIMITS: Dict[str, Dict[str, Any]] = {
        "free": {
            "max_analyses_per_month": 2,
            "max_bricks_per_analysis": 100,
            "has_instructions": False,
            "has_ads": True
        },
        "basic": {
            "max_analyses_per_month": 10,
            "max_bricks_per_analysis": 500,
            "has_instructions": True,
            "has_ads": False
        },
        "premium": {
            "max_analyses_per_month": float('inf'),
            "max_bricks_per_analysis": float('inf'),
            "has_instructions": True,
            "has_ads": False
        }
    }
    
    # Configuration des métriques et monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instance globale des paramètres
settings = Settings() 