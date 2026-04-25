from agents.base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    NAME = "Research Agent"
    SYSTEM_PROMPT = "You summarize relevant legal doctrines, standards, and citations."

    def build_prompt(self, case: str, context: str = "") -> str:
        return (
            "Review the case and summarize the most relevant legal authorities.\n\n"
            f"Case:\n{case}\n\n"
            f"Retrieved context:\n{context}"
        )
