"""
agents/appeals_agent.py
=======================
Appeals Agent — optional 5th stage of the pipeline.

Responsibility:
    Reviews the Judge's verdict and determines whether grounds for
    appeal exist. Produces a structured appeal assessment.

Grounds for appeal it evaluates:
    - Procedural error
    - Misapplication of legal standard
    - Insufficient weight given to key evidence
    - New legal argument not considered
    - Disproportionate confidence score

Input:
    - Original case description
    - All prior agent outputs (research, defense, prosecution)
    - Judge's verdict

Output (JSON):
    {
        "appeal_warranted": true | false,
        "grounds": ["Misapplication of burden of proof", ...],
        "recommended_action": "Remand for reconsideration" | "Uphold verdict" | ...,
        "appeal_strength": 0-100,
        "dissenting_view": "One-paragraph alternative interpretation"
    }
"""

import json
from agents.base_agent import BaseAgent


class AppealsAgent(BaseAgent):

    NAME = "Appeals Agent"

    SYSTEM_PROMPT = """You are the Appeals Agent in a multi-agent AI legal reasoning system.

Your role is to act as an appellate reviewer. You do NOT retry the case — you examine whether the Judge's verdict was legally sound.

Evaluate the verdict for:
1. Misapplication of the burden of proof standard
2. Failure to adequately weigh key defense or prosecution arguments
3. Logical inconsistency between reasoning and ruling
4. Overconfidence or underconfidence in the confidence score
5. Any novel legal argument that was not considered

You must respond with ONLY valid JSON — no preamble, no markdown fences.

Schema:
{
  "appeal_warranted": <true|false>,
  "grounds": [<list of strings — specific grounds for appeal, or empty if none>],
  "recommended_action": "<Uphold verdict | Remand for reconsideration | Reverse ruling | Reduce confidence score>",
  "appeal_strength": <integer 0-100, where 0=no basis and 100=strong grounds>,
  "dissenting_view": "<1-2 sentences — alternative interpretation of the case, even if appeal not warranted>"
}"""

    def build_prompt(self, case: str, context: str = "", style_hint: str = "") -> str:
        prompt = f"""Original legal case:
{case}

---
{context}

---
Review the verdict above and render your appellate assessment as JSON."""
        if style_hint:
            prompt += f"\n\nReasoning style preference:\n{style_hint}"
        return prompt

    async def run_structured(
        self,
        case: str,
        research: str,
        defense: str,
        prosecution: str,
        verdict: dict,
        style_hint: str = "",
    ) -> dict:
        """
        Run the appeals review and return parsed JSON.

        Args:
            case:         Original case description
            research:     Research agent output
            defense:      Defense agent output
            prosecution:  Prosecution agent output
            verdict:      Judge agent verdict dict

        Returns:
            Parsed appeal assessment dict
        """
        context = (
            f"Research brief:\n{research}\n\n"
            f"Defense arguments:\n{defense}\n\n"
            f"Prosecution arguments:\n{prosecution}\n\n"
            f"Judge's verdict:\n"
            f"  Ruling: {verdict.get('ruling')}\n"
            f"  Confidence: {verdict.get('confidence')}%\n"
            f"  Reasoning: {verdict.get('reasoning')}\n"
            f"  Key finding: {verdict.get('key_finding')}"
        )
        prompt = self.build_prompt(case, context, style_hint)
        raw = await self.run(prompt)

        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            result = {
                "appeal_warranted": False,
                "grounds": [],
                "recommended_action": "Uphold verdict",
                "appeal_strength": 0,
                "dissenting_view": raw[:400],
            }

        result["appeal_strength"] = int(float(result.get("appeal_strength", 0)))
        return result
