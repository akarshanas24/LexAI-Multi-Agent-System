from agents.base_agent import BaseAgent
from utils.fallback_reasoning import extract_labeled_section, heuristic_research_brief


class ResearchAgent(BaseAgent):
    NAME = "Research Agent"
    SYSTEM_PROMPT = (
        "You are the research specialist in an AI legal reasoning system. "
        "Summarize the legal issues, applicable standards, evidentiary tensions, "
        "and the most relevant cited materials from the retrieved context. "
        "Be analytical, neutral, and structured."
    )

    def build_prompt(self, case: str, context: str = "") -> str:
        return (
            "Review the case and produce a structured research brief.\n"
            "Organize the answer under short headings for: core issues, governing principles, "
            "key evidence tensions, and likely pressure points for both sides.\n\n"
            f"Case:\n{case}\n\n"
            f"Retrieved context:\n{context}"
        )

    def _fallback_response(self, prompt: str) -> str:
        case = extract_labeled_section(
            prompt,
            "Case:",
            ["Retrieved context:", "Reasoning style preference:"],
        )
        context = extract_labeled_section(
            prompt,
            "Retrieved context:",
            ["Reasoning style preference:"],
        )
        return heuristic_research_brief(case, context)
