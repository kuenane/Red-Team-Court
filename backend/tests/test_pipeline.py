import asyncio
from unittest.mock import patch

from backend.app import models
from backend.app.services.agents import AGENT_TYPES, JUDGE_SYSTEM, PERSONAS
from backend.app.services.orchestrator import run_pipeline

SYSTEM_TO_AGENT = {p["system"]: a for a, p in PERSONAS.items()}


def make_fake_chat(fail_agent=None, fail_judge=False):
    async def fake_chat_json(system_prompt, user_prompt, max_tokens=2000):
        if system_prompt == JUDGE_SYSTEM:
            if fail_judge:
                return {"ok": False, "error": "judge down"}
            return {"ok": True, "data": {
                "overall_risk_score": 75,
                "executive_summary": "High risk detected.",
                "final_risks": [{
                    "title": "Risk Title", "category": "General", "severity_final": 8,
                    "rationale": "Because.", "supporting_finding_ids": [1],
                }],
            }}
        if "FINDING FROM" in user_prompt:
            return {"ok": True, "data": {"stance": "support", "argument": "Agreed."}}
        agent = SYSTEM_TO_AGENT[system_prompt]
        if agent == fail_agent:
            return {"ok": False, "error": "agent down"}
        return {"ok": True, "data": {"findings": [{
            "claim": f"{agent} risk", "category": "cat", "severity": 6,
            "evidence_quote": "quote", "evidence_location": "p1", "confidence": 0.7,
        }]}}
    return fake_chat_json


def seed_run(db):
    doc = models.Document(filename="d.txt", mime_type="text/plain", raw_text="some plan", char_count=9)
    db.add(doc)
    db.commit()
    run = models.AnalysisRun(document_id=doc.id, status="pending")
    db.add(run)
    db.commit()
    return run.id


def run_with(fake, db_session):
    run_id = seed_run(db_session)
    with patch("backend.app.services.qwen_client.chat_json", fake):
        asyncio.run(run_pipeline(run_id))
    db_session.expire_all()
    return db_session.get(models.AnalysisRun, run_id)


def test_pipeline_completes_and_persists(db_session):
    run = run_with(make_fake_chat(), db_session)
    assert run.status == "complete"
    assert float(run.overall_risk_score) == 75
    assert len(run.findings) == len(AGENT_TYPES)
    # each agent's finding is cross-examined by the other four
    assert len(run.debate_turns) == len(AGENT_TYPES) * (len(AGENT_TYPES) - 1)
    assert len(run.final_risks) == 1
    assert run.final_risks[0].rank == 1


def test_pipeline_survives_one_failed_agent(db_session):
    run = run_with(make_fake_chat(fail_agent="legal"), db_session)
    assert run.status == "complete"
    assert {f.agent_type for f in run.findings} == set(AGENT_TYPES) - {"legal"}


def test_pipeline_marks_failed_when_judge_fails(db_session):
    run = run_with(make_fake_chat(fail_judge=True), db_session)
    assert run.status == "failed"
    assert run.error_message == "judge down"


def test_analyze_endpoint_runs_pipeline_to_completion(client):
    doc_id = client.post(
        "/api/v1/documents", files={"file": ("p.txt", b"our plan", "text/plain")}
    ).json()["id"]
    with patch("backend.app.services.qwen_client.chat_json", make_fake_chat()):
        resp = client.post(f"/api/v1/documents/{doc_id}/analyze")
        assert resp.status_code == 202
        run_id = resp.json()["id"]

    body = client.get(f"/api/v1/runs/{run_id}").json()
    assert body["status"] == "complete"
    assert len(body["findings"]) == len(AGENT_TYPES)
    assert len(body["final_risks"]) == 1


def test_sse_closes_immediately_for_finished_run(client):
    doc_id = client.post(
        "/api/v1/documents", files={"file": ("p.txt", b"our plan", "text/plain")}
    ).json()["id"]
    with patch("backend.app.services.qwen_client.chat_json", make_fake_chat()):
        run_id = client.post(f"/api/v1/documents/{doc_id}/analyze").json()["id"]

    resp = client.get(f"/api/v1/runs/{run_id}/events")
    assert resp.status_code == 200
    assert '"phase": "complete"' in resp.text


def test_pipeline_fails_fast_when_every_agent_fails(db_session):
    async def all_down(system_prompt, user_prompt, max_tokens=2000):
        assert system_prompt != JUDGE_SYSTEM, "judge must not run with zero findings"
        return {"ok": False, "error": "no key"}

    run = run_with(all_down, db_session)
    assert run.status == "failed"
    assert "No agent produced findings" in run.error_message
