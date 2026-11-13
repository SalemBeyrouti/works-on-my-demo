"""Build an agent live, in 6 steps.

This file starts as a plain chatbot (STEP 1). At each checkpoint in the talk,
copy the matching file from snippets/ and paste it at its marked spot below.
Later steps redefine ask() - in Python the last definition wins, so each step
upgrades the one before it.

Run it:
    python agent.py "when are the demos?"     one question
    python agent.py                           chat until you type quit
    python agent.py --check "Demos at 16:00"  (after step 5) run the evaluator on any text
"""

import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

HERE = Path(__file__).parent
if not (HERE / "data").exists():                 # running a copy from checkpoints/
    HERE = HERE.parent
load_dotenv(HERE / ".env")                       # your own key, if you copied .env.example
load_dotenv(HERE.parent / "alphabot" / ".env")   # the speaker's setup
sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.getenv("ALPHABOT_MODEL", "claude-opus-5-5")
client = anthropic.Anthropic()                   # reads ANTHROPIC_API_KEY from the environment
EVENT_FILE = HERE / "data" / "event.local.json"  # the real event data: kept out of git (.gitignore)
if not EVENT_FILE.exists():
    EVENT_FILE = HERE / "data" / "event.json"     # the sample that ships with the repo
EVENT = json.loads(EVENT_FILE.read_text(encoding="utf-8"))


# ═══ STEP 1 · THE MODEL: a chatbot ═══════════════════════════════════════════
# WHAT IT IS:  One request in, one answer out. No tools, no loop, no memory.
# WHAT GOES WRONG: The model has never seen YOUR data (the schedule, the rooms),
#              so it either makes something up or admits it doesn't know.
#              Either way, it's useless for your users.
# THIS IS NOT AN AGENT YET: an agent needs tools (step 2) and a loop.
def ask(question: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": f"About the AlphaHack hackathon at LAU Byblos: {question}"}],
        output_config={"effort": "low"},         # a chat answer doesn't need deep thinking - faster
    )
    return "".join(b.text for b in response.content if b.type == "text")


# ─── STEP 2 · PASTE THE TOOLS + THE LOOP HERE ─────────────────────────────────
# ═══ STEP 2 · TOOLS + THE LOOP: now it's an agent ════════════════════════════
# WHAT A TOOL IS: two halves.
#   1. A DESCRIPTION the model reads  (name, what it does, WHEN to use it, inputs)
#   2. A FUNCTION your code runs       (the model never runs code - it only asks)
# MAKE TOOLS BETTER:
#   - Name them like a teammate would understand: find_room, not api_call
#   - Say WHEN to use the tool, not just what it does
#   - Errors should say what to do next: "No room 'X'. Known rooms: A, B, C"
#   - Return only what's needed. Huge JSON dumps fill the context and confuse the model
# CHANGE IT FOR YOUR PROJECT: replace these three with calls to your own API or database.

def get_schedule(day: str | None = None) -> str:
    sessions = [s for s in EVENT["schedule"] if not day or s["day"].lower() == day.lower()]
    return json.dumps(sessions) if sessions else f"No sessions on '{day}'. Valid days: Friday, Saturday, Sunday."

def find_room(name: str) -> str:
    for room in EVENT["rooms"]:
        if name.lower() in room["name"].lower() or any(name.lower() in a for a in room["aliases"]):
            return json.dumps(room)
    return f"No room '{name}'. Known rooms: {', '.join(r['name'] for r in EVENT['rooms'])}."

def get_rules(topic: str | None = None) -> str:
    rules = EVENT["rules"]
    if topic and topic.lower() not in rules:
        return f"No topic '{topic}'. Topics: {', '.join(rules)}."
    return json.dumps(rules[topic.lower()] if topic else rules)

TOOLS = [
    {"name": "get_schedule", "description": "When things happen: talks, deadlines, checkpoints, judging, doors. Optional day: Friday, Saturday or Sunday.",
     "input_schema": {"type": "object", "properties": {"day": {"type": "string"}}}},
    {"name": "find_room", "description": "Where a room or place is on campus.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "get_rules", "description": f"Official rules and the challenge. Topics: {', '.join(EVENT['rules'])}. Never answer rules from memory.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}}},
]
FUNCTIONS = {"get_schedule": get_schedule, "find_room": find_room, "get_rules": get_rules}


def run_tool(name: str, args: dict) -> str:
    print(f"   🔧 {name}({args})")          # so the audience SEES the agent act
    return FUNCTIONS[name](**args)


# THE LOOP: think -> act -> observe -> repeat, until the model stops asking for tools.
# This replaces ask() from step 1.
def ask(question: str) -> str:
    messages = [{"role": "user", "content": question}]
    while True:                                                         # ⚠ no limit yet - step 3 fixes this
        response = client.messages.create(model=MODEL, max_tokens=4000, tools=TOOLS, messages=messages,
                                          output_config={"effort": "low"})                  # THINK
        messages.append({"role": "assistant", "content": response.content})
        calls = [b for b in response.content if b.type == "tool_use"]
        if not calls:                                                   # DECIDE: done
            return "".join(b.text for b in response.content if b.type == "text")
        results = [{"type": "tool_result", "tool_use_id": c.id, "content": run_tool(c.name, c.input)} for c in calls]   # ACT
        messages.append({"role": "user", "content": results})          # OBSERVE



# ─── STEP 3 · PASTE THE HARNESS HERE ──────────────────────────────────────────


# ─── STEP 4 · PASTE THE ROUTER HERE ───────────────────────────────────────────


# ─── STEP 5 · PASTE THE EVALUATOR HERE ────────────────────────────────────────


# ─── STEP 6 · PASTE THE LOCK HERE ─────────────────────────────────────────────


# ═══ RUN ═════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    def safe_ask(question: str) -> str:
        try:
            return ask(question)
        except anthropic.APIConnectionError:   # the Wi-Fi dropped: say so, don't crash the chat
            return "⚠ No connection to the model. Check the Wi-Fi and ask again."

    if sys.argv[1:2] == ["--check"] and "check_answer" in globals():   # step 5 demo: check any text
        problems = check_answer(" ".join(sys.argv[2:]))
        print("🛑 " + "; ".join(problems) if problems else "✅ passes the check")
    elif len(sys.argv) > 1:
        print(safe_ask(" ".join(sys.argv[1:])))
    else:
        while (q := input("\nyou> ").strip()).lower() not in {"quit", "exit"}:
            if q:
                print("agent>", safe_ask(q))
    if "langfuse" in globals():
        langfuse.flush()  # send the traces before the program exits (step 3)
