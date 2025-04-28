import os
from typing import Optional
from pydantic import BaseModel, BaseSettings
from dotenv import load_dotenv
from pathlib import Path
from functools import lru_cache

# Chargement des variables d'environnement
load_dotenv()

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Version et environnement
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Configuration des logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuration de la base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./brickify.db")
    
    # JWT
    SECRET_KEY: str = os.getenv("JWT_SECRET", "votre_secret_jwt_super_secret")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Blocky settings
    models_dir: str = "data/models"
    temp_dir: str = "data/temp"
    max_memory_mb: int = 4096  # 4GB
    max_storage_mb: int = 10240  # 10GB
    cleanup_interval_seconds: int = 3600  # 1 hour
    max_temp_files: int = 1000
    max_file_age_hours: int = 24
    
    # GPU settings
    use_gpu: bool = True
    gpu_memory_fraction: float = 0.8
    batch_size: int = 4
    num_workers: int = 4
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Ensure directories exist
def init_directories():
    settings = get_settings()
    Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)

# Instance de configuration
settings = Settings()

def validate_settings():
    """Valide que toutes les variables d'environnement requises sont définies"""
    required_vars = [
        "LUMI_API_KEY",
        "BRICKLINK_CONSUMER_KEY",
        "BRICKLINK_CONSUMER_SECRET",
        "BRICKLINK_TOKEN",
        "BRICKLINK_TOKEN_SECRET"
    ]
    
    missing_vars = [var for var in required_vars if not getattr(settings, var)]
    
    if missing_vars:
        raise ValueError(
            f"Variables d'environnement manquantes : {', '.join(missing_vars)}"
        ) 