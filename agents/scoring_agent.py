from agents.base_agent import BaseAgent, parse_json_response


class ScoringAgent(BaseAgent):
    NAME = "Scoring Agent"
    SYSTEM_PROMPT = """You evaluate the strength of two legal arguments.
Return only JSON with keys:
defense_score, prosecution_score, explanation, stronger_side.
Scores must be integers from 0 to 100."""

    def build_prompt(
        self,
        case: str,
        research: str,
        defense: str,
        prosecution: str,
        style_hint: str = "",
    ) -> str:
        prompt = (
            "Score the strength of the defense and prosecution arguments.\n"
            "Base the scores on internal coherence, use of retrieved legal context, responsiveness "
            "to the case facts, and evidentiary grounding.\n\n"
            f"Case:\n{case}\n\n"
            f"Research brief:\n{research}\n\n"
            f"Defense:\n{defense}\n\n"
            f"Prosecution:\n{prosecution}"
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
        style_hint: str = "",
    ) -> dict:
        raw = await self.run(self.build_prompt(case, research, defense, prosecution, style_hint))
        result = parse_json_response(
            raw,
            {
                "defense_score": 50,
                "prosecution_score": 50,
                "explanation": raw[:300],
                "stronger_side": "balanced",
            },
        )
        result["defense_score"] = int(float(result.get("defense_score", 50)))
        result["prosecution_score"] = int(float(result.get("prosecution_score", 50)))
        result["explanation"] = result.get("explanation", "")
        result["stronger_side"] = result.get("stronger_side", "balanced")
        return result
