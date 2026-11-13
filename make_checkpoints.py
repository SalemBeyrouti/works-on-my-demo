"""Builds checkpoints/agent_step1.py ... agent_step6.py by pasting the snippets into agent.py.

Your safety net on stage: if a paste goes wrong, open the checkpoint for that step and carry on.
agent_step6.py is also the finished agent you run at the very start of the talk.

    python make_checkpoints.py
"""

from pathlib import Path

HERE = Path(__file__).parent
SNIPPETS = {
    2: ("STEP 2 · PASTE THE TOOLS + THE LOOP HERE", "step2_tools.py"),
    3: ("STEP 3 · PASTE THE HARNESS HERE", "step3_harness.py"),
    4: ("STEP 4 · PASTE THE ROUTER HERE", "step4_routing.py"),
    5: ("STEP 5 · PASTE THE EVALUATOR HERE", "step5_evaluator.py"),
    6: ("STEP 6 · PASTE THE LOCK HERE", "step6_lock.py"),
}

out = HERE / "checkpoints"
out.mkdir(exist_ok=True)
lines = (HERE / "agent.py").read_text(encoding="utf-8").splitlines()
(out / "agent_step1.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

for step, (marker, snippet) in SNIPPETS.items():
    at = next(i for i, line in enumerate(lines) if marker in line)
    code = (HERE / "snippets" / snippet).read_text(encoding="utf-8").rstrip().splitlines()
    lines = lines[: at + 1] + code + [""] + lines[at + 1 :]
    (out / f"agent_step{step}.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("wrote", ", ".join(sorted(p.name for p in out.glob("agent_step*.py"))))
