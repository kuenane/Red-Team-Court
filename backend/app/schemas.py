from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentOut(BaseModel):
    id: int
    filename: str
    char_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class FindingOut(BaseModel):
    id: int
    agent_type: str
    claim: str
    category: Optional[str]
    severity_initial: Optional[int]
    evidence_quote: Optional[str]
    evidence_location: Optional[str]
    confidence: Optional[float]

    class Config:
        from_attributes = True


class DebateTurnOut(BaseModel):
    id: int
    round: int
    agent_type: str
    target_finding_id: Optional[int]
    stance: Optional[str]
    argument: str

    class Config:
        from_attributes = True


class FinalRiskOut(BaseModel):
    rank: int
    title: str
    category: Optional[str]
    severity_final: Optional[int]
    rationale: Optional[str]
    supporting_finding_ids: Optional[List[int]]

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: int
    document_id: int
    status: str
    overall_risk_score: Optional[float]
    executive_summary: Optional[str]
    findings: List[FindingOut] = []
    debate_turns: List[DebateTurnOut] = []
    final_risks: List[FinalRiskOut] = []
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class RunSummaryOut(BaseModel):
    id: int
    document_id: int
    status: str
    overall_risk_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
