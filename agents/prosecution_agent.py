from agents.base_agent import BaseAgent


class ProsecutionAgent(BaseAgent):
    NAME = "Prosecution Agent"
    SYSTEM_PROMPT = (
        "You are prosecution or plaintiff-side counsel in a simulated courtroom. "
        "Use the facts and research brief to build the strongest grounded case for liability or guilt. "
        "Avoid inventing evidence."
    )

    def build_prompt(
        self,
        case: str,
        research: str = "",
        defense_argument: str = "",
        round_name: str = "opening",
    ) -> str:
        round_instruction = (
            "Write the opening prosecution argument."
            if round_name == "opening"
            else "Write the prosecution rebuttal responding directly to the defense's strongest points."
        )
        opposing_block = (
            f"\n\nOpposing defense argument to address:\n{defense_argument}"
            if defense_argument
            else ""
        )
        return (
            f"{round_instruction}\n"
            "Use short sections or bullets for liability theory, evidentiary support, and legal framing.\n\n"
            f"Case:\n{case}\n\n"
            f"Research:\n{research}"
            f"{opposing_block}"
        )
