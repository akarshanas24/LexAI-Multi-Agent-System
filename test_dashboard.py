import json
from unittest.mock import AsyncMock, patch

import pytest

from rag.knowledge_base import LegalKnowledgeBase


MOCK_RESULT = {
    "research": {"content": "Research summary"},
    "defense": {"content": "Defense summary"},
    "prosecution": {"content": "Prosecution summary"},
    "evidence": {"documents": []},
    "rounds": [],
    "scoring": {"defense_score": 54, "prosecution_score": 63, "stronger_side": "prosecution"},
    "verdict": {
        "ruling": "Liable",
        "confidence": 72,
        "reasoning": "Reasoning",
        "key_finding": "Key finding",
        "winning_side": "prosecution",
        "cited_basis": "IPC Section 420",
    },
}


@pytest.mark.asyncio
class TestDashboardFeatures:
    async def test_activity_logs_capture_case_submission(self, auth_client):
        with patch("api.routes._orchestrator") as mock_orch:
            mock_orch.run = AsyncMock(return_value=MOCK_RESULT)
            response = await auth_client.post("/analyze", json={
                "case_description": "A cheating complaint involving inducement and delivery of funds.",
                "title": "Cheating Case",
            })

        assert response.status_code == 200
        logs = await auth_client.get("/activity/logs")
        assert logs.status_code == 200
        payload = logs.json()["logs"]
        assert any(item["action"] == "case_submitted" for item in payload)

    async def test_system_settings_round_trip(self, auth_client, tmp_path):
        import api.routes as api_routes

        temp_settings = tmp_path / "runtime_settings.json"
        with patch.object(api_routes, "_runtime_settings_path", temp_settings), \
             patch.object(api_routes, "_runtime_settings", dict(api_routes._default_runtime_settings)):
            response = await auth_client.put("/system/settings", json={
                "default_include_appeals": True,
                "retrieval_documents": 5,
                "reasoning_profile": "detailed",
                "evidence_highlight_limit": 6,
                "typing_speed_ms": 4,
                "auto_scroll_results": False,
                "show_keyword_highlights": True,
            })

            assert response.status_code == 200
            body = response.json()
            assert body["retrieval_documents"] == 5
            assert body["reasoning_profile"] == "detailed"
            assert body["rule_based"] is False

            fetched = await auth_client.get("/system/settings")
            assert fetched.status_code == 200
            assert fetched.json()["retrieval_documents"] == 5

    async def test_knowledge_document_crud(self, auth_client, tmp_path):
        import api.routes as api_routes

        corpus_path = tmp_path / "legal_corpus.json"
        corpus_path.write_text(json.dumps([
            {
                "id": "ipc-420",
                "title": "IPC Section 420",
                "citation": "Indian Penal Code - Section 420",
                "content": "Cheating and dishonestly inducing delivery of property.",
                "keywords": ["ipc 420", "cheating"],
                "source": "Indian Penal Code",
            }
        ]), encoding="utf-8")
        temp_kb = LegalKnowledgeBase(corpus_path)

        with patch.object(api_routes, "_knowledge_base", temp_kb):
            created = await auth_client.post("/knowledge/documents", json={
                "title": "IPC Section 406",
                "citation": "Indian Penal Code - Section 406",
                "content": "Punishment for criminal breach of trust.",
                "keywords": ["ipc 406", "breach of trust"],
                "source": "Indian Penal Code",
            })
            assert created.status_code == 200
            document = created.json()["document"]
            assert document["title"] == "IPC Section 406"

            listed = await auth_client.get("/knowledge/documents")
            assert listed.status_code == 200
            assert len(listed.json()["documents"]) == 2

            deleted = await auth_client.delete(f"/knowledge/documents/{document['id']}")
            assert deleted.status_code == 204
