from sqlalchemy import (
    Column, Integer, String, Text, SmallInteger, ForeignKey, TIMESTAMP, Numeric, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(64))
    raw_text = Column(Text, nullable=False)
    char_count = Column(Integer)
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    runs = relationship("AnalysisRun", backref="document", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    status = Column(String(24), default="pending")
    overall_risk_score = Column(Numeric(5, 2))
    executive_summary = Column(Text)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))

    findings = relationship("AgentFinding", backref="run", cascade="all, delete-orphan")
    debate_turns = relationship("DebateTurn", backref="run", cascade="all, delete-orphan")
    final_risks = relationship("FinalRisk", backref="run", cascade="all, delete-orphan")


class AgentFinding(Base):
    __tablename__ = "agent_findings"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    agent_type = Column(String(24), nullable=False)
    claim = Column(Text, nullable=False)
    category = Column(String(64))
    severity_initial = Column(SmallInteger)
    evidence_quote = Column(Text)
    evidence_location = Column(Text)
    confidence = Column(Numeric(3, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class DebateTurn(Base):
    __tablename__ = "debate_turns"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    round = Column(SmallInteger, default=1)
    agent_type = Column(String(24), nullable=False)
    target_finding_id = Column(Integer, ForeignKey("agent_findings.id", ondelete="CASCADE"))
    stance = Column(String(12))
    argument = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class FinalRisk(Base):
    __tablename__ = "final_risks"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    rank = Column(SmallInteger, nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(64))
    severity_final = Column(SmallInteger)
    rationale = Column(Text)
    supporting_finding_ids = Column(ARRAY(Integer))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
