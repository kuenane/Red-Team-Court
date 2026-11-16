"""Runs the full RedTeam Court pipeline for a single analysis run:

  1. ATTACK   — 5 agents analyze the document in parallel (asyncio.gather)
  2. DEBATE   — each agent's top findings get cross-examined by the other 4
  3. VERDICT  — a Judge agent synthesizes a final severity-scored report

Progress is published to the in-process event bus so the frontend's SSE
stream can show a live "courtroom" view.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..config import settings
from ..database import SessionLocal
from ..models import AnalysisRun, AgentFinding, DebateTurn, FinalRisk
from . import qwen_client, events
from .agents import AGENT_TYPES, PERSONAS, ATTACK_INSTRUCTIONS, DEBATE_INSTRUCTIONS, JUDGE_SYSTEM, JUDGE_INSTRUCTIONS

logger = logging.getLogger(__name__)


async def _run_attack(agent_type: str, document_text: str) -> dict:
    persona = PERSONAS[agent_type]
    prompt = ATTACK_INSTRUCTIONS.format(document_text=document_text[: settings.max_upload_chars])
    result = await qwen_client.chat_json(persona["system"], prompt)
    return {"agent_type": agent_type, **result}


async def _attack_phase(db: Session, run: AnalysisRun, document_text: str) -> list[AgentFinding]:
    await events.publish(run.id, {"phase": "attacking", "message": "Five agents are reviewing the document..."})

    results = await asyncio.gather(*[_run_attack(a, document_text) for a in AGENT_TYPES])

    all_findings: list[AgentFinding] = []
    for res in results:
        agent_type = res["agent_type"]
        if not res.get("ok"):
            await events.publish(run.id, {"phase": "attacking", "agent": agent_type, "error": res.get("error")})
            continue
        for f in res["data"].get("findings", []):
            finding = AgentFinding(
                run_id=run.id, agent_type=agent_type, claim=f.get("claim", ""),
                category=f.get("category"), severity_initial=f.get("severity"),
                evidence_quote=f.get("evidence_quote"), evidence_location=f.get("evidence_location"),
                confidence=f.get("confidence"),
            )
            db.add(finding)
            db.flush()  # get finding.id without committing yet
            all_findings.append(finding)
            await events.publish(run.id, {
                "phase": "attacking", "agent": agent_type, "finding_id": finding.id,
                "claim": finding.claim, "severity": finding.severity_initial,
            })
    db.commit()
    return all_findings


async def _run_debate_turn(reacting_agent: str, target: AgentFinding) -> dict:
    persona = PERSONAS[reacting_agent]
    prompt = DEBATE_INSTRUCTIONS.format(
        other_agent=PERSONAS[target.agent_type]["label"], other_category=target.category or "general",
        severity=target.severity_initial, claim=target.claim, evidence_quote=target.evidence_quote or "",
    )
    result = await qwen_client.chat_json(persona["system"], prompt, max_tokens=400)
    return {"agent_type": reacting_agent, "target_finding_id": target.id, **result}


async def _debate_phase(db: Session, run: AnalysisRun, findings: list[AgentFinding]) -> None:
    await events.publish(run.id, {"phase": "debating", "message": "Agents are cross-examining findings..."})

    # top N findings per agent by severity carry into debate
    by_agent: dict[str, list[AgentFinding]] = {a: [] for a in AGENT_TYPES}
    for f in findings:
        by_agent[f.agent_type].append(f)
    top_findings: list[AgentFinding] = []
    for a, flist in by_agent.items():
        flist.sort(key=lambda x: (x.severity_initial or 0), reverse=True)
        top_findings.extend(flist[: settings.debate_top_n_per_agent])

    tasks = []
    for target in top_findings:
        for reacting_agent in AGENT_TYPES:
            if reacting_agent == target.agent_type:
                continue
            tasks.append(_run_debate_turn(reacting_agent, target))

    results = await asyncio.gather(*tasks)
    for res in results:
        if not res.get("ok"):
            continue
        turn = DebateTurn(
            run_id=run.id, round=1, agent_type=res["agent_type"],
            target_finding_id=res["target_finding_id"],
            stance=res["data"].get("stance"), argument=res["data"].get("argument", ""),
        )
        db.add(turn)
        db.flush()
        await events.publish(run.id, {
            "phase": "debating", "agent": res["agent_type"], "target_finding_id": res["target_finding_id"],
            "stance": turn.stance, "argument": turn.argument,
        })
    db.commit()


async def _verdict_phase(db: Session, run: AnalysisRun, findings: list[AgentFinding], debate_turns: list[DebateTurn]) -> None:
    await events.publish(run.id, {"phase": "judging", "message": "The Judge is weighing the evidence..."})

    findings_json = [
        {"id": f.id, "agent": f.agent_type, "claim": f.claim, "category": f.category, "severity": f.severity_initial}
        for f in findings
    ]
    debate_json = [
        {"agent": t.agent_type, "target_finding_id": t.target_finding_id, "stance": t.stance, "argument": t.argument}
        for t in debate_turns
    ]
    prompt = JUDGE_INSTRUCTIONS.format(findings_json=findings_json, debate_json=debate_json)
    result = await qwen_client.chat_json(JUDGE_SYSTEM, prompt, max_tokens=2500)

    if not result.get("ok"):
        run.status = "failed"
        run.error_message = result.get("error")
        db.commit()
        await events.publish(run.id, {"phase": "failed", "error": result.get("error")})
        return

    data = result["data"]
    run.overall_risk_score = data.get("overall_risk_score")
    run.executive_summary = data.get("executive_summary")
    run.status = "complete"
    run.completed_at = datetime.utcnow()

    for i, risk in enumerate(data.get("final_risks", []), start=1):
        db.add(FinalRisk(
            run_id=run.id, rank=i, title=risk.get("title", ""), category=risk.get("category"),
            severity_final=risk.get("severity_final"), rationale=risk.get("rationale"),
            supporting_finding_ids=risk.get("supporting_finding_ids", []),
        ))
    db.commit()
    await events.publish(run.id, {
        "phase": "complete", "overall_risk_score": run.overall_risk_score,
        "executive_summary": run.executive_summary,
    })


async def run_pipeline(run_id: int):
    """Entry point invoked as a FastAPI BackgroundTask."""
    db = SessionLocal()
    try:
        run = db.get(AnalysisRun, run_id)
        document_text = run.document.raw_text

        run.status = "attacking"
        db.commit()
        findings = await _attack_phase(db, run, document_text)

        if not findings:
            msg = "No agent produced findings; check the model API key and logs"
            run.status = "failed"
            run.error_message = msg
            db.commit()
            await events.publish(run_id, {"phase": "failed", "error": msg})
            return

        run.status = "debating"
        db.commit()
        await _debate_phase(db, run, findings)
        debate_turns = db.query(DebateTurn).filter_by(run_id=run_id).all()

        run.status = "judging"
        db.commit()
        await _verdict_phase(db, run, findings, debate_turns)
    except Exception as exc:  # noqa: BLE001
        logger.exception("pipeline failed for run %s", run_id)
        run = db.get(AnalysisRun, run_id)
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        await events.publish(run_id, {"phase": "failed", "error": str(exc)})
    finally:
        db.close()
