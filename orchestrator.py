"""
agents/orchestrator.py
======================
Pipeline Orchestrator — coordinates all agents.

    Case → RAG → Research → [Defense ‖ Prosecution] → Judge → Appeals (optional)
"""

import asyncio
from typing import AsyncGenerator, Tuple, Any

from agents.research_agent import ResearchAgent
from agents.defense_agent import DefenseAgent
from agents.prosecution_agent import ProsecutionAgent
from agents.judge_agent import JudgeAgent
from agents.appeals_agent import AppealsAgent
from rag.knowledge_base import LegalKnowledgeBase
from utils.logger import log_pipeline_event, log_agent_call, log_rag_retrieval


class AgentOrchestrator:

    def __init__(self, knowledge_base: LegalKnowledgeBase):
        self._kb          = knowledge_base
        self._research    = ResearchAgent()
        self._defense     = DefenseAgent()
        self._prosecution = ProsecutionAgent()
        self._judge       = JudgeAgent()
        self._appeals     = AppealsAgent()

    # ── Blocking run ──────────────────────────────────
    async def run(self, case: str, case_id: str = "n/a", include_appeals: bool = False) -> dict:
        research = await self._run_research(case, case_id)
        defense, prosecution = await asyncio.gather(
            self._run_defense(case, research),
            self._run_prosecution(case, research),
        )
        verdict = await self._judge.run_structured(case, defense, prosecution)
        log_pipeline_event(case_id, "judge", "done")

        result = {
            "research":    {"content": research},
            "defense":     {"content": defense},
            "prosecution": {"content": prosecution},
            "verdict":     verdict,
        }
        if include_appeals:
            appeal = await self._appeals.run_structured(case, research, defense, prosecution, verdict)
            result["appeals"] = appeal
        return result

    # ── Streaming run ─────────────────────────────────
    async def run_streaming(
        self,
        case: str,
        case_id: str = "n/a",
        include_appeals: bool = False,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        research = await self._run_research(case, case_id)
        yield "research", {"content": research}

        defense_task     = asyncio.create_task(self._run_defense(case, research))
        prosecution_task = asyncio.create_task(self._run_prosecution(case, research))
        pending = {defense_task, prosecution_task}
        defense_output = prosecution_output = None

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task is defense_task:
                    defense_output = task.result()
                    yield "defense", {"content": defense_output}
                else:
                    prosecution_output = task.result()
                    yield "prosecution", {"content": prosecution_output}

        verdict = await self._judge.run_structured(case, defense_output, prosecution_output)
        log_pipeline_event(case_id, "judge", "done")
        yield "judge", verdict

        if include_appeals:
            appeal = await self._appeals.run_structured(
                case, research, defense_output, prosecution_output, verdict
            )
            yield "appeals", appeal

    # ── Internals ─────────────────────────────────────
    async def _run_research(self, case: str, case_id: str = "") -> str:
        docs    = self._kb.retrieve(case)
        log_rag_retrieval(len(case), len(docs))
        context = self._kb.format_context(docs)
        prompt  = self._research.build_prompt(case, context)
        result  = await self._research.run(prompt)
        log_agent_call("ResearchAgent")
        return result

    async def _run_defense(self, case: str, research: str) -> str:
        result = await self._defense.run(self._defense.build_prompt(case, research))
        log_agent_call("DefenseAgent")
        return result

    async def _run_prosecution(self, case: str, research: str) -> str:
        result = await self._prosecution.run(self._prosecution.build_prompt(case, research))
        log_agent_call("ProsecutionAgent")
        return result
