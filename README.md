# Agent Observability & Security

A small two-agent pipeline used as a testbed for two Claude Code capabilities:

- **Persistent observability** — hook-based tracing plus a replayable evaluation harness.
- **Permission-model behaviour** — the permission modes exercised against a live
  Claude Code session and cross-checked with the official documentation, rather than
  taken on trust.

The pipeline itself is intentionally minimal. It exists to give the two capabilities
above something concrete to act on; it is not the point of the project.

## What the pipeline does

It turns a git diff into a reviewed, structured commit summary:

1. **`drafter`** (Haiku) reads a unified diff and emits
   `{type, scope, description}` using conventional-commit vocabulary.
2. **`reviewer`** (Sonnet) reads the diff *and* drafter's summary, then returns a
   qualitative `{approved, concerns}` verdict.
3. The orchestrator writes drafter's JSON to `fixtures/<case>/actual_output.json`.
4. `tests/run_eval.py` checks that output against fixed structural rules — no LLM
   call, identical verdict for identical input.

## Capabilities demonstrated

### 1. Persistent observability via hooks

- `.claude/settings.json` registers `scripts/trace_hook.py` on `PostToolUse` and
  `SubagentStop`.
- Every tool call and every subagent completion appends one JSON line to
  `traces/<session_id>.jsonl`. The full raw hook payload is kept on each line, so no
  field is lost even if a Claude Code version renames one.
- The payload schema is documented in the script, from real invocations. Findings
  worth noting:
  - the real field is `agent_type`, not `subagent_type`;
  - `PostToolUse` also fires for tool calls made *inside* a subagent — those lines
    carry a non-null `agent_type`, which is the clean way to tell them apart from
    orchestrator-level calls;
  - `PostToolUse` only fires *after* a successful call, so a blocked call never
    reaches the hook (see the permissions report for where this matters).

### 2. Replayable evaluation

- `fixtures/<case>/` holds `diff.txt` (input), `expected.json` (mechanical rules)
  and `actual_output.json` (the last pipeline run).
- `run_eval.py` checks `type` against an allowed set, the `scope` prefix, and the
  `description` length. It is deterministic — the same `actual_output.json` always
  produces the same verdict.
- Structural by design. Judging whether the description is *semantically* good would
  need an LLM judge; that job belongs to `reviewer`, which is non-deterministic and
  kept separate from the score.
- The loop in action: an early run failed on description length (80–84 chars against
  a 72 cap); tightening drafter's prompt brought it green without a model change.

### 3. Permission-model behaviour, tested live

`experiments/part2-permissions-report.md` documents three experiments run inside a
dev container under `bypassPermissions`:

1. **`git push --force`** — passes with no check under `bypassPermissions` and
   really rewrites remote history. The only classifier-style guard still active in
   that mode is the critical-path circuit-breaker: `rmdir /usr` was prompted and
   denied even here.
2. **`dontAsk` vs `bypassPermissions`** on a trivial file write — opposite ends of
   one spectrum: deny-by-default versus allow-by-default, and neither ever prompts.
3. **Writing into `.claude/` and `.git/`** (protected paths) — allowed silently
   under `bypassPermissions`, via both the `Write` tool and a Bash redirect.

Every direct observation is backed by a real trace line in
`experiments/trace-excerpts/`. Claims about the other permission modes are sourced
to the official docs, with reproduction commands included in the report.

## Architecture

| Piece | File | Role |
| --- | --- | --- |
| drafter agent | `.claude/agents/drafter.md` | diff → structured summary (Haiku) |
| reviewer agent | `.claude/agents/reviewer.md` | summary + diff → qualitative verdict (Sonnet) |
| trace hook | `scripts/trace_hook.py` | one JSONL line per tool call / subagent stop |
| hook registration | `.claude/settings.json` | `PostToolUse` + `SubagentStop` matchers |
| eval harness | `tests/run_eval.py` | deterministic structural check, no LLM |
| fixtures | `fixtures/case-*/` | input diff + expected rules + last output |
| permissions report | `experiments/` | live permission-mode findings + trace evidence |
| dev container | `.devcontainer/devcontainer.json` | isolated environment for `bypassPermissions` testing |

### Model choice

- `drafter` → **Haiku**: low-ambiguity extraction and classification.
- `reviewer` → **Sonnet**: a real qualitative comparison between the diff and the
  summary.
- Neither agent uses tools. The `tools` frontmatter key is omitted rather than set
  to `[]` (an empty list fails subagent launch on current Claude Code versions), so
  the "no tools" rule is enforced at the prompt level, not by the engine.

## Tools and integrations used

- **Claude Code subagents** (`.claude/agents/`) — the drafter/reviewer pipeline.
- **Claude Code hooks** (`PostToolUse`, `SubagentStop`) — the tracing mechanism.
- **GitHub CLI (`gh`)** — remote repository and the branch/PR workflow.
- **Dev Containers** — `mcr.microsoft.com/devcontainers/base:ubuntu` plus the Node
  and `claude-code` features, for isolated permission testing.
- **Python 3**, standard library only (`json`, `pathlib`, `time`) — no third-party
  dependencies.
- No external MCP servers; the pipeline is self-contained.

## Running it

### Evaluation (no LLM, no setup)

```bash
python tests/run_eval.py
```

Reads each `fixtures/<case>/actual_output.json`, checks it against `expected.json`,
and exits non-zero if any case fails.

### The full pipeline (requires Claude Code)

From a Claude Code session in this repository:

1. Invoke `drafter` with the contents of a `fixtures/<case>/diff.txt`.
2. Invoke `reviewer` with the same diff plus drafter's JSON output.
3. Write drafter's JSON to `fixtures/<case>/actual_output.json`.
4. Run `python tests/run_eval.py`.

The hooks fire automatically for every tool call; the trace lands in
`traces/<session_id>.jsonl` (gitignored).

### Permission experiments

See `experiments/part2-permissions-report.md` for the exact
`claude --permission-mode ...` reproduction commands. Run them inside the dev
container under `.devcontainer/`.

## Repository layout

```
.claude/
  agents/{drafter,reviewer}.md   pipeline agents
  settings.json                  hook registration
.devcontainer/devcontainer.json  isolated environment for permission tests
scripts/trace_hook.py            the tracing hook
tests/run_eval.py                deterministic evaluation
fixtures/case-*/                  diff.txt + expected.json + actual_output.json
experiments/
  part2-permissions-report.md    permission-mode findings
  trace-excerpts/*.json          raw trace evidence
traces/                          per-session JSONL (gitignored)
```

## Git workflow

Every change goes through a dedicated branch and a pull request; no direct commits
to `master`. Merges are performed by a human.
