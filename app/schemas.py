"""Схемы данных PatternGuard."""
from pydantic import BaseModel, Field
from typing import List


class PatternDetectionResult(BaseModel):
    pattern_name: str
    score: float = Field(ge=0.0, le=1.0)
    detected: bool
    explanation: str
    highlighted_spans: List[str] = Field(default_factory=list)
