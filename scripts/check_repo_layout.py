#!/usr/bin/env python3
"""Guard the user-facing repository layout and local Markdown links.

This checks organization only; the existing Momentum SDK and native-C CI
remain responsible for application compilation and functional tests.
"""
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MANIFEST = (ROOT / "application.fam").read_text(encoding="utf-8")

assert SRC.is_dir(), "src/ must contain application C/header files"
assert (SRC / "labmate.c").is_file(), "main app entry point missing from src/"
assert (SRC / "labmate_ui_screens.c").is_file(), "UI module missing"
assert (SRC / "labmate_generator.c").is_file(), "PWM module missing"
assert len(list(SRC.glob("*.c"))) >= 20, "unexpectedly few source files"
assert len(list(SRC.glob("*.h"))) >= 20, "unexpectedly few header files"
assert not list(ROOT.glob("*.c")) and not list(ROOT.glob("*.h")), (
    "app source/header files must not clutter the repository root"
)
assert 'sources=["src/*.c"]' in MANIFEST, (
    "application.fam must compile relocated source files"
)
assert (ROOT / "docs/releases/RELEASE_NOTES_v1.7.md").is_file()
assert (ROOT / "docs/archive/DATA_LOGGER_v1.5_DEV.md").is_file()

# Markdown inline links: leave all external URLs and in-page anchors alone.
# Resolve local links relative to each Markdown file's own directory.
bad = []
total = 0
for markdown in ROOT.rglob("*.md"):
    if ".git" in markdown.parts:
        continue
    text = markdown.read_text(encoding="utf-8")
    for match in re.finditer(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text):
        target = match.group(1).strip().split(" ", 1)[0].strip("<>")
        if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
            continue
        path = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not path:
            continue
        total += 1
        if not (markdown.parent / path).exists():
            bad.append(f"{markdown.relative_to(ROOT)} -> {target}")

if bad:
    raise AssertionError("Broken local Markdown links:\n" + "\n".join(bad))
print(f"Repository layout PASS: source in src/, checked {total} local Markdown links")
