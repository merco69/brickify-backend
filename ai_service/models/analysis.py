from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List, Optional

class Analysis(BaseModel):
    """Modèle pour l'analyse d'un modèle 3D."""
    id: str
    user_id: str
    model_path: str
    voxel_resolution: int
    brick_count: int
    dimensions: List[int]
    stability_score: float
    brick_types: Dict[str, int]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class AnalysisResult(BaseModel):
    """Résultat de l'analyse d'un modèle 3D."""
    status: str
    model_info: Dict
    instructions: List[Dict]
    device: str
    cuda_available: bool 