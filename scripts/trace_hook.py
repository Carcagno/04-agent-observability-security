#!/usr/bin/env python3
"""Claude Code hook: append one structured trace line per lifecycle event.

Registered on PostToolUse and SubagentStop in .claude/settings.json. Claude Code
invokes this script and pipes a JSON payload describing the event on stdin.

Payload schema verified against real hook invocations on 2026-08-27/28 (see CLAUDE.md):
  - both events carry: session_id, transcript_path, cwd, prompt_id, permission_mode,
    hook_event_name
  - PostToolUse adds: tool_name, tool_input, tool_response, tool_use_id; plus
    agent_id + agent_type ONLY when the call originates inside a subagent (an
    orchestrator-level PostToolUse has neither, but carries `effort` instead)
  - SubagentStop adds: agent_id, agent_type, agent_transcript_path, stop_hook_active,
    last_assistant_message, background_tasks, session_crons; tool_name is absent
  - there is NO `subagent_type` field -- the real name is `agent_type`

Still deliberately defensive: every access uses .get() with a fallback, and the full
raw payload is kept in each trace line, so nothing is lost if a future Claude Code
version renames a field.
"""
import json
import os
import sys
import time
from pathlib import Path

TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"_unparsed_stdin": raw}

    run_id = (
        payload.get("session_id")
        or os.environ.get("CLAUDE_SESSION_ID")
        or "unknown-session"
    )

    event = {
        "ts": time.time(),
        "hook_event": payload.get("hook_event_name", "unknown"),
        "tool_name": payload.get("tool_name"),
        # `agent_type` is set on SubagentStop and on subagent-internal PostToolUse;
        # it is None for orchestrator-level tool calls. That None vs non-None is the
        # cleanest way to tell the two apart in the trace.
        "agent_type": payload.get("agent_type"),
        "agent_id": payload.get("agent_id"),
        # permission_mode is on every payload -- promoted to top level because the
        # part-2 permission experiments key off it.
        "permission_mode": payload.get("permission_mode"),
        "raw": payload,
    }

    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    trace_file = TRACES_DIR / f"{run_id}.jsonl"
    with trace_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
