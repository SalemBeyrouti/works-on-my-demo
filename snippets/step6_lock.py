# ═══ STEP 6 · THE REAL LOCK: a human click, built into the code ══════════════
# WHAT IT IS:  A tool that does something you can't take back: submitting your
#              checkpoint. The model can ASK to submit. Only a human "y" makes it happen.
# WHY IT MATTERS: AlphaHack twist 04: "anything that can't be undone needs a human click,
#              built into the code, not asked for in the prompt". A prompt can be talked
#              out of a rule. This if-statement can't.
# MAKE IT BETTER:
#   - In a web app the "y" is a button, not input(). Same rule: no click, no action
#   - Show exactly what will happen before asking: what, for whom, where it goes
#   - Log who approved what, and when
# CHANGE IT FOR YOUR PROJECT: put every send / pay / delete / submit tool behind approve().

SUBMITTED = []   # stands in for the real checkpoint form


def approve(action: str) -> bool:
    print(f"   🔒 {action}")
    return input("   approve? [y/N] ").strip().lower() == "y"      # the lock: no "y", no action


def submit_checkpoint(team: str, update: str) -> str:
    if not approve(f"Submit checkpoint for team '{team}': \"{update}\""):
        return "NOT submitted: the user was shown this update and answered no. Nothing was sent."
    SUBMITTED.append({"team": team, "update": update})
    return f"Submitted and final: the user approved it, and team '{team}'s update was sent."


TOOLS = TOOLS + [{"name": "submit_checkpoint",
                  "description": "Submit a team's checkpoint progress update to the organisers. Call it as soon as the user asks: the code itself shows the user what will be sent and asks for approval, so don't ask in chat.",
                  "input_schema": {"type": "object", "properties": {"team": {"type": "string"}, "update": {"type": "string"}},
                                   "required": ["team", "update"]}}]
FUNCTIONS["submit_checkpoint"] = submit_checkpoint
