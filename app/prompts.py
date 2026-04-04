from __future__ import annotations

import json
from pathlib import Path


AGENT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "agent-config" / "tolo-kabab-house.json"


def load_agent_config() -> dict:
    with AGENT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_system_prompt() -> str:
    config = load_agent_config()
    prompt_lines = config["system_prompt"][:]
    prompt_lines.extend(
        [
            "Use tools whenever they can help you answer correctly.",
            "When you successfully create a reservation, clearly confirm it once.",
            "If a live transfer is not available in the system, explain that a staff member will call back.",
            "This deployment is for phone calls, so keep answers conversational and concise.",
        ]
    )
    return "\n".join(f"- {line}" for line in prompt_lines)


def build_greeting_instruction() -> str:
    config = load_agent_config()
    return (
        "Start the call now. Greet the caller with this exact opening line, then pause for their answer: "
        f"\"{config['opening_script']}\""
    )
