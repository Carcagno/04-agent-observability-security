#!/usr/bin/env python3
"""Deterministic, replayable check of drafter's structured output against fixed rules.

No LLM call happens in this script. It only reads whatever `actual_output.json` a
previous pipeline run left behind for each fixture (the orchestrator is responsible
for writing that file -- see CLAUDE.md) and checks it against `expected.json`. This is
deliberately not a semantic/content judgment ("is the description any good?") -- that
would require an LLM judge, out of scope here (see roadmap-agentique.md, "En cours"
note on evaluation). What it checks is purely mechanical, so re-running it always
gives the same verdict for the same actual_output.json.
"""
import json
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def check_case(case_dir: Path):
    expected_path = case_dir / "expected.json"
    actual_path = case_dir / "actual_output.json"

    if not actual_path.exists():
        return "SKIPPED", ["no actual_output.json yet -- run the pipeline on this fixture first"]

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    actual = json.loads(actual_path.read_text(encoding="utf-8"))

    failures = []

    if actual.get("type") not in expected["type_in"]:
        failures.append(f"type={actual.get('type')!r} not in {expected['type_in']}")

    scope = actual.get("scope", "")
    if not scope.startswith(expected["scope_prefix"]):
        failures.append(f"scope={scope!r} does not start with {expected['scope_prefix']!r}")

    description = actual.get("description", "")
    if not (expected["description_min_len"] <= len(description) <= expected["description_max_len"]):
        failures.append(
            f"description length {len(description)} outside "
            f"[{expected['description_min_len']}, {expected['description_max_len']}]"
        )

    return ("PASS" if not failures else "FAIL"), failures


def main() -> int:
    cases = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
    if not cases:
        print("No fixtures found under fixtures/.")
        return 1

    results = []
    for case_dir in cases:
        status, details = check_case(case_dir)
        results.append(status)
        print(f"[{status}] {case_dir.name}")
        for line in details:
            print(f"    - {line}")

    passed = results.count("PASS")
    failed = results.count("FAIL")
    skipped = results.count("SKIPPED")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped ({len(results)} total)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
