import json
import textwrap

# ---- LLM CLIENT SETUP (replace with your actual client) ----
# from openai import OpenAI
# client = OpenAI()

def call_architect(system_prompt: str, messages: list) -> str:
    """
    Single call to the Architect LLM.
    Internally, the Architect will use ReAct-style Thought/Action/Observation
    because we encode that in the system prompt and examples.
    """
    # ---- Replace this with your real API call ----
    # resp = client.responses.create(
    #     model="gpt-5.1-thinking",  # or your Mosaic/Databricks endpoint
    #     input=[{"role": m["role"], "content": m["content"]} for m in messages],
    # )
    # content = resp.output[0].content[0].text
    # For now, stub so the script is runnable as a template:
    content = (
        "Thought: I’ll summarize what I’ve learned and propose a next step.\n\n"
        "Action: finish\n\n"
        "Observation: (none)\n\n"
        "FINAL_OUTPUT:\n"
        "{\n"
        '  "summary": "Stub architect response.",\n'
        '  "next_step_hint": "Ask the user for repo structure next."\n'
        "}"
    )
    return content


# ---- JUNIE EXECUTOR (stub) ----

def run_junie_task(task: dict) -> dict:
    """
    Stub Junie executor.
    In reality, this would call your codegen/execution pipeline.
    """
    print("\n[Junie] Executing task:")
    print(json.dumps(task, indent=2))
    # Here you'd modify files, run tests, etc.
    # We'll just pretend everything passed.
    return {
        "task_id": task.get("task_id"),
        "status": "passed",
        "changed_files": task.get("target_files", []),
        "tests": {"unit": {"passed": True}, "lint": {"passed": True}},
        "notes": "Stub: task executed successfully."
    }


# ---- PHASE 1: Architect Onboarding / Initial Briefing ----

def run_architect_onboarding_cycle():
    print("\n=== PHASE 1: New Architect Onboarding ===")

    # 1) Ask user for initial briefing
    print("\nDescribe the overall project for this new Architect.")
    project_brief = input("Project brief > ")

    print("\nPaste any high-level design docs or notes (or leave empty):")
    extra_docs = input("Docs > ")

    system_prompt = textwrap.dedent("""
    You are a Loopforge Architect LLM.

    Your job in THIS PHASE:
    - Absorb the high-level context
    - Ask for missing critical information (one chunk at a time)
    - Produce a short "Architect Onboarding Summary" the human can review

    Use a ReAct-style trace internally:

    Thought: ...
    Action: one of [ask_clarifying_question, finish]
    Observation: ...

    When you are done, return a JSON object under FINAL_OUTPUT with:
    {
      "onboarding_summary": "...",
      "key_unknowns": ["..."],
      "suggested_next_prompts": ["..."]
    }
    """).strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"PROJECT_BRIEF:\n{project_brief}\n\nEXTRA_DOCS:\n{extra_docs}"}
    ]

    raw = call_architect(system_prompt, messages)
    print("\n--- Architect ReAct Trace (Onboarding) ---")
    print(raw)

    # Extract the FINAL_OUTPUT JSON if present
    onboarding_result = extract_final_output(raw)
    print("\n--- Architect Onboarding Summary ---")
    print(json.dumps(onboarding_result, indent=2))

    input("\nIf this looks good, press Enter to continue to Vision phase ...")
    return onboarding_result


# ---- PHASE 2: Vision Draft + User Confirmation ----

def run_vision_cycle(onboarding_result: dict):
    print("\n=== PHASE 2: Vision Draft ===")

    print("\nOptionally refine what you want the Architect to focus on (or leave blank):")
    refinement = input("Vision refinement > ")

    system_prompt = textwrap.dedent("""
    You are a Loopforge Architect LLM.

    In THIS PHASE:
    - Use the onboarding summary and user refinement
    - Articulate a clear vision for the next 1–2 sprints for this project
    - Identify risks, tech debt concerns, and open design questions

    Use ReAct-style Thought/Action internally, but at the end,
    return under FINAL_OUTPUT a JSON:

    {
      "vision_summary": "...",
      "design_principles": ["..."],
      "risk_register": ["..."],
      "open_questions": ["..."]
    }
    """).strip()

    user_content = {
        "onboarding_summary": onboarding_result,
        "user_refinement": refinement,
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_content, indent=2)},
    ]

    raw = call_architect(system_prompt, messages)
    print("\n--- Architect ReAct Trace (Vision) ---")
    print(raw)

    vision_result = extract_final_output(raw)
    print("\n--- Vision Draft ---")
    print(json.dumps(vision_result, indent=2))

    print("\nYou can now manually tweak the vision (e.g., in a text editor) and paste it back.")
    edited = input("Paste edited / approved vision JSON (or press Enter to accept as-is) > ").strip()
    if edited:
        try:
            vision_result = json.loads(edited)
        except Exception as e:
            print(f"Failed to parse edited JSON, keeping original. Error: {e}")

    print("\nVision approved. Moving to Sprint Planning.")
    input("Press Enter to continue ...")
    return vision_result


# ---- PHASE 3: Sprint Planning (Architect → Junie tasks) ----

def run_sprint_planning_cycle(vision_result: dict):
    print("\n=== PHASE 3: Sprint Planning ===")

    print("\nAny constraints for this sprint? (e.g., timebox, files to avoid, etc.)")
    constraints = input("Sprint constraints > ")

    system_prompt = textwrap.dedent("""
    You are a Loopforge Architect LLM.

    In THIS PHASE:
    - Turn the agreed vision into a concrete sprint plan
    - Break work into Junie tasks with clear acceptance criteria
    - Do NOT write code; Junie will do implementation

    At the end, under FINAL_OUTPUT return a JSON:

    {
      "sprint_overview": "...",
      "junie_tasks": [
        {
          "task_id": "string",
          "title": "string",
          "description": "string",
          "target_files": ["..."],
          "acceptance_criteria": ["..."],
          "priority": "P1|P2|P3"
        },
        ...
      ]
    }
    """).strip()

    user_content = {
        "vision": vision_result,
        "constraints": constraints,
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_content, indent=2)},
    ]

    raw = call_architect(system_prompt, messages)
    print("\n--- Architect ReAct Trace (Sprint Planning) ---")
    print(raw)

    planning_result = extract_final_output(raw)
    print("\n--- Sprint Plan ---")
    print(json.dumps(planning_result, indent=2))

    input("\nReview the sprint plan. Press Enter to continue to Junie execution ...")
    return planning_result


# ---- PHASE 4: Junie Execution + Architect Validation ----

def run_junie_execution_loop(planning_result: dict):
    print("\n=== PHASE 4: Junie Execution + Architect Validation ===")

    junie_tasks = planning_result.get("junie_tasks", [])
    if not junie_tasks:
        print("No junie_tasks found; nothing to execute.")
        return

    all_reports = []
    for task in junie_tasks:
        print("\nNext Junie task:")
        print(json.dumps(task, indent=2))
        proceed = input("Run Junie for this task? [y/N] > ").strip().lower()
        if proceed != "y":
            print("Skipping this task.")
            continue

        report = run_junie_task(task)
        all_reports.append(report)
        print("\n[Junie] Report:")
        print(json.dumps(report, indent=2))

        # Architect validates this task’s result
        validation = run_architect_validation_step(task, report)
        print("\n--- Architect Validation for this task ---")
        print(json.dumps(validation, indent=2))

        cont = input("\nContinue to next task? [Y/n] > ").strip().lower()
        if cont == "n":
            break

    print("\n=== All collected Junie reports ===")
    print(json.dumps(all_reports, indent=2))


def run_architect_validation_step(task: dict, report: dict) -> dict:
    """
    Ask Architect to sanity-check Junie's output for one task.
    Here the Architect could also ReAct internally: inspect files, compare to plan, etc.
    """
    system_prompt = textwrap.dedent("""
    You are a Loopforge Architect LLM.

    In THIS PHASE:
    - Validate whether Junie's implementation for ONE task matches the intention
    - Identify mismatches, risks, or follow-up tasks if needed

    At the end, under FINAL_OUTPUT return a JSON:

    {
      "validation_summary": "...",
      "is_acceptable": true,
      "follow_up_tasks": [
        {
          "title": "string",
          "description": "string"
        }
      ]
    }
    """).strip()

    user_content = {
        "task": task,
        "junie_report": report,
        # Optionally: you could add repo snapshots, etc.
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_content, indent=2)},
    ]

    raw = call_architect(system_prompt, messages)
    print("\n--- Architect ReAct Trace (Validation) ---")
    print(raw)

    return extract_final_output(raw)


# ---- Utility: Extract FINAL_OUTPUT JSON from Architect trace ----

def extract_final_output(raw_text: str) -> dict:
    """
    Very simple parser: looks for 'FINAL_OUTPUT:' and tries to parse the following as JSON.
    You will want something more robust in reality.
    """
    marker = "FINAL_OUTPUT:"
    if marker not in raw_text:
        return {"raw": raw_text}

    _, after = raw_text.split(marker, 1)
    after = after.strip()
    # Try to find the first '{' and parse balanced JSON
    try:
        first_brace = after.index("{")
    except ValueError:
        return {"raw": raw_text}

    json_str = after[first_brace:]
    # Very naive: assume it ends at the last '}'.
    last_brace = json_str.rfind("}")
    if last_brace != -1:
        json_str = json_str[: last_brace + 1]

    try:
        return json.loads(json_str)
    except Exception:
        return {"raw": raw_text, "parse_error": True}


# ---- MAIN ENTRYPOINT ----

def main():
    onboarding = run_architect_onboarding_cycle()
    vision = run_vision_cycle(onboarding)
    planning = run_sprint_planning_cycle(vision)
    run_junie_execution_loop(planning)


if __name__ == "__main__":
    main()
