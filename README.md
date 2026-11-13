# Works on My Demo: build an agent in 6 steps

The code from the AlphaHack talk. One file, `agent.py`, grows from a chatbot into an agent with tools, a harness, routing and an evaluator. Every snippet explains what it does and how to adapt it to your project.

| Step | Snippet | What it adds |
|---|---|---|
| 1 | already in `agent.py` | A plain LLM call: a chatbot that doesn't know your data |
| 2 | `snippets/step2_tools.py` | **Tools + the loop**: now it's an agent |
| 2b | `snippets/step2b_bad_tools.py` | The same tools with vague names. Paste it, watch the agent fail, then remove it |
| 3 | `snippets/step3_harness.py` | **The harness**: system prompt, max steps, memory, tracing (Langfuse), cost per answer |
| 4 | `snippets/step4_routing.py` | **Routing pattern**: cheap model for easy questions, strong one for hard |
| 5 | `snippets/step5_evaluator.py` | **Evaluator pattern**: code checks the answer before the user sees it |
| 6 | `snippets/step6_lock.py` | **The real lock**: a tool that can't be undone only runs after a human types "y", enforced in code |

Paste each snippet at its marked spot in `agent.py`, or open the finished version of any step in `checkpoints/`.

## Run it

```bash
pip install anthropic python-dotenv langfuse
cp .env.example .env        # then add your keys
python agent.py "when are the demos?"     # one question
python agent.py                           # chat, with memory
```

## Test it: `supportbot/`

A tiny agent that sorts customer messages into refund, complaint or question, plus 20 tests:

```bash
cd supportbot
python eval.py
```

Add `Anything that mentions refunds should go to the refund team.` to `prompt.txt` and run it again: a few tests break. Then open Claude Code in that folder and paste `claude_fix_prompt.txt`. It reads the failures, fixes the prompt (not the tests) and reruns until 20/20.

The agent reads its schedule, places and rules from `data/event.json`, a made-up sample. Put your real data in `data/event.local.json` (same shape) and the agent uses that instead; `.gitignore` keeps it, and your `.env`, out of git.

Step 3 onwards sends traces to Langfuse (free account at langfuse.com). Without Langfuse keys, the agent still works.

## Use it for your own project

Every snippet has a **CHANGE IT FOR YOUR PROJECT** comment. The usual path:
1. Replace the three tools in step 2 with your own API or database calls.
2. Rewrite `SYSTEM_PROMPT` in step 3 for your users.
3. Write one check in step 5 for the fact your users rely on most.
4. Write 10 test inputs and rerun them after every change. See `supportbot/` for a 30-line example.
