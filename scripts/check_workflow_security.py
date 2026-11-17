#!/usr/bin/env python3
"""Basic supply-chain policy guard for GitHub Actions workflows.

Checks only a few easy-to-enforce text invariants, not full YAML semantics.
Approval, token permissions, release provenance and security of the pinned
upstream commits still require human review.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
USES = re.compile(r"^\\s*-?\\s*uses:\\s*([^\\s#]+)", flags=re.MULTILINE)
PIN = re.compile(r"^[^@\\s]+@[a-fA-F0-9]{40}$")


def main() -> int:
    failures: list[str] = []
    sources = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    if not sources:
        print("FAIL: no GitHub Actions workflows found")
        return 1

    count = 0
    for path in sources:
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\\s*pull_request_target\\s*:", text):
            failures.append(f"{path.name}: pull_request_target requires separate review")
        if not re.search(r"(?m)^permissions\\s*:", text):
            failures.append(f"{path.name}: explicit workflow permissions missing")
        for match in USES.finditer(text):
            uses = match.group(1)
            if uses.startswith("./"):
                continue  # repository-local actions do not have remote refs
            count += 1
            if not PIN.fullmatch(uses):
                failures.append(f"{path.name}: action is not pinned to a 40-hex commit")

    for item in failures:
        print("FAIL: " + item)  # never print token contents or entire workflow lines
    if failures:
        return 1
    print(f"PASS: checked {len(sources)} workflows and {count} pinned remote action references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
