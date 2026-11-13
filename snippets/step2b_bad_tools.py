# ═══ STEP 2b · THE SAME TOOLS, NAMED BADLY (paste, run, then UNDO) ═══════════
# WHAT IT SHOWS: the exact same functions, but with the names and descriptions most
#              people write at 3 AM. The model chooses tools ONLY from this text.
# WHAT HAPPENS:  Measured: with these, the agent got all three test questions wrong.
#              Asked "how many people per team?", it replied "which team - a sport?"
#              because nothing told it a rules tool exists.
# LESSON: tool names and descriptions are a user interface - for the model.
# ⚠ Ctrl+Z after the demo: this snippet is meant to be removed.

TOOLS = [
    {"name": "tool_a", "description": "Returns data.", "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}}},
    {"name": "tool_b", "description": "Returns data.", "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}},
    {"name": "tool_c", "description": "Returns data.", "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}}},
]
FUNCTIONS = {"tool_a": lambda x=None: get_schedule(x), "tool_b": lambda x: find_room(x), "tool_c": lambda x=None: get_rules(x)}
