from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, List
from ..services.blocky_service import BlockyService
from ..services.auth_service import AuthService, get_current_user
from ..models.user import User
from ..config import get_settings

router = APIRouter(prefix="/api/blocky", tags=["blocky"])
settings = get_settings()

def get_blocky_service():
    """Dépendance pour obtenir le service Blocky."""
    return BlockyService(
        storage=settings.storage_service,
        database=settings.database_service,
        base_dir=Path(settings.models_dir),
        max_memory_mb=settings.max_memory_mb,
        max_storage_mb=settings.max_storage_mb
    )

@router.post("/convert")
async def convert_model(
    file: UploadFile = File(...),
    settings: Dict = {},
    user: User = Depends(get_current_user),
    blocky: BlockyService = Depends(get_blocky_service)
):
    """
    Convertit un modèle 3D en LEGO.
    
    Args:
        file: Fichier modèle 3D
        settings: Paramètres de conversion
        user: Utilisateur authentifié
        blocky: Service Blocky
    """
    try:
        # Sauvegarder le fichier temporairement
        temp_dir = Path(settings.temp_dir) / f"upload_{file.filename}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename
        
        with temp_path.open("wb") as f:
            content = await file.read()
            f.write(content)
            
        # Générer un ID unique pour le modèle
        model_id = f"{user.id}_{file.filename}"
        
        # Convertir le modèle
        result_path = await blocky.convert_to_lego(
            model_path=temp_path,
            user_id=user.id,
            model_id=model_id,
            settings=settings
        )
        
        # Retourner le fichier
        return FileResponse(
            path=result_path,
            filename=f"lego_{file.filename}",
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la conversion: {str(e)}"
        )
        
@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    user: User = Depends(get_current_user),
    blocky: BlockyService = Depends(get_blocky_service)
):
    """
    Récupère les informations d'un modèle.
    
    Args:
        model_id: ID du modèle
        user: Utilisateur authentifié
        blocky: Service Blocky
    """
    model_info = await blocky.get_model_info(model_id, user.id)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail="Modèle non trouvé"
        )
    return model_info
    
@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    user: User = Depends(get_current_user),
    blocky: BlockyService = Depends(get_blocky_service)
):
    """
    Supprime un modèle.
    
    Args:
        model_id: ID du modèle
        user: Utilisateur authentifié
        blocky: Service Blocky
    """
    success = await blocky.delete_model(model_id, user.id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Modèle non trouvé ou permission refusée"
        )
    return {"status": "success"} 