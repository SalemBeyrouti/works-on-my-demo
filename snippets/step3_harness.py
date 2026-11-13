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
