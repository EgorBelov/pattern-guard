"""Схемы данных PatternGuard."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModerationRequest(BaseModel):
    comment_id: str
    text: str
    author_id: str
    parent_comment_text: Optional[str] = None


class PatternDetectionResult(BaseModel):
    pattern_name: str
    score: float = Field(ge=0.0, le=1.0)
    detected: bool
    explanation: str
    highlighted_spans: List[str] = Field(default_factory=list)


class ModerationVerdict(BaseModel):
    comment_id: str
    is_flagged: bool
    overall_risk_score: float = Field(ge=0.0, le=1.0)
    patterns: List[PatternDetectionResult] = Field(default_factory=list)
    recommended_action: Literal["approve", "review", "reject"]
