import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base_agent import BaseAgent
from agents.orchestrator import AgentOrchestrator
from auth.auth import get_current_user
from db.crud import (
    create_case,
    delete_case,
    get_case_by_id,
    get_cases_for_user,
    save_agent_output,
    update_case_verdict,
)
from db.database import get_db
from db.models import User
from middleware.rate_limit import limiter
from pdf_exporter import generate_case_pdf
from rag.knowledge_base import LegalKnowledgeBase

router = APIRouter(tags=["cases"])

_knowledge_base = LegalKnowledgeBase()
_orchestrator = AgentOrchestrator(_knowledge_base)


class AnalyzeRequest(BaseModel):
    case_description: str = Field(min_length=1)
    title: str | None = None
    include_appeals: bool = False


def _validate_case_text(case_description: str) -> str:
    text = case_description.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Case description cannot be empty")
    return text


async def _persist_pipeline_result(
    db: AsyncSession,
    case_id: str,
    result: dict[str, Any],
) -> None:
    for agent_name in ("research", "defense", "prosecution"):
        if agent_name in result:
            await save_agent_output(db, case_id, agent_name, result[agent_name]["content"])

    verdict = result["verdict"]
    await save_agent_output(db, case_id, "judge", json.dumps(verdict))
    await update_case_verdict(
        db,
        case_id,
        verdict["ruling"],
        float(verdict["confidence"]),
        verdict["reasoning"],
        verdict["key_finding"],
    )

    if "appeals" in result:
        await save_agent_output(db, case_id, "appeals", json.dumps(result["appeals"]))


def _serialize_case(case) -> dict[str, Any]:
    outputs = {item.agent_name: item.content for item in case.agent_outputs}
    return {
        "id": case.id,
        "title": case.title,
        "case_description": case.case_description,
        "ruling": case.ruling,
        "confidence": case.confidence,
        "reasoning": case.reasoning,
        "key_finding": case.key_finding,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "completed_at": case.completed_at.isoformat() if case.completed_at else None,
        "agent_outputs": outputs,
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "agents": ["research", "defense", "prosecution", "judge", "appeals"],
        "agent_backend": BaseAgent.describe_backend(),
        "rag_backend": _knowledge_base.describe_backend(),
    }


@router.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "LexAI API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


@router.get("/favicon.ico", status_code=status.HTTP_204_NO_CONTENT)
async def favicon() -> Response:
    # Browsers request this automatically; return an empty success response
    # so local development logs do not show a misleading 404.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_case(
    request: Request,
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case_description = _validate_case_text(payload.case_description)
    case = await create_case(db, current_user.id, case_description, payload.title)

    result = await _orchestrator.run(
        case_description,
        case_id=case.id,
        include_appeals=payload.include_appeals,
    )
    await _persist_pipeline_result(db, case.id, result)
    return {**result, "case_id": case.id}


@router.post("/analyze/stream")
@limiter.limit("10/minute")
async def analyze_case_stream(
    request: Request,
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    case_description = _validate_case_text(payload.case_description)
    case = await create_case(db, current_user.id, case_description, payload.title)

    async def event_stream():
        verdict = None
        async for stage, data in _orchestrator.run_streaming(
            case_description,
            case_id=case.id,
            include_appeals=payload.include_appeals,
        ):
            if stage in {"research", "defense", "prosecution"}:
                await save_agent_output(db, case.id, stage, data["content"])
            elif stage == "judge":
                verdict = data
                await save_agent_output(db, case.id, "judge", json.dumps(data))
                await update_case_verdict(
                    db,
                    case.id,
                    data["ruling"],
                    float(data["confidence"]),
                    data["reasoning"],
                    data["key_finding"],
                )
            elif stage == "appeals":
                await save_agent_output(db, case.id, "appeals", json.dumps(data))

            yield f"data: {json.dumps({'stage': stage, 'data': data})}\n\n"

        yield f"data: {json.dumps({'stage': 'complete', 'data': {'case_id': case.id}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/cases")
async def list_cases(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cases = await get_cases_for_user(db, current_user.id, limit=limit, offset=offset)
    return {
        "cases": [
            {
                "id": case.id,
                "title": case.title,
                "ruling": case.ruling,
                "confidence": case.confidence,
                "created_at": case.created_at.isoformat() if case.created_at else None,
            }
            for case in cases
        ]
    }


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case = await get_case_by_id(db, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize_case(case)


@router.delete("/cases/{case_id}", status_code=204)
async def remove_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await delete_case(db, case_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    return Response(status_code=204)


@router.get("/cases/{case_id}/pdf")
async def download_case_pdf(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    case = await get_case_by_id(db, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")

    pdf_bytes = generate_case_pdf(case, {item.agent_name: item.content for item in case.agent_outputs})
    headers = {"Content-Disposition": f'attachment; filename="lexai_{case.id[:8]}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
