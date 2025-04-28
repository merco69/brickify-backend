import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status, Query
from fastapi.responses import JSONResponse
from ..models.lego_models import LegoAnalysis, LegoAnalysisCreate, LegoAnalysisUpdate, AnalysisStatus
from ..models.lego_models import LegoAnalysis, LegoAnalysisCreate, LegoAnalysisUpdate
from ..services.database_service import DatabaseService
from ..services.lego_analyzer_service import LegoAnalyzerService
from ..services.storage_service import StorageService
from ..config import settings
import os
from datetime import datetime
from ..services.user_service import UserService
from ..models.user_models import SubscriptionTier, User
from ..services.stats_service import StatsService
from ..exceptions import ValidationError, SubscriptionLimitError
from ..metrics import track_request_metrics, analysis_tracker
import uuid
from ..services.subscription_service import SubscriptionService
from ..services.lego_service import LegoService
from ..services.auth_service import get_current_user, AuthService
from ..services.lego_converter_service import LegoConverterService
from ..models.lego_model import LegoModel

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/lego",
    tags=["lego"],
    responses={404: {"description": "Not found"}},
)

# Constantes
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
MAX_FILENAME_LENGTH = 255

def validate_file(file: UploadFile) -> None:
    """
    Valide un fichier uploadé
    
    Args:
        file: Fichier à valider
        
    Raises:
        ValidationError: Si le fichier est invalide
    """
    # Vérification de l'extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Extension non autorisée. Extensions acceptées: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Vérification de la longueur du nom
    if len(file.filename) > MAX_FILENAME_LENGTH:
        raise ValidationError(f"Nom de fichier trop long. Maximum: {MAX_FILENAME_LENGTH} caractères")
    
    # Vérification de la taille
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    while chunk := file.read(chunk_size):
        file_size += len(chunk)
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(f"Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE/1024/1024}MB")

def validate_user_id(user_id: Optional[str]) -> None:
    """
    Valide un ID utilisateur
    
    Args:
        user_id: ID à valider
        
    Raises:
        ValidationError: Si l'ID est invalide
    """
    if user_id is not None:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise ValidationError("Format d'ID utilisateur invalide")

# Dépendances
async def get_db():
    async with DatabaseService() as db:
        yield db

async def get_storage():
    return StorageService()

async def get_analyzer(storage: StorageService = Depends(get_storage)):
    return LegoAnalyzerService(storage)

async def get_user_service(db: DatabaseService = Depends(get_db)):
    return UserService(db)

async def get_stats_service(db: DatabaseService = Depends(get_db)):
    return StatsService(db)

async def get_subscription_service(db: DatabaseService = Depends(get_db)):
    return SubscriptionService(db)

# Routes
@router.post("/analyze", response_model=LegoAnalysis)
async def analyze_lego_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> LegoAnalysis:
    """
    Analyser une image LEGO et retourner les résultats
    """
    try:
        analysis = await LegoService.analyze_image(file, current_user)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/analysis/{analysis_id}", response_model=LegoAnalysis)
async def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user)
) -> LegoAnalysis:
    """
    Récupérer les résultats d'une analyse par son ID
    """
    analysis = await LegoService.get_analysis(analysis_id, current_user)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    return analysis

@router.get("/analysis", response_model=List[LegoAnalysis])
async def list_analyses(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
) -> List[LegoAnalysis]:
    """
    Lister toutes les analyses de l'utilisateur
    """
    return await LegoService.list_analyses(current_user, skip, limit)

@router.put("/analysis/{analysis_id}", response_model=LegoAnalysis)
async def update_analysis(
    analysis_id: int,
    analysis_update: LegoAnalysisUpdate,
    current_user: User = Depends(get_current_user)
) -> LegoAnalysis:
    """
    Mettre à jour une analyse
    """
    analysis = await LegoService.update_analysis(analysis_id, analysis_update, current_user)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    return analysis

@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Supprimer une analyse
    """
    success = await LegoService.delete_analysis(analysis_id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    return JSONResponse(content={"message": "Analyse supprimée avec succès"})

# Fonctions utilitaires
async def process_analysis_with_stats(
    analysis_id: str,
    db: DatabaseService,
    analyzer: LegoAnalyzerService,
    subscription_service: SubscriptionService
):
    """Traite une analyse en arrière-plan avec statistiques"""
    try:
        await analysis_tracker.start_analysis()
        
        # Récupération de l'analyse
        analysis = await db.get_analysis(analysis_id)
        if not analysis:
            logger.error(f"Analyse {analysis_id} non trouvée")
            return
        
        # Mise à jour du statut
        await db.update_analysis(analysis_id, {"status": "processing"})
        
        # Traitement de l'image
        result = await analyzer.process_image(analysis["image_path"], analysis["user_id"])
        
        # Mise à jour de l'analyse avec les résultats
        await db.update_analysis(analysis_id, {
            "status": "completed",
            "confidence_score": result["analysis"]["confidence_score"],
            "bricks": result["analysis"]["parts_list"],
            "bricklink_summary": result["bricklink_summary"],
            "updated_at": datetime.now().isoformat()
        })
        
        # Mise à jour des statistiques
        await subscription_service.increment_analysis_count(
            datetime.now().year,
            datetime.now().month,
            True,
            len(result["analysis"]["parts_list"]),
            result["analysis"]["confidence_score"]
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'analyse {analysis_id}: {str(e)}")
        await db.update_analysis(analysis_id, {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        })
        
        # Mise à jour des statistiques d'erreur
        await subscription_service.increment_analysis_count(
            datetime.now().year,
            datetime.now().month,
            False,
            0,
            0.0
        )
        
    finally:
        await analysis_tracker.end_analysis()

@router.get("/models", response_model=List[LegoModel])
async def get_models(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(AuthService.get_current_user),
    lego_service: LegoConverterService = Depends(),
    storage_service: StorageService = Depends()
):
    """
    Récupère la liste des modèles Lego.
    
    Args:
        category: Filtrer par catégorie
        difficulty: Filtrer par difficulté
        tags: Filtrer par tags
        search: Rechercher par nom ou description
        limit: Nombre maximum de résultats
        offset: Décalage pour la pagination
        current_user: Utilisateur actuel
        lego_service: Service de conversion Lego
        storage_service: Service de stockage
        
    Returns:
        Liste des modèles Lego
    """
    try:
        # Récupérer les modèles
        models = await lego_service.get_models(
            category=category,
            difficulty=difficulty,
            tags=tags,
            search=search,
            limit=limit,
            offset=offset
        )
        
        return models
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/models/{model_id}", response_model=LegoModel)
async def get_model(
    model_id: str,
    current_user: User = Depends(AuthService.get_current_user),
    lego_service: LegoConverterService = Depends(),
    storage_service: StorageService = Depends()
):
    """
    Récupère un modèle Lego par son ID.
    
    Args:
        model_id: ID du modèle
        current_user: Utilisateur actuel
        lego_service: Service de conversion Lego
        storage_service: Service de stockage
        
    Returns:
        Le modèle Lego
    """
    try:
        # Récupérer le modèle
        model = await lego_service.get_model(model_id)
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail="Modèle non trouvé"
            )
        
        # Vérifier les permissions
        if not model.is_public and model.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Accès non autorisé"
            )
        
        return model
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: User = Depends(AuthService.get_current_user),
    lego_service: LegoConverterService = Depends(),
    storage_service: StorageService = Depends()
):
    """
    Supprime un modèle Lego.
    
    Args:
        model_id: ID du modèle
        current_user: Utilisateur actuel
        lego_service: Service de conversion Lego
        storage_service: Service de stockage
        
    Returns:
        Message de confirmation
    """
    try:
        # Récupérer le modèle
        model = await lego_service.get_model(model_id)
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail="Modèle non trouvé"
            )
        
        # Vérifier les permissions
        if model.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Accès non autorisé"
            )
        
        # Supprimer le modèle
        await lego_service.delete_model(model_id)
        
        return {"message": "Modèle supprimé avec succès"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 