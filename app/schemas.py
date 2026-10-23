from typing import List, Literal, Optional

from pydantic import BaseModel


class ModerationRequest(BaseModel):
    comment_id: str
    text: str
    author_id: str
    parent_comment_text: Optional[str] = None


class PatternDetectionResult(BaseModel):
    pattern_name: str
    score: float
    detected: bool
    explanation: str
    highlighted_spans: List[str]


class ModerationVerdict(BaseModel):
    comment_id: str
    is_flagged: bool
    overall_risk_score: float
    patterns: List[PatternDetectionResult]
    recommended_action: Literal["approve", "review", "reject"]