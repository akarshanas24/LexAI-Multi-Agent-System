"""
db/models.py
============
SQLAlchemy ORM models for LexAI.

Tables:
    users       — Registered users (for auth)
    cases       — Submitted legal cases with full pipeline results
    case_agents — Individual agent outputs per case (one row per agent)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Float, Integer,
    DateTime, ForeignKey, Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Users ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str]           = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str]     = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str]        = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool]   = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="user", cascade="all, delete-orphan")


# ── Cases ──────────────────────────────────────────────
class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str]                = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str]           = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str]             = mapped_column(String(256), nullable=False)
    case_description: Mapped[str]  = mapped_column(Text, nullable=False)

    # Verdict summary (denormalised for fast listing)
    ruling: Mapped[str | None]     = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    reasoning: Mapped[str | None]  = mapped_column(Text)
    key_finding: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"]           = relationship("User", back_populates="cases")
    agent_outputs: Mapped[list["CaseAgentOutput"]] = relationship(
        "CaseAgentOutput", back_populates="case", cascade="all, delete-orphan"
    )


# ── Per-Agent Outputs ──────────────────────────────────
class CaseAgentOutput(Base):
    __tablename__ = "case_agent_outputs"

    id: Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str]  = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)  # research/defense/prosecution/judge/appeals
    content: Mapped[str]  = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["Case"]  = relationship("Case", back_populates="agent_outputs")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
