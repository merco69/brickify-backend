import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import tempfile
import shutil

from ..services.lego_converter_service import LegoConverterService
from ..services.meshroom_service import MeshroomService
from ..services.storage_service import StorageService
from ..models.lego_model import LegoModel
from ..services.auth_service import AuthService
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/conversion",
    tags=["conversion"],
    responses={404: {"description": "Not found"}},
)

# Dépendances
async def get_meshroom_service():
    return MeshroomService()

async def get_storage_service():
    return StorageService()

async def get_converter_service(
    meshroom: MeshroomService = Depends(get_meshroom_service),
    storage: StorageService = Depends(get_storage_service)
):
    return LegoConverterService(meshroom, storage)

@router.post("/3d-to-lego")
async def convert_3d_to_lego(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    difficulty: str = Form(...),
    is_public: bool = Form(False),
    tags: Optional[List[str]] = Form(None),
    current_user: User = Depends(AuthService.get_current_user),
    lego_service: LegoConverterService = Depends(),
    storage_service: StorageService = Depends()
):
    """
    Convertit un fichier 3D en modèle Lego.
    
    Args:
        file: Fichier 3D à convertir
        name: Nom du modèle
        description: Description du modèle
        category: Catégorie du modèle
        difficulty: Niveau de difficulté
        is_public: Si le modèle est public
        tags: Liste des tags
        current_user: Utilisateur actuel
        lego_service: Service de conversion Lego
        storage_service: Service de stockage
        
    Returns:
        Le modèle Lego créé
    """
    try:
        # Vérifier le format du fichier
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [f['extension'] for f in lego_service.get_supported_formats()]:
            raise HTTPException(
                status_code=400,
                detail=f"Format de fichier non supporté. Formats supportés: {', '.join(f['extension'] for f in lego_service.get_supported_formats())}"
            )
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        try:
            # Convertir le modèle
            model = await lego_service.convert_to_lego(
                model_path=temp_path,
                user_id=current_user.id,
                name=name,
                description=description,
                category=category,
                difficulty=difficulty,
                is_public=is_public,
                tags=tags
            )
            
            if not model:
                raise HTTPException(
                    status_code=500,
                    detail="Erreur lors de la conversion du modèle"
                )
            
            return model
            
        finally:
            # Nettoyer le fichier temporaire
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Erreur lors de la conversion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/supported-formats")
async def get_supported_formats(
    lego_service: LegoConverterService = Depends()
):
    """
    Retourne la liste des formats de fichiers supportés.
    
    Args:
        lego_service: Service de conversion Lego
        
    Returns:
        Liste des formats avec leur description
    """
    return lego_service.get_supported_formats() 