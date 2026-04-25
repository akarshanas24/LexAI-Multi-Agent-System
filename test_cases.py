"""
tests/test_cases.py
===================
Tests for case management endpoints and pipeline integration.
Uses monkeypatching to mock the LLM orchestrator — no real API calls.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


# ── Mocked pipeline output ─────────────────────────────
MOCK_RESULT = {
    "research":    {"content": "• Contract Law\n• Breach of contract\n• UCC § 2-301\n• Preponderance\n• Hadley v Baxendale"},
    "defense":     {"content": "• No intentional breach\n• Claimant failed to mitigate\n• Terms were ambiguous\n• Substantial performance complete"},
    "prosecution": {"content": "• Clear terms\n• Full consideration received\n• Documented damages\n• Written obligations confirmed"},
    "verdict":     {"ruling": "Liable", "confidence": 72,
                    "reasoning": "Weight of evidence supports liability given written communications.",
                    "key_finding": "Written communications confirm the defendant's obligations."},
    "case_id":     "mock-case-id",
}

MOCK_STREAM_STAGES = [
    ("research",    MOCK_RESULT["research"]),
    ("defense",     MOCK_RESULT["defense"]),
    ("prosecution", MOCK_RESULT["prosecution"]),
    ("judge",       MOCK_RESULT["verdict"]),
    ("complete",    {"case_id": "mock-case-id"}),
]


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "research" in data["agents"]
        assert "appeals" in data["agents"]


@pytest.mark.asyncio
class TestAnalyze:

    async def test_analyze_requires_auth(self, client):
        """Unauthenticated requests must be rejected."""
        r = await client.post("/analyze", json={"case_description": "Some case"})
        assert r.status_code == 401

    async def test_analyze_empty_description(self, auth_client):
        r = await auth_client.post("/analyze", json={"case_description": "   "})
        assert r.status_code == 400

    async def test_analyze_full_pipeline(self, auth_client):
        """Mock the orchestrator and verify the full response shape."""
        with patch("api.routes._orchestrator") as mock_orch:
            mock_orch.run = AsyncMock(return_value=MOCK_RESULT)
            r = await auth_client.post("/analyze", json={
                "case_description": "A developer was accused of stealing code.",
                "title": "Code Theft Test"
            })
        assert r.status_code == 200
        data = r.json()
        assert "research" in data
        assert "defense" in data
        assert "prosecution" in data
        assert "verdict" in data
        assert data["verdict"]["ruling"] == "Liable"
        assert isinstance(data["verdict"]["confidence"], (int, float))
        assert "case_id" in data


@pytest.mark.asyncio
class TestCaseHistory:

    async def _create_case(self, auth_client) -> str:
        """Helper: create a case via the analyze endpoint and return its ID."""
        with patch("api.routes._orchestrator") as mock_orch:
            mock_orch.run = AsyncMock(return_value=MOCK_RESULT)
            r = await auth_client.post("/analyze", json={
                "case_description": "Employee sued for trade secret misappropriation.",
                "title": "Trade Secret Case"
            })
        assert r.status_code == 200
        return r.json()["case_id"]

    async def test_list_cases_empty(self, auth_client):
        r = await auth_client.get("/cases")
        assert r.status_code == 200
        assert r.json()["cases"] == []

    async def test_list_cases_after_analysis(self, auth_client):
        await self._create_case(auth_client)
        r = await auth_client.get("/cases")
        assert r.status_code == 200
        assert len(r.json()["cases"]) == 1

    async def test_get_case_by_id(self, auth_client):
        case_id = await self._create_case(auth_client)
        r = await auth_client.get(f"/cases/{case_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == case_id
        assert "agent_outputs" in data
        assert "research" in data["agent_outputs"]

    async def test_get_case_not_found(self, auth_client):
        r = await auth_client.get("/cases/nonexistent-id")
        assert r.status_code == 404

    async def test_delete_case(self, auth_client):
        case_id = await self._create_case(auth_client)
        r = await auth_client.delete(f"/cases/{case_id}")
        assert r.status_code == 204
        # Confirm it's gone
        r2 = await auth_client.get(f"/cases/{case_id}")
        assert r2.status_code == 404

    async def test_delete_nonexistent_case(self, auth_client):
        r = await auth_client.delete("/cases/does-not-exist")
        assert r.status_code == 404

    async def test_cannot_access_another_users_case(self, auth_client, client):
        """A user should not be able to access another user's case."""
        case_id = await self._create_case(auth_client)

        # Register and login as a second user
        await client.post("/auth/register", json={
            "username": "user2", "email": "user2@lexai.dev", "password": "pass12345"
        })
        login = await client.post("/auth/login", data={"username": "user2", "password": "pass12345"})
        token2 = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token2}"})

        r = await client.get(f"/cases/{case_id}")
        assert r.status_code == 404   # should not see another user's case


@pytest.mark.asyncio
class TestRAGRetrieval:

    async def test_retrieval_returns_relevant_docs(self):
        """Verify the RAG layer returns results for legal queries."""
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("employee stole trade secrets from company")
        assert len(docs) > 0
        assert len(docs) <= 3  # respects TOP_K_DOCS default

    async def test_retrieval_contract_case(self):
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("breach of contract payment dispute")
        titles = [d.title for d in docs]
        # Contract Law doc should rank highly for contract query
        assert any("Contract" in t for t in titles)

    async def test_format_context_non_empty(self):
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("fraud financial advisor")
        ctx = kb.format_context(docs)
        assert len(ctx) > 50
        assert "Citation:" in ctx
