from app.schemas import ModerationVerdict, PatternDetectionResult


class ModerationPolicy:
    def evaluate(self, patterns: list[PatternDetectionResult]) -> tuple[float, str, bool]:
        if not patterns:
            overall = 0.0
        else:
            overall = max(p.score for p in patterns)
        if overall < 0.3:
            return overall, "approve", False
        if overall <= 0.75:
            return overall, "review", True
        return overall, "reject", True

    def verdict(self, comment_id: str, patterns: list[PatternDetectionResult]) -> ModerationVerdict:
        score, action, flagged = self.evaluate(patterns)
        return ModerationVerdict(
            comment_id=comment_id,
            is_flagged=flagged,
            overall_risk_score=score,
            patterns=patterns,
            recommended_action=action,
        )