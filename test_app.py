import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"

def test_create_and_get_task(client):
    post_res = client.post("/tasks", json={"title": "CI Pipeline Test"})
    assert post_res.status_code == 201
    get_res = client.get("/tasks")
    assert any(t["title"] == "CI Pipeline Test" for t in get_res.get_json())
