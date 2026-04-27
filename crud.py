"""
db/crud.py
==========
All database read/write operations (CRUD).
Keeps raw SQL/ORM logic out of routes and agents.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import ActivityLog, User, Case, CaseAgentOutput


# ═══════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, username: str, email: str, hashed_password: str
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.flush()
    return user


# ═══════════════════════════════════════════════════════
# CASES
# ═══════════════════════════════════════════════════════

async def create_case(
    db: AsyncSession,
    user_id: str,
    case_description: str,
    title: Optional[str] = None,
) -> Case:
    """Create a new case record (before pipeline runs)."""
    # Auto-generate title from first 80 chars if not provided
    auto_title = title or (
        case_description[:77] + "..." if len(case_description) > 80 else case_description
    )
    case = Case(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=auto_title,
        case_description=case_description,
    )
    db.add(case)
    await db.flush()
    return case


async def update_case_verdict(
    db: AsyncSession,
    case_id: str,
    ruling: str,
    confidence: float,
    reasoning: str,
    key_finding: str,
) -> None:
    """Populate verdict fields once Judge agent completes."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if case:
        case.ruling       = ruling
        case.confidence   = confidence
        case.reasoning    = reasoning
        case.key_finding  = key_finding
        case.completed_at = datetime.utcnow()
        await db.flush()


async def save_agent_output(
    db: AsyncSession,
    case_id: str,
    agent_name: str,
    content: str,
) -> CaseAgentOutput:
    """Save one agent's output for a case."""
    output = CaseAgentOutput(
        case_id=case_id,
        agent_name=agent_name,
        content=content,
    )
    db.add(output)
    await db.flush()
    return output


async def get_case_by_id(db: AsyncSession, case_id: str) -> Optional[Case]:
    """Fetch a case with all agent outputs eagerly loaded."""
    result = await db.execute(
        select(Case)
        .options(selectinload(Case.agent_outputs))
        .where(Case.id == case_id)
    )
    return result.scalar_one_or_none()


async def get_cases_for_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> List[Case]:
    """List all cases for a user, newest first."""
    result = await db.execute(
        select(Case)
        .where(Case.user_id == user_id)
        .order_by(desc(Case.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def delete_case(db: AsyncSession, case_id: str, user_id: str) -> bool:
    """Delete a case (only if it belongs to the user)."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        return False
    await db.delete(case)
    await db.flush()
    return True


async def create_activity_log(
    db: AsyncSession,
    user_id: str,
    action: str,
    description: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(log)
    await db.flush()
    return log


async def get_activity_logs(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
) -> List[ActivityLog]:
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.user_id == user_id)
        .order_by(desc(ActivityLog.created_at), desc(ActivityLog.id))
        .limit(limit)
    )
    return list(result.scalars().all())
