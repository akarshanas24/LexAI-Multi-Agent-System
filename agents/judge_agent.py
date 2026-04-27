from agents.base_agent import BaseAgent, parse_json_response


class JudgeAgent(BaseAgent):
    NAME = "Judge Agent"
    SYSTEM_PROMPT = """You are the Judge Agent in a multi-agent legal reasoning system.
Evaluate the arguments neutrally and return only JSON with keys:
ruling, confidence, reasoning, key_finding, winning_side, cited_basis.
Confidence must be an integer from 0 to 100."""

    def build_prompt(
        self,
        case: str,
        research: str,
        defense: str,
        prosecution: str,
        scoring: dict,
        style_hint: str = "",
    ) -> str:
        prompt = (
            "Decide this case and return a JSON verdict.\n"
            "Weigh the legal framing, factual uncertainty, burden of proof, and strength of support.\n\n"
            f"Case:\n{case}\n\n"
            f"Research brief:\n{research}\n\n"
            f"Defense argument set:\n{defense}\n\n"
            f"Prosecution argument set:\n{prosecution}\n\n"
            f"Argument strength scoring:\n{scoring}"
        )
        if style_hint:
            prompt += f"\n\nReasoning style preference:\n{style_hint}"
        return prompt

    async def run_structured(
        self,
        case: str,
        research: str,
        defense: str,
        prosecution: str,
        scoring: dict,
        style_hint: str = "",
    ) -> dict:
        raw = await self.run(self.build_prompt(case, research, defense, prosecution, scoring, style_hint))
        verdict = parse_json_response(
            raw,
            {
                "ruling": "Undetermined",
                "confidence": 50,
                "reasoning": raw[:400],
                "key_finding": "",
                "winning_side": "balanced",
                "cited_basis": "",
            },
        )
        verdict["confidence"] = int(float(verdict.get("confidence", 50)))
        verdict["ruling"] = verdict.get("ruling", "Undetermined")
        verdict["reasoning"] = verdict.get("reasoning", "")
        verdict["key_finding"] = verdict.get("key_finding", "")
        verdict["winning_side"] = verdict.get("winning_side", "balanced")
        verdict["cited_basis"] = verdict.get("cited_basis", "")
        return verdict

    def _fallback_response(self, prompt: str) -> str:
        return (
            '{"ruling":"Undetermined","confidence":50,'
            '"reasoning":"Fallback verdict generated because no LLM is configured.",'
            '"key_finding":"No live model configured.",'
            '"winning_side":"balanced",'
            '"cited_basis":"No live model configured."}'
        )
