"""HTTP-маршруты PatternGuard."""
from dataclasses import asdict
from typing import Any, List

from fastapi import APIRouter

from app.core.policy import ModerationPolicy
from app.detector.model import PatternDetector
from app.preprocessor.cleaner import TextCleaner
from app.schemas import ModerationRequest, ModerationVerdict, PatternDetectionResult

router = APIRouter()

cleaner = TextCleaner()
detector = PatternDetector()
policy = ModerationPolicy()

QUEUE: List[ModerationRequest] = [
    ModerationRequest(
        comment_id="c1",
        author_id="u1",
        text="Ты просто идиот, как можно так думать?",
    ),
    ModerationRequest(
        comment_id="c2",
        author_id="u2",
        text="Пишите в лс за БЕСПЛАТНЫЙ заработок без вложений!",
    ),
    ModerationRequest(
        comment_id="c3",
        author_id="u3",
        text="С твоим-то умом мне вас учить...",
    ),
    ModerationRequest(
        comment_id="c4",
        author_id="u4",
        text="ЭТО ПРОСТО НЕВЕРОЯТНО!! КАК ТАК МОЖНО!!!",
    ),
]


def _run_pipeline(
    text: str,
    parent_comment_text: Any = None,
) -> List[PatternDetectionResult]:
    cleaned_text, metadata = cleaner.clean(text)
    detection_metadata = asdict(metadata)
    if parent_comment_text:
        detection_metadata["parent_comment_text"] = parent_comment_text
    return detector.detect(cleaned_text, detection_metadata)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/api/v1/moderate", response_model=ModerationVerdict)
def moderate(req: ModerationRequest) -> ModerationVerdict:
    patterns = _run_pipeline(req.text, req.parent_comment_text)
    return policy.verdict(req.comment_id, patterns)


@router.get("/api/v1/queue")
def queue():
    items = []
    for req in QUEUE:
        patterns = _run_pipeline(req.text)
        verdict = policy.verdict(req.comment_id, patterns)
        items.append(
            {
                "comment_id": req.comment_id,
                "text": req.text,
                "author_id": req.author_id,
                "risk_score": verdict.overall_risk_score,
                "recommended_action": verdict.recommended_action,
                "reason": (
                    patterns[0].explanation
                    if patterns
                    else "Негативных паттернов не обнаружено."
                ),
                "patterns": [pattern.model_dump() for pattern in patterns],
            }
        )
    return items
