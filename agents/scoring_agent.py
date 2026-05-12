from agents.base_agent import BaseAgent
from utils.fallback_reasoning import clamp, heuristic_scoring, parse_json_object


class ScoringAgent(BaseAgent):
    NAME = "Scoring Agent"
    SYSTEM_PROMPT = """You evaluate the strength of two legal arguments.
Return only JSON with keys:
defense_score, prosecution_score, explanation, stronger_side.
Scores must be integers from 0 to 100.
Do not return identical scores unless the arguments are genuinely inseparable on the present record."""

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
            "to the case facts, and evidentiary grounding.\n"
            "If one side is even slightly stronger, reflect that with a numeric gap.\n\n"
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
        heuristic = heuristic_scoring(case, research, defense, prosecution)
        result = parse_json_object(raw) or heuristic
        return self._normalize_scores(result, heuristic)

    @staticmethod
    def _normalize_scores(result: dict, heuristic: dict) -> dict:
        defense_score = int(float(result.get("defense_score", heuristic["defense_score"])))
        prosecution_score = int(float(result.get("prosecution_score", heuristic["prosecution_score"])))
        stronger_side = str(result.get("stronger_side", heuristic["stronger_side"] or "balanced")).lower()
        explanation = str(result.get("explanation", "")).strip() or heuristic["explanation"]

        defense_score = clamp(defense_score, 0, 100)
        prosecution_score = clamp(prosecution_score, 0, 100)

        heuristic_gap = abs(int(heuristic["prosecution_score"]) - int(heuristic["defense_score"]))
        heuristic_side = heuristic.get("stronger_side", "balanced")

        if defense_score == prosecution_score:
            if stronger_side == "defense":
                defense_score = clamp(defense_score + 1, 0, 100)
                prosecution_score = clamp(prosecution_score - 1, 0, 100)
            elif stronger_side == "prosecution":
                prosecution_score = clamp(prosecution_score + 1, 0, 100)
                defense_score = clamp(defense_score - 1, 0, 100)
            elif heuristic_side in {"defense", "prosecution"} and heuristic_gap >= 3:
                defense_score = int(heuristic["defense_score"])
                prosecution_score = int(heuristic["prosecution_score"])
                stronger_side = heuristic_side
                explanation = heuristic["explanation"]

        if defense_score > prosecution_score:
            stronger_side = "defense"
        elif prosecution_score > defense_score:
            stronger_side = "prosecution"
        else:
            stronger_side = "balanced"

        return {
            "defense_score": defense_score,
            "prosecution_score": prosecution_score,
            "explanation": explanation,
            "stronger_side": stronger_side,
        }
