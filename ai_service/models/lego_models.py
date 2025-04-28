from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

class LegoAnalysisBase(BaseModel):
    model_path: str
    voxel_resolution: int
    brick_count: Optional[int] = None
    dimensions: Optional[Dict[str, float]] = None
    stability_score: Optional[float] = None
    brick_types: Optional[Dict[str, int]] = None

class LegoAnalysisCreate(LegoAnalysisBase):
    pass

class LegoAnalysisUpdate(LegoAnalysisBase):
    pass

class LegoAnalysis(LegoAnalysisBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 