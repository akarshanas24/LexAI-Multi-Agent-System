from agents.base_agent import BaseAgent


class DefenseAgent(BaseAgent):
    NAME = "Defense Agent"
    SYSTEM_PROMPT = "You argue for the defendant using concise, persuasive bullet points."

    def build_prompt(self, case: str, research: str = "") -> str:
        return (
            "Write the strongest defense arguments for this case.\n\n"
            f"Case:\n{case}\n\n"
            f"Research:\n{research}"
        )
