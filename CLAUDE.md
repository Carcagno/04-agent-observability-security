# 04-agent-observability-security

Guidance for agents working in this repository. See `README.md` for the full
project overview.

## Purpose

A minimal two-agent pipeline that serves as a testbed for two Claude Code
capabilities: persistent observability (hook-based traces + a replayable evaluation
harness) and permission-model behaviour. The pipeline is deliberately small — it is
the support for those two topics, not the subject.

## The pipeline

Two subagents in `.claude/agents/`:

- `drafter` — turns a git diff into a structured JSON summary
  (`type` / `scope` / `description`, conventional-commit vocabulary).
- `reviewer` — re-reads that summary against the original diff and returns a
  qualitative verdict (`approved` / `concerns`). This verdict is non-deterministic
  by nature and must not be conflated with the structural validation below.

The orchestrator writes drafter's structured result to
`fixtures/<case>/actual_output.json` so that `tests/run_eval.py` can check it.

### Model choice

`drafter` runs on Haiku (low-ambiguity extraction / classification); `reviewer` runs
on Sonnet (real qualitative comparison between diff and summary).

Neither agent uses tools. The `tools` frontmatter key is omitted rather than set to
`[]` — an empty list fails the subagent launch on current Claude Code versions, and
there is no confirmed syntax for declaring zero tools. The "no tools" rule is
therefore enforced in each agent's prompt, not by the engine.

## Persistent traces (hooks)

`.claude/settings.json` registers two hooks (`PostToolUse`, `SubagentStop`) that call
`scripts/trace_hook.py` on every tool call and every subagent completion. The script
reads the JSON payload Claude Code pipes on stdin and appends one line to
`traces/<session_id>.jsonl`.

The payload schema is documented in `scripts/trace_hook.py` from real invocations.
The script keeps the full raw payload on every line and uses `.get()` with fallbacks
throughout, so a future field rename degrades gracefully rather than breaking the
trace.

## Replayable evaluation

`fixtures/<case>/` contains `diff.txt` (input) and `expected.json` (mechanically
checkable rules — never an exact expected answer, since drafter's text varies between
runs). `tests/run_eval.py` makes no LLM call: it reads `actual_output.json` from a
pipeline run and checks the rules in plain code. The goal is an objective score that
can be replayed after every change to drafter's prompt.

The checks are structural on purpose (type in an allowed set, scope prefix,
description length). Judging semantic quality would require an LLM judge and is out
of scope here — that is `reviewer`'s job, kept separate from the score.

Triggering is manual, never a hook: unlike `trace_hook.py` (observational, must run
on every event), deciding that a run is worth scoring is a choice — made by the
orchestrator via an ordinary `Bash` call, or by a person on the command line.

## Permission experiments

`experiments/part2-permissions-report.md` is the technical report for three
permission-mode experiments, run inside the dev container (`.devcontainer/`) under
`bypassPermissions`. Its findings are backed by the trace excerpts in
`experiments/trace-excerpts/` and sourced to the official documentation.

## Git workflow

No direct commits or pushes to `master`. Every change goes through a dedicated
branch and a pull request, however small. Merges are a human action.

## Language

Code, system prompts, JSON, and commit messages are in English.
