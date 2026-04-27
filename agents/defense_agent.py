from agents.base_agent import BaseAgent


class DefenseAgent(BaseAgent):
    NAME = "Defense Agent"
    SYSTEM_PROMPT = (
        "You are defense counsel in a simulated courtroom. "
        "Use the case facts and research brief to produce grounded, persuasive reasoning. "
        "Avoid inventing evidence. Acknowledge weaknesses when strategically useful."
    )

    def build_prompt(
        self,
        case: str,
        research: str = "",
        prosecution_argument: str = "",
        round_name: str = "opening",
    ) -> str:
        round_instruction = (
            "Write the opening defense argument."
            if round_name == "opening"
            else "Write the defense rebuttal responding directly to the prosecution's strongest points."
        )
        opposing_block = (
            f"\n\nOpposing prosecution argument to address:\n{prosecution_argument}"
            if prosecution_argument
            else ""
        )
        return (
            f"{round_instruction}\n"
            "Use short sections or bullets for theory of the case, evidentiary concerns, and legal framing.\n\n"
            f"Case:\n{case}\n\n"
            f"Research:\n{research}"
            f"{opposing_block}"
        )
