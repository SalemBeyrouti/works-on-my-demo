"""Run SupportBot on all 20 scenarios and print the score.

    python eval.py        (from this folder)

Then add a line to prompt.txt, run it again, and see what breaks.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from supportbot import classify

sys.stdout.reconfigure(encoding="utf-8")
GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

scenarios = json.loads((Path(__file__).parent / "scenarios.json").read_text(encoding="utf-8"))

# Run all 20 at the same time so the demo takes seconds, not a minute.
with ThreadPoolExecutor(max_workers=10) as pool:
    answers = list(pool.map(lambda s: classify(s["message"]), scenarios))

passed = 0
for s, got in zip(scenarios, answers):
    ok = got == s["expect"]
    passed += ok
    mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    detail = "" if ok else f"  {RED}expected {s['expect']}, got {got}{RESET}"
    print(f" {mark} {DIM}#{s['id']:<2} {s['type']:<12}{RESET} {s['message'][:58]:<58}{detail}")

color = GREEN if passed == len(scenarios) else RED
print(f"\n {BOLD}{color}{passed}/{len(scenarios)} passed{RESET}")
