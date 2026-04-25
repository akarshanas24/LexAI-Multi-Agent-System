from agents.base_agent import BaseAgent, parse_json_response


class JudgeAgent(BaseAgent):
    NAME = "Judge Agent"
    SYSTEM_PROMPT = """You are the Judge Agent in a multi-agent legal reasoning system.
Return only JSON with keys: ruling, confidence, reasoning, key_finding."""

    def build_prompt(self, case: str, defense: str, prosecution: str) -> str:
        return (
            "Decide this case and return a JSON verdict.\n\n"
            f"Case:\n{case}\n\nDefense:\n{defense}\n\nProsecution:\n{prosecution}"
        )

    async def run_structured(self, case: str, defense: str, prosecution: str) -> dict:
        raw = await self.run(self.build_prompt(case, defense, prosecution))
        verdict = parse_json_response(
            raw,
            {
                "ruling": "Undetermined",
                "confidence": 50,
                "reasoning": raw[:400],
                "key_finding": "",
            },
        )
        verdict["confidence"] = int(float(verdict.get("confidence", 50)))
        verdict["ruling"] = verdict.get("ruling", "Undetermined")
        verdict["reasoning"] = verdict.get("reasoning", "")
        verdict["key_finding"] = verdict.get("key_finding", "")
        return verdict

    def _fallback_response(self, prompt: str) -> str:
        return (
            '{"ruling":"Undetermined","confidence":50,'
            '"reasoning":"Fallback verdict generated because no LLM is configured.",'
            '"key_finding":"No live model configured."}'
        )
