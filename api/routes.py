import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base_agent import BaseAgent
from agents.orchestrator import AgentOrchestrator
from auth.auth import get_current_user
from db.crud import (
    create_activity_log,
    create_case,
    delete_case,
    get_activity_logs,
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
_runtime_settings_path = Path("config/runtime_settings.json")
_default_runtime_settings = {
    "default_include_appeals": False,
    "retrieval_documents": 4,
    "reasoning_profile": "balanced",
    "evidence_highlight_limit": 8,
    "typing_speed_ms": 8,
    "auto_scroll_results": True,
    "show_keyword_highlights": True,
}


def _load_runtime_settings() -> dict[str, Any]:
    if _runtime_settings_path.exists():
        try:
            payload = json.loads(_runtime_settings_path.read_text(encoding="utf-8"))
            return {**_default_runtime_settings, **payload}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_default_runtime_settings)


def _save_runtime_settings(settings_payload: dict[str, Any]) -> dict[str, Any]:
    merged = {**_default_runtime_settings, **settings_payload}
    _runtime_settings_path.parent.mkdir(parents=True, exist_ok=True)
    _runtime_settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


_runtime_settings = _load_runtime_settings()


class AnalyzeRequest(BaseModel):
    case_description: str = Field(min_length=1)
    title: str | None = None
    include_appeals: bool = False


class KnowledgeDocumentRequest(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    content: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    source: str | None = None


class RuntimeSettingsRequest(BaseModel):
    default_include_appeals: bool | None = None
    retrieval_documents: int | None = Field(default=None, ge=1, le=10)
    reasoning_profile: str | None = None
    evidence_highlight_limit: int | None = Field(default=None, ge=1, le=20)
    typing_speed_ms: int | None = Field(default=None, ge=0, le=30)
    auto_scroll_results: bool | None = None
    show_keyword_highlights: bool | None = None


def _validate_case_text(case_description: str) -> str:
    text = case_description.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Case description cannot be empty")
    return text


def _safe_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _split_outputs(case) -> dict[str, str]:
    return {item.agent_name: item.content for item in case.agent_outputs}


def _serialize_activity(log) -> dict[str, Any]:
    return {
        "id": log.id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "description": log.description,
        "metadata": _safe_json(log.metadata_json, {}),
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _settings_payload() -> dict[str, Any]:
    return {
        **_runtime_settings,
        "reasoning_mode": "multi-agent-rag",
        "rule_based": False,
    }


def _validate_reasoning_profile(profile: str | None) -> str | None:
    if profile is None:
        return None
    normalized = profile.strip().lower()
    if normalized not in {"concise", "balanced", "detailed"}:
        raise HTTPException(status_code=400, detail="Reasoning profile must be concise, balanced, or detailed")
    return normalized


def _serialize_case(case) -> dict[str, Any]:
    outputs = _split_outputs(case)
    verdict = _safe_json(outputs.get("judge"), {})
    appeals = _safe_json(outputs.get("appeals"), None)
    evidence = _safe_json(outputs.get("evidence"), {"documents": []})
    rounds = _safe_json(outputs.get("rounds"), [])
    scoring = _safe_json(outputs.get("scoring"), {})
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
        "research": {
            "content": outputs.get("research", ""),
            "sources": evidence.get("documents", []),
        },
        "defense": {"content": outputs.get("defense", "")},
        "prosecution": {"content": outputs.get("prosecution", "")},
        "evidence": evidence,
        "rounds": rounds,
        "scoring": scoring,
        "verdict": verdict,
        "appeals": appeals,
        "agent_outputs": outputs,
    }


async def _persist_pipeline_result(db: AsyncSession, case_id: str, result: dict[str, Any]) -> None:
    await save_agent_output(db, case_id, "research", result["research"]["content"])
    await save_agent_output(db, case_id, "defense", result["defense"]["content"])
    await save_agent_output(db, case_id, "prosecution", result["prosecution"]["content"])
    await save_agent_output(db, case_id, "evidence", json.dumps(result.get("evidence", {})))
    await save_agent_output(db, case_id, "rounds", json.dumps(result.get("rounds", [])))
    await save_agent_output(db, case_id, "scoring", json.dumps(result.get("scoring", {})))

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


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "agents": ["research", "defense", "prosecution", "judge", "appeals"],
        "agent_backend": BaseAgent.describe_backend(),
        "rag_backend": _knowledge_base.describe_backend(),
        "reasoning_mode": "multi-agent-rag",
        "rule_based": False,
    }


@router.get("/", response_model=None)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/app/index.html", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return {
        "name": "LexAI API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


@router.get("/favicon.ico", status_code=status.HTTP_204_NO_CONTENT)
async def favicon() -> Response:
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
        retrieval_limit=int(_runtime_settings["retrieval_documents"]),
        reasoning_profile=str(_runtime_settings["reasoning_profile"]),
    )
    await _persist_pipeline_result(db, case.id, result)
    await create_activity_log(
        db,
        current_user.id,
        "case_submitted",
        f"Submitted case analysis for {case.title}",
        entity_type="case",
        entity_id=case.id,
        metadata={"title": case.title, "include_appeals": payload.include_appeals},
    )
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
    await create_activity_log(
        db,
        current_user.id,
        "case_submitted",
        f"Submitted case analysis for {case.title}",
        entity_type="case",
        entity_id=case.id,
        metadata={"title": case.title, "include_appeals": payload.include_appeals, "streaming": True},
    )
    stream_state: dict[str, Any] = {"rounds": []}

    async def event_stream():
        async for stage, data in _orchestrator.run_streaming(
            case_description,
            case_id=case.id,
            include_appeals=payload.include_appeals,
            retrieval_limit=int(_runtime_settings["retrieval_documents"]),
            reasoning_profile=str(_runtime_settings["reasoning_profile"]),
        ):
            if stage == "research":
                stream_state["research"] = data
                await save_agent_output(db, case.id, "research", data["content"])
            elif stage == "evidence":
                stream_state["evidence"] = data
                await save_agent_output(db, case.id, "evidence", json.dumps(data))
            elif stage == "round":
                stream_state["rounds"].append(data)
                await save_agent_output(db, case.id, f"round_{data['round']}", json.dumps(data))
            elif stage == "defense":
                stream_state["defense"] = data
                await save_agent_output(db, case.id, "defense", data["content"])
            elif stage == "prosecution":
                stream_state["prosecution"] = data
                await save_agent_output(db, case.id, "prosecution", data["content"])
            elif stage == "scoring":
                stream_state["scoring"] = data
                await save_agent_output(db, case.id, "scoring", json.dumps(data))
                await save_agent_output(db, case.id, "rounds", json.dumps(stream_state["rounds"]))
            elif stage == "judge":
                stream_state["verdict"] = data
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
                stream_state["appeals"] = data
                await save_agent_output(db, case.id, "appeals", json.dumps(data))

            yield f"data: {json.dumps({'stage': stage, 'data': data})}\n\n"

        yield f"data: {json.dumps({'stage': 'complete', 'data': {'case_id': case.id}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/cases")
async def list_cases(
    limit: int = 50,
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
    await create_activity_log(
        db,
        current_user.id,
        "case_loaded",
        f"Opened saved case {case.title}",
        entity_type="case",
        entity_id=case.id,
        metadata={"title": case.title},
    )
    return _serialize_case(case)


@router.get("/cases/{case_id}/evidence")
async def get_case_evidence(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case = await get_case_by_id(db, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    outputs = _split_outputs(case)
    evidence = _safe_json(outputs.get("evidence"), None)
    if evidence is None:
        docs = _knowledge_base.retrieve(case.case_description, limit=int(_runtime_settings["retrieval_documents"]))
        evidence = {
            "query": case.case_description,
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "citation": doc.citation,
                    "content": doc.content,
                    "keywords": list(doc.keywords),
                    "source": doc.source,
                    "score": round(float(doc.score), 4),
                }
                for doc in docs
            ],
        }
    return evidence


@router.get("/analytics/summary")
async def analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cases = await get_cases_for_user(db, current_user.id, limit=200, offset=0)
    activity_logs = await get_activity_logs(db, current_user.id, limit=250)
    completed_cases = [case for case in cases if case.ruling]
    verdict_distribution = Counter((case.ruling or "Pending") for case in completed_cases)
    confidences = [float(case.confidence) for case in completed_cases if case.confidence is not None]
    activity_counter = Counter(log.action for log in activity_logs)
    recent = [
        {
            "title": case.title,
            "ruling": case.ruling or "Pending",
            "confidence": float(case.confidence or 0),
            "created_at": case.created_at.isoformat() if case.created_at else None,
        }
        for case in cases[:8]
    ]
    return {
        "total_cases": len(cases),
        "completed_cases": len(completed_cases),
        "average_confidence": round(mean(confidences), 1) if confidences else 0.0,
        "verdict_distribution": dict(verdict_distribution),
        "recent_cases": recent,
        "activity_summary": dict(activity_counter),
        "activity_events": len(activity_logs),
        "report_downloads": activity_counter.get("report_downloaded", 0),
        "knowledge_documents": len(_knowledge_base.documents),
        "agent_backend": BaseAgent.describe_backend(),
        "rag_backend": _knowledge_base.describe_backend(),
        "system_settings": _settings_payload(),
    }


@router.delete("/cases/{case_id}", status_code=204)
async def remove_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    case = await get_case_by_id(db, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    deleted = await delete_case(db, case_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    await create_activity_log(
        db,
        current_user.id,
        "case_deleted",
        f"Deleted case {case.title}",
        entity_type="case",
        entity_id=case.id,
        metadata={"title": case.title},
    )
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

    pdf_bytes = generate_case_pdf(case, _split_outputs(case))
    await create_activity_log(
        db,
        current_user.id,
        "report_downloaded",
        f"Downloaded PDF report for {case.title}",
        entity_type="case",
        entity_id=case.id,
        metadata={"title": case.title},
    )
    headers = {"Content-Disposition": f'attachment; filename="lexai_{case.id[:8]}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/activity/logs")
async def activity_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    logs = await get_activity_logs(db, current_user.id, limit=max(1, min(limit, 200)))
    return {"logs": [_serialize_activity(item) for item in logs]}


@router.get("/knowledge/documents")
async def knowledge_documents(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "documents": _knowledge_base.list_documents(),
        "editable": True,
        "rule_based": False,
    }


@router.post("/knowledge/documents")
async def save_knowledge_document(
    payload: KnowledgeDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        document = _knowledge_base.upsert_document(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await create_activity_log(
        db,
        current_user.id,
        "knowledge_updated",
        f"Updated knowledge document {document['title']}",
        entity_type="knowledge_document",
        entity_id=str(document["id"]),
        metadata={"citation": document["citation"]},
    )
    return {"document": document, "documents": _knowledge_base.list_documents()}


@router.delete("/knowledge/documents/{doc_id}", status_code=204)
async def delete_knowledge_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    existing = next((item for item in _knowledge_base.list_documents() if str(item["id"]) == doc_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    deleted = _knowledge_base.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    await create_activity_log(
        db,
        current_user.id,
        "knowledge_deleted",
        f"Deleted knowledge document {existing['title']}",
        entity_type="knowledge_document",
        entity_id=doc_id,
        metadata={"citation": existing["citation"]},
    )
    return Response(status_code=204)


@router.get("/system/settings")
async def get_system_settings(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return _settings_payload()


@router.put("/system/settings")
async def update_system_settings(
    payload: RuntimeSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    updates = payload.model_dump(exclude_none=True)
    if "reasoning_profile" in updates:
        updates["reasoning_profile"] = _validate_reasoning_profile(updates["reasoning_profile"])
    _runtime_settings.update(updates)
    saved = _save_runtime_settings(_runtime_settings)
    await create_activity_log(
        db,
        current_user.id,
        "settings_updated",
        "Updated system settings",
        entity_type="system_settings",
        metadata=updates,
    )
    return {**saved, "reasoning_mode": "multi-agent-rag", "rule_based": False}
