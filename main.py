import logging
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import Dict, Optional
import time
import torch

from services.blocky_service import BlockyService
from services.blocky_resource_manager import BlockyResourceManager
from services.blocky_optimizer import BlockyOptimizer
from services.storage_service import StorageService
from services.database_service import DatabaseService

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création de l'application
app = FastAPI(
    title="Brickify API",
    description="API pour l'application Brickify",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de compression
app.add_middleware(GZipMiddleware)

# Middleware de monitoring
@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Enregistrement des métriques
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.2f}s")
    
    return response

@app.get("/")
async def root():
    """Route de base pour vérifier que l'API fonctionne"""
    return {
        "message": "Bienvenue sur l'API Brickify",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Route de health check pour Render"""
    return {"status": "healthy"}

# Initialisation des services Blocky
resource_manager = BlockyResourceManager(
    base_dir=Path(os.getenv("STORAGE_PATH", "storage")),
    max_memory_mb=int(os.getenv("MAX_MEMORY_MB", "4096")),
    max_storage_gb=int(os.getenv("MAX_STORAGE_GB", "10")),
    cleanup_interval_mins=int(os.getenv("CLEANUP_INTERVAL_MINS", "30")),
    max_temp_files=int(os.getenv("MAX_TEMP_FILES", "100")),
    max_file_age_hours=int(os.getenv("MAX_FILE_AGE_HOURS", "24"))
)

optimizer = BlockyOptimizer(
    device=os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu"),
    num_workers=int(os.getenv("NUM_WORKERS", "4")),
    batch_size=int(os.getenv("BATCH_SIZE", "32")),
    precision=os.getenv("PRECISION", "float32")
)

blocky_service = BlockyService(
    resource_manager=resource_manager,
    optimizer=optimizer
)

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application"""
    logger.info("Démarrage de l'application...")
    logger.info(f"Blocky initialisé avec GPU: {settings.BLOCKY_DEVICE}")

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application"""
    logger.info("Arrêt de l'application...")

@app.post("/api/blocky/convert")
async def convert_model(
    file: UploadFile = File(...),
    settings: Optional[Dict] = Form(default_factory=dict)
):
    """
    Convertit un modèle 3D en LEGO.
    
    Args:
        file: Fichier modèle 3D
        settings: Paramètres de conversion
    """
    try:
        # Sauvegarder le fichier temporairement
        temp_dir = resource_manager.get_temp_dir("upload")
        file_path = temp_dir / file.filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Convertir le modèle
        success, message = await blocky_service.convert_to_lego(
            model_path=str(file_path),
            settings=settings
        )
        
        if not success:
            return {"success": False, "error": message}
            
        return {"success": True, "result": message}
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/blocky/stats")
async def get_stats():
    """Récupère les statistiques des ressources."""
    try:
        return resource_manager.get_resource_stats()
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(settings.PORT)
    uvicorn.run(app, host="0.0.0.0", port=port) 