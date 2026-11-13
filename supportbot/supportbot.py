"""SupportBot: sorts one customer message into refund, complaint or question.

Deliberately tiny - it exists to show how testing catches mistakes.
The instructions live in prompt.txt so you can edit them live on stage.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")                         # the repo's .env (same keys as agent.py)
load_dotenv(HERE.parent.parent / "alphabot" / ".env")     # the speaker's setup

MODEL = os.getenv("ALPHABOT_MODEL", "claude-opus-5-5")
LABELS = ["refund", "complaint", "question"]
client = anthropic.Anthropic()

# Rule 3 from the talk, "force the shape": the model can only answer with one of the three labels.
SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": LABELS}},
    "required": ["label"],
    "additionalProperties": False,
}


def classify(message: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=(HERE / "prompt.txt").read_text(encoding="utf-8"),  # re-read every call, so edits apply instantly
        messages=[{"role": "user", "content": message}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["label"]


if __name__ == "__main__":
    import sys
    print(classify(" ".join(sys.argv[1:]) or "it broke after one day, I want my money back"))
