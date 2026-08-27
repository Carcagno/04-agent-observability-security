#!/usr/bin/env python3
"""Claude Code hook: append one structured trace line per lifecycle event.

Registered on PostToolUse and SubagentStop in .claude/settings.json. Claude Code
invokes this script and pipes a JSON payload describing the event on stdin.

Deliberately defensive: the exact payload schema (field names like `session_id`,
`tool_name`, `hook_event_name`...) is written here from memory of Claude Code's docs,
NOT verified against a real hook invocation yet -- see CLAUDE.md. Every access below
uses .get() with a fallback, and the full raw payload is kept in each trace line, so
no information is lost even if the assumed field names turn out to be wrong. Fix this
script once the real payload has been inspected, don't just trust it.
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
        "subagent_type": payload.get("subagent_type") or payload.get("agent_type"),
        "raw": payload,
    }

    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    trace_file = TRACES_DIR / f"{run_id}.jsonl"
    with trace_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
