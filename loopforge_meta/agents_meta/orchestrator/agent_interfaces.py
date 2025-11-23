import json
from datetime import datetime
from loopforge_meta.agents_meta.snapshotter.prompts import snapshotter_system_prompt, snapshotter_trigger_prompt

# Default Context for the snapshotter trigger prompt (can be overridden at call time)
DEFAULT_SNAPSHOTTER_CONTEXT = """
    * The repository has recently undergone a major refactor and is now fully layered.
    * Ignore any previous snapshots unless explicitly inserted here (none is provided in this prompt).
    * Extract all modules, identify responsibilities, list key entrypoints, dependencies, and surface uncertainties.
    * Begin extraction.
    """

def call_snapshotter_llm(files, context:str=None):
    # 1) Prepare input payload
    payload = {
        "repo_root": ".",
        "files": files,
    }

    system_prompt = snapshotter_system_prompt()
    user_message = (
        snapshotter_trigger_prompt() + "\n\n" + context + "\n\n" +
        f"INPUT:\n{json.dumps(payload)}"
    )

    # 2) Call your LLM platform here
    raw_output = call_llm(system_prompt, user_message)  # you implement this

    # 3) Parse JSON
    snapshot = json.loads(raw_output)
    return snapshot
