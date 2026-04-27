"""
Pipeline orchestrator for LexAI.

Flow:
    Case -> RAG retrieval -> Research -> Round 1 arguments -> Round 2 rebuttals
    -> Argument scoring -> Judge verdict -> Appeals (optional)
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from agents.appeals_agent import AppealsAgent
from agents.defense_agent import DefenseAgent
from agents.judge_agent import JudgeAgent
from agents.prosecution_agent import ProsecutionAgent
from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent
from rag.knowledge_base import LegalKnowledgeBase
from utils.logger import log_agent_call, log_pipeline_event, log_rag_retrieval


class AgentOrchestrator:
    def __init__(self, knowledge_base: LegalKnowledgeBase):
        self._kb = knowledge_base
        self._research = ResearchAgent()
        self._defense = DefenseAgent()
        self._prosecution = ProsecutionAgent()
        self._judge = JudgeAgent()
        self._appeals = AppealsAgent()
        self._scoring = ScoringAgent()

    async def run(
        self,
        case: str,
        case_id: str = "n/a",
        include_appeals: bool = False,
        retrieval_limit: int | None = None,
        reasoning_profile: str = "balanced",
    ) -> dict[str, Any]:
        research, evidence = await self._run_research(case, case_id, retrieval_limit, reasoning_profile)
        rounds = await self._run_debate_rounds(case, research, reasoning_profile)
        defense = self._merge_rounds("defense", rounds)
        prosecution = self._merge_rounds("prosecution", rounds)
        style_hint = self._style_hint(reasoning_profile)
        scoring = await self._scoring.run_structured(case, research, defense, prosecution, style_hint)
        verdict = await self._judge.run_structured(case, research, defense, prosecution, scoring, style_hint)
        log_pipeline_event(case_id, "judge", "done")

        result: dict[str, Any] = {
            "research": {"content": research, "sources": evidence["documents"]},
            "evidence": evidence,
            "rounds": rounds,
            "defense": {"content": defense},
            "prosecution": {"content": prosecution},
            "scoring": scoring,
            "verdict": verdict,
        }
        if include_appeals:
            result["appeals"] = await self._appeals.run_structured(
                case,
                research,
                defense,
                prosecution,
                verdict,
                style_hint,
            )
        return result

    async def run_streaming(
        self,
        case: str,
        case_id: str = "n/a",
        include_appeals: bool = False,
        retrieval_limit: int | None = None,
        reasoning_profile: str = "balanced",
    ) -> AsyncGenerator[tuple[str, Any], None]:
        research, evidence = await self._run_research(case, case_id, retrieval_limit, reasoning_profile)
        yield "research", {"content": research, "sources": evidence["documents"]}
        yield "evidence", evidence

        rounds = await self._run_debate_rounds(case, research, reasoning_profile)
        for item in rounds:
            yield "round", item

        defense = self._merge_rounds("defense", rounds)
        prosecution = self._merge_rounds("prosecution", rounds)
        yield "defense", {"content": defense}
        yield "prosecution", {"content": prosecution}

        style_hint = self._style_hint(reasoning_profile)
        scoring = await self._scoring.run_structured(case, research, defense, prosecution, style_hint)
        yield "scoring", scoring

        verdict = await self._judge.run_structured(case, research, defense, prosecution, scoring, style_hint)
        log_pipeline_event(case_id, "judge", "done")
        yield "judge", verdict

        if include_appeals:
            appeal = await self._appeals.run_structured(case, research, defense, prosecution, verdict, style_hint)
            yield "appeals", appeal

    async def _run_research(
        self,
        case: str,
        case_id: str = "",
        retrieval_limit: int | None = None,
        reasoning_profile: str = "balanced",
    ) -> tuple[str, dict[str, Any]]:
        docs = self._kb.retrieve(case, limit=retrieval_limit)
        log_rag_retrieval(len(case), len(docs))
        context = self._kb.format_context(docs)
        prompt = self._research.build_prompt(case, context)
        result = await self._research.run(self._apply_style_hint(prompt, reasoning_profile))
        log_agent_call("ResearchAgent")
        evidence = {
            "query": case,
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
        log_pipeline_event(case_id, "research", "done")
        return result, evidence

    async def _run_debate_rounds(
        self,
        case: str,
        research: str,
        reasoning_profile: str,
    ) -> list[dict[str, Any]]:
        opening_defense, opening_prosecution = await asyncio.gather(
            self._run_defense(case, research, round_name="opening", reasoning_profile=reasoning_profile),
            self._run_prosecution(case, research, round_name="opening", reasoning_profile=reasoning_profile),
        )
        round_one = {
            "round": 1,
            "label": "Opening Arguments",
            "defense": opening_defense,
            "prosecution": opening_prosecution,
        }

        rebuttal_defense, rebuttal_prosecution = await asyncio.gather(
            self._run_defense(
                case,
                research,
                opposing_argument=opening_prosecution,
                round_name="rebuttal",
                reasoning_profile=reasoning_profile,
            ),
            self._run_prosecution(
                case,
                research,
                opposing_argument=opening_defense,
                round_name="rebuttal",
                reasoning_profile=reasoning_profile,
            ),
        )
        round_two = {
            "round": 2,
            "label": "Counter Arguments",
            "defense": rebuttal_defense,
            "prosecution": rebuttal_prosecution,
        }
        return [round_one, round_two]

    async def _run_defense(
        self,
        case: str,
        research: str,
        opposing_argument: str = "",
        round_name: str = "opening",
        reasoning_profile: str = "balanced",
    ) -> str:
        prompt = self._defense.build_prompt(case, research, opposing_argument, round_name)
        result = await self._defense.run(
            self._apply_style_hint(prompt, reasoning_profile)
        )
        log_agent_call("DefenseAgent")
        return result

    async def _run_prosecution(
        self,
        case: str,
        research: str,
        opposing_argument: str = "",
        round_name: str = "opening",
        reasoning_profile: str = "balanced",
    ) -> str:
        prompt = self._prosecution.build_prompt(case, research, opposing_argument, round_name)
        result = await self._prosecution.run(
            self._apply_style_hint(prompt, reasoning_profile)
        )
        log_agent_call("ProsecutionAgent")
        return result

    @staticmethod
    def _merge_rounds(side: str, rounds: list[dict[str, Any]]) -> str:
        return "\n\n".join(f"{item['label']}:\n{item[side]}" for item in rounds)

    @staticmethod
    def _style_hint(reasoning_profile: str) -> str:
        profile = (reasoning_profile or "balanced").strip().lower()
        if profile == "concise":
            return "Be concise, prioritize the strongest authorities and avoid repetitive argumentation."
        if profile == "detailed":
            return "Be detailed, explain competing arguments, cite more support, and show a fuller reasoning trail."
        return "Keep the analysis balanced, readable, and grounded in the retrieved legal material."

    def _apply_style_hint(self, prompt: str, reasoning_profile: str) -> str:
        return f"{prompt}\n\nReasoning style preference:\n{self._style_hint(reasoning_profile)}"
