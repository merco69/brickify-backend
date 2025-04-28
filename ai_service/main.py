import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import torch

from services.blocky_service import BlockyService
from services.blocky_resource_manager import BlockyResourceManager
from services.blocky_optimizer import BlockyOptimizer
from services.cache_service import CacheService

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création de l'application
app = FastAPI(
    title="Brickify AI Service",
    description="Service d'IA pour la conversion de modèles 3D en LEGO",
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

# Initialisation des services
resource_manager = BlockyResourceManager(
    base_dir=Path(os.getenv("STORAGE_PATH", "storage")),
    max_memory_mb=int(os.getenv("MAX_MEMORY_MB", "4096")),
    max_storage_gb=int(os.getenv("MAX_STORAGE_GB", "10")),
    cleanup_interval_mins=int(os.getenv("CLEANUP_INTERVAL_MINS", "30")),
    max_temp_files=int(os.getenv("MAX_TEMP_FILES", "100")),
    max_file_age_hours=int(os.getenv("MAX_FILE_AGE_HOURS", "24"))
)

cache_service = CacheService(
    cache_dir=Path(os.getenv("CACHE_DIR", "cache")),
    max_age_days=int(os.getenv("CACHE_MAX_AGE_DAYS", "30"))
)

optimizer = BlockyOptimizer(
    device=os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu"),
    num_workers=int(os.getenv("NUM_WORKERS", "4")),
    batch_size=int(os.getenv("BATCH_SIZE", "32")),
    precision=os.getenv("PRECISION", "float32")
)

blocky_service = BlockyService(
    resource_manager=resource_manager,
    optimizer=optimizer,
    cache_service=cache_service
)

@app.post("/api/convert")
async def convert_model(
    file: UploadFile = File(...),
    voxel_resolution: int = 32,
    optimize_stability: bool = True,
    optimize_colors: bool = True
):
    """
    Convertit un modèle 3D en LEGO.
    
    Args:
        file: Fichier modèle 3D
        voxel_resolution: Résolution de la grille de voxels (8-128)
        optimize_stability: Optimiser la stabilité
        optimize_colors: Optimiser les couleurs
    """
    try:
        # Vérifie le format du fichier
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in blocky_service.get_supported_formats():
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté: {file_ext}. Formats supportés: {', '.join(blocky_service.get_supported_formats())}"
            )
        
        # Paramètres de conversion
        model_params = {
            "voxel_resolution": voxel_resolution,
            "optimize_stability": optimize_stability,
            "optimize_colors": optimize_colors
        }
        
        # Sauvegarder le fichier temporairement
        temp_dir = resource_manager.get_temp_dir("upload")
        file_path = temp_dir / file.filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Vérifie le cache
        cached_result = await cache_service.get_cached_result(file_path, model_params)
        if cached_result:
            logger.info(f"Résultat trouvé dans le cache pour {file.filename}")
            return cached_result
            
        # Convertir le modèle
        result = await blocky_service.convert_to_lego(
            model_path=str(file_path),
            **model_params
        )
        
        # Sauvegarde dans le cache
        await cache_service.save_result(file_path, model_params, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Retourne les statistiques du cache."""
    return await cache_service.get_cache_stats()

@app.post("/api/cache/cleanup")
async def cleanup_cache():
    """Nettoie les entrées expirées du cache."""
    await cache_service.cleanup()
    return {"status": "success", "message": "Cache nettoyé"}

@app.get("/api/formats")
async def get_supported_formats():
    """Liste tous les formats de fichiers 3D supportés."""
    return {
        "formats": sorted(list(blocky_service.get_supported_formats())),
        "total": len(blocky_service.get_supported_formats())
    }

@app.get("/health")
async def health_check():
    """Route de health check"""
    return {
        "status": "healthy",
        "gpu": torch.cuda.is_available(),
        "device": optimizer.device
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port) 