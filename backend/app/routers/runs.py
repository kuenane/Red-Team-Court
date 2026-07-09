import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..services import events
from ..services.orchestrator import run_pipeline

router = APIRouter(prefix="/api/v1", tags=["runs"])


@router.post("/documents/{document_id}/analyze", response_model=schemas.RunSummaryOut, status_code=202)
def start_run(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    document = db.get(models.Document, document_id)
    if not document:
        raise HTTPException(404, "document not found")

    run = models.AnalysisRun(document_id=document_id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(run_pipeline, run.id)
    return run





@router.get("/runs/{run_id}", response_model=schemas.RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(models.AnalysisRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.get("/runs", response_model=list[schemas.RunSummaryOut])
def list_runs(db: Session = Depends(get_db)):
    return db.query(models.AnalysisRun).order_by(models.AnalysisRun.created_at.desc()).all()


@router.get("/runs/{run_id}/events")
async def run_events(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(models.AnalysisRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")

    queue = events.subscribe(run_id)

    async def event_generator():
        try:
            # Replay current status immediately so late subscribers aren't lost
            yield {"event": "status", "data": json.dumps({"status": run.status})}
            while True:
                if await request.is_disconnected():
                    break
                event = await queue.get()
                yield {"event": "update", "data": json.dumps(event)}
                if event.get("phase") in ("complete", "failed"):
                    break
        finally:
            events.unsubscribe(run_id, queue)

    return EventSourceResponse(event_generator())
