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
