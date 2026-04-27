"""tests/test_agents.py — Unit tests for all agents (LLM calls mocked)"""
import pytest, json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestJudgeAgent:

    async def test_parses_valid_verdict(self):
        from agents.judge_agent import JudgeAgent
        agent = JudgeAgent()
        mock = json.dumps({"ruling":"Liable","confidence":75,"reasoning":"Evidence supports liability.","key_finding":"Files retained."})
        with patch.object(agent, "run", AsyncMock(return_value=mock)):
            v = await agent.run_structured("case","research","defense","prosecution", {"defense_score": 50, "prosecution_score": 50})
        assert v["ruling"] == "Liable"
        assert v["confidence"] == 75

    async def test_handles_malformed_json(self):
        from agents.judge_agent import JudgeAgent
        agent = JudgeAgent()
        with patch.object(agent, "run", AsyncMock(return_value="NOT JSON")):
            v = await agent.run_structured("case","research","defense","prosecution", {"defense_score": 50, "prosecution_score": 50})
        assert v["ruling"] == "Undetermined"

    async def test_strips_markdown_fences(self):
        from agents.judge_agent import JudgeAgent
        agent = JudgeAgent()
        wrapped = '```json\n{"ruling":"Not Guilty","confidence":60,"reasoning":"Doubt.","key_finding":"No evidence."}\n```'
        with patch.object(agent, "run", AsyncMock(return_value=wrapped)):
            v = await agent.run_structured("case","research","d","p", {"defense_score": 50, "prosecution_score": 50})
        assert v["ruling"] == "Not Guilty"

    async def test_confidence_coerced_to_int(self):
        from agents.judge_agent import JudgeAgent
        agent = JudgeAgent()
        mock = json.dumps({"ruling":"Liable","confidence":"82.5","reasoning":"...","key_finding":"..."})
        with patch.object(agent, "run", AsyncMock(return_value=mock)):
            v = await agent.run_structured("case","research","d","p", {"defense_score": 50, "prosecution_score": 50})
        assert isinstance(v["confidence"], int)
        assert v["confidence"] == 82


@pytest.mark.asyncio
class TestAppealsAgent:

    async def test_parses_valid_appeal(self):
        from agents.appeals_agent import AppealsAgent
        agent = AppealsAgent()
        mock = json.dumps({"appeal_warranted":True,"grounds":["Misapplication"],"recommended_action":"Remand","appeal_strength":65,"dissenting_view":"Defense deserved more weight."})
        with patch.object(agent, "run", AsyncMock(return_value=mock)):
            r = await agent.run_structured("c","research","defense","prosecution",{"ruling":"Liable","confidence":80,"reasoning":"...","key_finding":"..."})
        assert r["appeal_warranted"] is True
        assert r["appeal_strength"] == 65

    async def test_graceful_fallback_on_bad_json(self):
        from agents.appeals_agent import AppealsAgent
        agent = AppealsAgent()
        with patch.object(agent, "run", AsyncMock(return_value="NOT JSON")):
            r = await agent.run_structured("c","r","d","p",{"ruling":"Liable","confidence":70,"reasoning":".","key_finding":"."})
        assert r["appeal_warranted"] is False
        assert r["recommended_action"] == "Uphold verdict"


@pytest.mark.asyncio
class TestOrchestrator:

    async def test_run_returns_all_keys(self):
        from agents.orchestrator import AgentOrchestrator
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        orch = AgentOrchestrator(kb)
        mock_text = "• Mock agent output"
        mock_verdict = {"ruling":"Liable","confidence":70,"reasoning":"Mock.","key_finding":"Finding."}
        with patch.object(orch._research,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._defense,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._prosecution,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._scoring,"run_structured",AsyncMock(return_value={"defense_score":50,"prosecution_score":50,"stronger_side":"balanced","explanation":"Mock"})), \
             patch.object(orch._judge,"run_structured",AsyncMock(return_value=mock_verdict)):
            result = await orch.run("A legal case.")
        assert {"research","defense","prosecution","verdict","evidence","rounds","scoring"} <= set(result.keys())

    async def test_streaming_yields_correct_stages(self):
        from agents.orchestrator import AgentOrchestrator
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        orch = AgentOrchestrator(kb)
        mock_text = "• Stream output"
        mock_verdict = {"ruling":"Not Guilty","confidence":55,"reasoning":"Doubt.","key_finding":"No evidence."}
        with patch.object(orch._research,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._defense,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._prosecution,"run",AsyncMock(return_value=mock_text)), \
             patch.object(orch._scoring,"run_structured",AsyncMock(return_value={"defense_score":50,"prosecution_score":50,"stronger_side":"balanced","explanation":"Mock"})), \
             patch.object(orch._judge,"run_structured",AsyncMock(return_value=mock_verdict)):
            stages = [s async for s, _ in orch.run_streaming("Streaming case.")]
        assert stages == ["research","evidence","round","round","defense","prosecution","scoring","judge"]


@pytest.mark.asyncio
class TestRAG:

    async def test_retrieves_relevant_docs(self):
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("employee stole trade secrets")
        assert 0 < len(docs) <= 3

    async def test_contract_query_returns_contract_doc(self):
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("breach of contract payment")
        assert any("Contract" in d.title for d in docs)

    async def test_format_context_structure(self):
        from rag.knowledge_base import LegalKnowledgeBase
        kb = LegalKnowledgeBase()
        docs = kb.retrieve("fraud advisor")
        ctx = kb.format_context(docs)
        assert "Citation:" in ctx
        assert len(ctx) > 50
