from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ActionItem(BaseModel):
    text: str
    url: Optional[str] = None
    priority: str = Field(pattern="^(high|medium|low)$")


class AnalysisResult(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    red_flags: List[str]
    user_action_items: List[ActionItem]
    timestamp: datetime
    url: str
