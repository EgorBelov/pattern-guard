from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_moderate_pipeline_flags_toxic_spam_with_homoglyph_and_link():
    text = (
        "Ты иди"
        + "o"
        + "т! Переходи по ссылке https://t.me/scam и получи бесплатные деньги"
    )
    response = client.post(
        "/api/v1/moderate",
        json={
            "comment_id": "it-1",
            "text": text,
            "author_id": "u-test",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["comment_id"] == "it-1"
    assert data["is_flagged"] is True
    assert 0.0 <= data["overall_risk_score"] <= 1.0
    assert data["recommended_action"] in {"review", "reject"}

    patterns = {pattern["pattern_name"]: pattern for pattern in data["patterns"]}
    assert "toxicity" in patterns
    assert "spam_invite" in patterns
    assert "идиот" in patterns["toxicity"]["highlighted_spans"]


def test_moderate_pipeline_approves_clean_comment():
    response = client.post(
        "/api/v1/moderate",
        json={
            "comment_id": "it-2",
            "text": "Спасибо за подробный разбор, всё понятно.",
            "author_id": "u-test",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_flagged"] is False
    assert data["recommended_action"] == "approve"
    assert data["overall_risk_score"] == 0.0
    assert data["patterns"] == []


def test_queue_exposes_pipeline_scores():
    response = client.get("/api/v1/queue")

    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 4
    assert all(0.0 <= item["risk_score"] <= 1.0 for item in items)
    assert any(item["recommended_action"] != "approve" for item in items)
    assert {"comment_id", "text", "author_id", "reason", "patterns"} <= set(
        items[0]
    )
