from typing import Any, List

from fastapi import APIRouter

from app.schemas import ModerationRequest, ModerationVerdict, PatternDetectionResult

router = APIRouter()

QUEUE: List[dict] = [
    {"comment_id": "c1", "text": " suspicious comment 1 ", "author_id": "u1"},
    {"comment_id": "c2", "text": " suspicious comment 2 ", "author_id": "u2"},
]


def _preprocess(text: str, parent: Any = None) -> str:
    try:
        from app.preprocessor import preprocess

        return preprocess(text, parent)
    except Exception:
        return text.strip()


def _detect(text: str) -> List[PatternDetectionResult]:
    try:
        from app.detector import detect

        return detect(text)
    except Exception:
        return [
            PatternDetectionResult(
                pattern_name="mock",
                score=0.1,
                detected=False,
                explanation="fallback mock",
                highlighted_spans=[],
            )
        ]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/api/v1/moderate", response_model=ModerationVerdict)
def moderate(req: ModerationRequest):
    cleaned = _preprocess(req.text, req.parent_comment_text)
    patterns = _detect(cleaned)
    from app.core.policy import ModerationPolicy

    policy = ModerationPolicy()
    return policy.verdict(req.comment_id, patterns)


@router.get("/api/v1/queue")
def queue():
    return QUEUE