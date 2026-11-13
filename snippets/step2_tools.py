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
