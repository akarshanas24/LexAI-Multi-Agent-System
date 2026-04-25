from agents.base_agent import BaseAgent


class ProsecutionAgent(BaseAgent):
    NAME = "Prosecution Agent"
    SYSTEM_PROMPT = "You argue for the plaintiff or prosecution using concise, persuasive bullet points."

    def build_prompt(self, case: str, research: str = "") -> str:
        return (
            "Write the strongest prosecution arguments for this case.\n\n"
            f"Case:\n{case}\n\n"
            f"Research:\n{research}"
        )
