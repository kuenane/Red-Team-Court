import pytest
from sqlalchemy import TypeDecorator, JSON

# PATCH ARRAY BEFORE ANY OTHER IMPORTS
class SQLiteARRAY(TypeDecorator):
    impl = JSON
    cache_ok = True
    def process_bind_param(self, value, dialect):
        return value
    def process_result_value(self, value, dialect):
        return value

import sqlalchemy
sqlalchemy.ARRAY = SQLiteARRAY
import sqlalchemy.dialects.postgresql as postgresql
postgresql.ARRAY = SQLiteARRAY

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.services import qwen_client
from unittest.mock import patch, AsyncMock

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with patch("backend.app.services.orchestrator.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_document():
    files = {"file": ("test.txt", b"this is some test content", "text/plain")}
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.txt"
    assert "id" in data

@patch("backend.app.services.qwen_client.chat_json", new_callable=AsyncMock)
def test_analyze_document(mock_chat_json):
    # Mock responses for attack, debate, and verdict phases
    mock_chat_json.side_effect = [
        # Attack Phase (5 agents)
        {"ok": True, "data": {"findings": [{"claim": "Risk 1", "category": "Fin", "severity": 8, "evidence_quote": "test", "evidence_location": "p1", "confidence": 0.9}]}},
        {"ok": True, "data": {"findings": [{"claim": "Risk 2", "category": "Leg", "severity": 7, "evidence_quote": "test", "evidence_location": "p1", "confidence": 0.8}]}},
        {"ok": True, "data": {"findings": [{"claim": "Risk 3", "category": "Comp", "severity": 6, "evidence_quote": "test", "evidence_location": "p1", "confidence": 0.7}]}},
        {"ok": True, "data": {"findings": [{"claim": "Risk 4", "category": "Mark", "severity": 5, "evidence_quote": "test", "evidence_location": "p1", "confidence": 0.6}]}},
        {"ok": True, "data": {"findings": [{"claim": "Risk 5", "category": "Exec", "severity": 4, "evidence_quote": "test", "evidence_location": "p1", "confidence": 0.5}]}},
    ] + [{"ok": True, "data": {"stance": "neutral", "argument": "I agree"}}] * 100 + [
        # Verdict Phase
        {"ok": True, "data": {
            "overall_risk_score": 75,
            "executive_summary": "High risk detected.",
            "final_risks": [{"title": "Risk Title", "category": "General", "severity_final": 8, "rationale": "Because...", "supporting_finding_ids": [1]}]
        }}
    ]

    # 1. Upload
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/api/v1/documents", files=files)
    doc_id = response.json()["id"]

    # 2. Start Analyze
    # We need to run the background task synchronously for testing or wait for it.
    # FastAPI's TestClient runs background tasks if we use the right approach.
    with patch("backend.app.services.orchestrator.SessionLocal", TestingSessionLocal):
        response = client.post(f"/api/v1/documents/{doc_id}/analyze")
        assert response.status_code == 202
        run_id = response.json()["id"]

        # 3. Check Run Status
        response = client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["id"] == run_id
