from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

class UserStats(BaseModel):
    user_id: str
    total_analyses: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    total_bricks: int = 0
    average_confidence: float = 0.0
    monthly_counts: Dict[str, int] = {}
    last_analysis_date: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 