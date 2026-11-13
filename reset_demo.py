"""Put everything back to the start of the talk. Run after every rehearsal.

    python reset_demo.py
"""

import shutil
from pathlib import Path

HERE = Path(__file__).parent
shutil.copy(HERE / "checkpoints" / "agent_step1.py", HERE / "agent.py")
shutil.copy(HERE / "supportbot" / "prompt_clean.txt", HERE / "supportbot" / "prompt.txt")
print("reset: agent.py is back at step 1, supportbot/prompt.txt is clean")
