import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine
from app.models.domain import TripleItem, ProjectCreate

Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_llm_providers():
    response = client.get("/api/v1/llm/providers")
    assert response.status_code == 200
    providers = response.json()
    assert any(p["name"] == "LM Studio" for p in providers)
    assert any(p["name"] == "OpenRouter" for p in providers)

def test_project_crud():
    # Create
    create_res = client.post("/api/v1/projects", json={"name": "Test Project", "description": "Unit test"})
    assert create_res.status_code == 200
    proj_id = create_res.json()["id"]

    # Read
    get_res = client.get(f"/api/v1/projects/{proj_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Project"

    # Delete
    del_res = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_res.status_code == 200

    # Verify deleted
    verify_res = client.get(f"/api/v1/projects/{proj_id}")
    assert verify_res.status_code == 404
