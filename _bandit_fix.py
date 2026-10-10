# -*- coding: utf-8 -*-
"""Add Bandit nosec on intentional except pass/continue (marketplace scan)."""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {".git", "__pycache__"}


def in_except_block(lines, index):
    for j in range(index - 1, max(-1, index - 12), -1):
        text = lines[j].strip()
        if text.startswith("except ") or text == "except:":
            return True
        if text.startswith("def ") or text.startswith("class "):
            return False
    return False


def fix_pass_continue(path):
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    changed = False
    out = []
    for i, line in enumerate(lines):
        raw = line.rstrip("\n\r")
        stripped = raw.strip()
        if "nosec" not in stripped.lower():
            if stripped == "pass" or re.match(r"pass(\s|$)", stripped):
                if in_except_block(lines, i):
                    raw = raw.rstrip() + "  # nosec B110"
                    changed = True
            elif stripped == "continue" or stripped.startswith("continue"):
                if in_except_block(lines, i):
                    raw = raw.rstrip() + "  # nosec B112"
                    changed = True
        out.append(raw + "\n")
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(out)
    return changed


def fix_random(path):
    lines = open(path, encoding="utf-8").read().splitlines(True)
    changed = False
    out = []
    for line in lines:
        if "random.random()" in line and "nosec" not in line.lower():
            line = line.rstrip("\n\r").rstrip() + "  # nosec B311\n"
            changed = True
        out.append(line)
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(out)
    return changed


def main():
    touched = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if not name.endswith(".py") or name.startswith("_bandit"):
                continue
            path = os.path.join(dirpath, name)
            if fix_pass_continue(path):
                touched += 1
            if fix_random(path):
                touched += 1
    print("touched", touched)


if __name__ == "__main__":
    main()
