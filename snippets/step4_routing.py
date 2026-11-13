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
