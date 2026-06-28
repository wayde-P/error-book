# backend/tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    from app import app
    import auth
    app.dependency_overrides[auth.get_current_user_id] = lambda: "user1"
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_tags_returns_200(client):
    with patch("routes.tags.TagService") as MockSvc:
        MockSvc.return_value.list_tags.return_value = []
        resp = client.get("/tags", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        assert resp.json() == []

def test_create_tag_returns_tag(client):
    from models.tag import Tag
    fake_tag = Tag(tagId="t1", userId="user1", name="数学", color="#FF0000", createdAt="2026-06-28T00:00:00Z")
    with patch("routes.tags.TagService") as MockSvc:
        MockSvc.return_value.create_tag.return_value = fake_tag
        resp = client.post("/tags", json={"name": "数学", "color": "#FF0000"},
                           headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "数学"

def test_get_question_404(client):
    with patch("routes.questions.QuestionService") as MockSvc:
        MockSvc.return_value.get_question.side_effect = KeyError("not found")
        resp = client.get("/questions/nonexistent", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 404
