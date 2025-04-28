from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LegoBrick(BaseModel):
    """Modèle pour une brique LEGO détectée"""
    id: str
    name: str
    color: str
    quantity: int
    price: float
    confidence: float

class LegoAnalysisBase(BaseModel):
    """Modèle de base pour une analyse LEGO"""
    user_id: str
    original_image_url: str
    lego_image_url: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default="pending")
    error_message: Optional[str] = None
    parts_list: List[LegoBrick] = Field(default_factory=list)
    total_price: float = Field(default=0.0, ge=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LegoAnalysisCreate(LegoAnalysisBase):
    """Modèle pour la création d'une analyse"""
    pass

class LegoAnalysisUpdate(BaseModel):
    """Modèle pour la mise à jour d'une analyse"""
    lego_image_url: Optional[str] = None
    confidence_score: Optional[float] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    parts_list: Optional[List[LegoBrick]] = None
    total_price: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LegoAnalysis(LegoAnalysisBase):
    """Modèle complet pour une analyse LEGO"""
    id: str

    class Config:
        from_attributes = True

class Brick(BaseModel):
    id: str
    name: str
    color: str
    quantity: int
    price: float
    image_url: Optional[str] = None

class LegoAnalysis(BaseModel):
    id: Optional[str] = None
    user_id: str
    file_path: str
    status: AnalysisStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    bricks: Optional[List[Brick]] = None
    total_price: Optional[float] = None
    instructions: Optional[Dict] = None
    error_message: Optional[str] = None

class LegoAnalysisCreate(BaseModel):
    user_id: str
    file_path: str
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: datetime = datetime.utcnow()

class LegoAnalysisUpdate(BaseModel):
    status: Optional[AnalysisStatus] = None
    completed_at: Optional[datetime] = None
    bricks: Optional[List[Brick]] = None
    total_price: Optional[float] = None
    instructions: Optional[Dict] = None
    error_message: Optional[str] = None 