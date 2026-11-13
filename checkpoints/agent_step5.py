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
# ═══ STEP 3 · THE HARNESS: everything AROUND the model ═══════════════════════
# Same model, same tools. What changes is the code around them:
#   1. A SYSTEM PROMPT  - who the agent is, what it must and must not do
#   2. A STOP CONDITION - MAX_STEPS, so a confused agent can't loop and burn money forever
#   3. MEMORY           - the conversation so far, so "and where is that?" works
#   4. TRACING          - every step recorded in Langfuse, so you can SEE why it failed
#   5. COST + TIME      - printed for every answer. If you don't measure it, you can't fix it
# MAKE IT BETTER:
#   - Keep the system prompt short and specific: rules it must follow, not an essay
#   - Memory keeps questions and answers, NOT every tool result - those fill the context fast.
#     But keep a short note of WHICH tools backed each answer. Without it, the model sees
#     facts with no evidence behind them and starts "correcting" its own earlier answers.
#   - Cap tokens and spend per user, not just steps
#   - Turn tracing on in hour one, not the night before the demo
# CHANGE IT FOR YOUR PROJECT: rewrite SYSTEM_PROMPT for your users; keep everything else.

import re
import time
from langfuse import get_client, observe

TRACING = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))  # no keys? the agent still works, just untraced
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", str(TRACING).lower())
langfuse = get_client()                          # reads LANGFUSE_* keys from .env
MAX_STEPS = 6
MEMORY = []                                       # earlier questions and answers in this chat
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-5-5": (4, 20)}  # $ per M tokens
spent = {"usd": 0.0}

TODAY = time.strftime("%A")                      # the model can't know what day it is: tell it
SYSTEM_PROMPT = f"""You are AlphaBot, the assistant for AlphaHack, a hackathon at LAU Byblos. Today is {TODAY}.
- Use your tools for every fact about the event. Never guess a time, a room or a rule.
- Questions that aren't about the event: answer briefly from general knowledge, no tools.
- If nothing is on the day they asked about, say so and tell them when it actually is.
- If the tools can't answer, say so and send people to an organiser.
- Earlier answers marked [checked with: ...] were verified with tools. Don't re-check or correct them unless asked; answer only the new question.
- Answer in 1-3 short sentences of plain text, no markdown: people read this on their phones."""


@observe(as_type="generation", name="model-call")
def call_model(messages: list, model: str):
    response = client.messages.create(model=model, max_tokens=4000, system=SYSTEM_PROMPT, tools=TOOLS,
                                      messages=messages, output_config={"effort": "low"})
    price_in, price_out = PRICES.get(model, (0, 0))
    spent["usd"] += (response.usage.input_tokens * price_in + response.usage.output_tokens * price_out) / 1e6
    langfuse.update_current_generation(model=model, usage_details={"input": response.usage.input_tokens, "output": response.usage.output_tokens})
    return response


@observe(as_type="tool")
def traced_tool(name: str, args: dict) -> str:
    return run_tool(name, args)


# This replaces ask() from step 2: same loop, now with a prompt, a limit, memory and a recording.
@observe(as_type="agent", name="alphabot")
def ask(question: str, model: str = MODEL) -> str:
    start, spent["usd"], used = time.time(), 0.0, []
    messages = MEMORY + [{"role": "user", "content": question}]
    for step in range(MAX_STEPS):                                       # ✅ the stop condition
        response = call_model(messages, model)
        messages.append({"role": "assistant", "content": response.content})
        calls = [b for b in response.content if b.type == "tool_use"]
        used += [c.name for c in calls]
        if not calls:
            answer = "".join(b.text for b in response.content if b.type == "text")
            answer = re.sub(r"\s*\[checked with:[^\]]*\]", "", answer).strip()  # the model copies our note: strip it in code
            note = f"\n\n[checked with: {', '.join(sorted(set(used)))}]" if used else ""
            MEMORY.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer + note}])
            print(f"   💰 ${spent['usd']:.4f} · ⏱ {time.time() - start:.1f}s · {model}")
            if TRACING:
                print(f"   🔍 trace: {langfuse.get_trace_url()}")
            return answer
        results = [{"type": "tool_result", "tool_use_id": c.id, "content": traced_tool(c.name, c.input)} for c in calls]
        messages.append({"role": "user", "content": results})
    return "I'm going in circles. Could you ask that another way?"      # stopped instead of looping forever



# ─── STEP 4 · PASTE THE ROUTER HERE ───────────────────────────────────────────
# ═══ STEP 4 · PATTERN: ROUTING ═══════════════════════════════════════════════
# WHAT IT IS:  A cheap, fast model looks at the question first and decides who
#              should answer: easy questions -> small model, hard ones -> strong model.
# WHY IT MATTERS: Most questions are easy. Paying the strong model for
#              "where's the food?" wastes money and time - and a judge feels the delay.
# MAKE IT BETTER:
#   - Route on more than difficulty: language, topic, or "needs a human"
#   - Log every routing decision (it's in the trace) and check it's not sending hard work to the small model
#   - If the small model's answer fails a check (step 5), retry on the strong model
# CHANGE IT FOR YOUR PROJECT: change the two models, and the definition of "hard" in ROUTER_PROMPT.

CHEAP, STRONG = "claude-haiku-5-5", "claude-sonnet-5-5"
PRICE = {CHEAP: "$0.10 / $0.50", STRONG: "$2 / $10"}   # per million tokens, input / output

ROUTER_PROMPT = """Classify the user's question for a hackathon assistant.
easy: one fact - a time, a place, a rule.
hard: needs planning, comparing several facts, or advice."""


@observe(as_type="span", name="router")
def route(question: str) -> str:
    response = client.messages.create(
        model=CHEAP, max_tokens=1000, system=ROUTER_PROMPT,
        messages=[{"role": "user", "content": question}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {"level": {"type": "string", "enum": ["easy", "hard"]}},
            "required": ["level"], "additionalProperties": False}}},
    )
    return json.loads(next(b.text for b in response.content if b.type == "text"))["level"]


answer_with = ask   # keep step 3's agent - the new ask() below hands work to it

@observe(name="routed")
def ask(question: str) -> str:
    model = STRONG if route(question) == "hard" else CHEAP
    print(f"   🧭 router: {model} ({PRICE[model]} per M tokens)")
    return answer_with(question, model)



# ─── STEP 5 · PASTE THE EVALUATOR HERE ────────────────────────────────────────
# ═══ STEP 5 · PATTERN: EVALUATOR - check the answer in CODE ══════════════════
# WHAT IT IS:  Before the user sees an answer, plain code checks it against the
#              real data. Here: every time it mentions (like "14:00") must exist in
#              the schedule. A wrong answer gets one retry, then a safe fallback.
# WHY IT MATTERS: Never ask the model "are you sure?" - that's letting a student
#              grade their own exam. Check with something that isn't the model.
# MAKE IT BETTER:
#   - Check what MUST be there AND what must NOT be there (a promise you don't offer, a leaked secret)
#   - Facts, numbers, formats, IDs: always check in code. Fuzzy things (tone): an LLM judge with a rubric
#   - Count how often the check fires - that's your real error rate
# CHANGE IT FOR YOUR PROJECT: write one check for the fact your users rely on most.

import re

@observe(as_type="evaluator", name="check-answer")
def check_answer(answer: str) -> list[str]:
    real_times = {s["time"] for s in EVENT["schedule"]}
    return [f"{t} is not in the schedule" for t in re.findall(r"\b\d{1,2}:\d{2}\b", answer) if t.zfill(5) not in real_times]


answer_unchecked = ask   # keep step 4's router + agent

@observe(name="checked")
def ask(question: str) -> str:
    answer = answer_unchecked(question)
    problems = check_answer(answer)
    if not problems:
        return answer
    print(f"   🛑 evaluator: {'; '.join(problems)} - retrying")
    del MEMORY[-2:]          # forget the rejected answer - the user never saw it
    answer = answer_unchecked(f"{question}\n\n(A previous answer said {problems}. Check the schedule tool.)")
    if not check_answer(answer):
        return answer
    del MEMORY[-2:]
    return "I'm not sure about that time - please check with an organiser."



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
