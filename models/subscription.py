from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

class SubscriptionType(str, Enum):
    FREE = "free"
    MEDIUM = "medium"
    PREMIUM = "premium"

class SubscriptionFeatures(BaseModel):
    max_models: int
    max_storage_gb: int
    max_resolution: str
    export_formats: list[str]
    priority_support: bool
    api_access: bool

class SubscriptionInfo(BaseModel):
    user_id: str
    type: SubscriptionType
    start_date: datetime
    end_date: Optional[datetime] = None
    features: SubscriptionFeatures
    model_count: int = 0
    storage_used_gb: float = 0.0
    is_active: bool = True

    class Config:
        orm_mode = True 