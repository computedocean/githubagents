#!/usr/bin/env python3
"""Copy the shared rules block from docs/playbooks/shared-rules.md into every agent profile.

Copilot custom agent profiles cannot include other files, so each profile
carries an exact copy of the block. This script is the only supported way to
update those copies; scripts/validate_agents.py fails if any copy drifts.

Usage:  python scripts/sync_shared_rules.py [repo_root] [--check]
  --check  report profiles that are out of date and exit 1, without writing.
"""

import sys
from pathlib import Path

BEGIN = "<!-- BEGIN SHARED RULES -->"
END = "<!-- END SHARED RULES -->"
SOURCE = Path("docs") / "playbooks" / "shared-rules.md"


def extract_block(text):
    """Return the block from BEGIN to END inclusive, or None if absent or malformed."""
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start or text.count(BEGIN) != 1 or text.count(END) != 1:
        return None
    return text[start:end + len(END)]


def apply_block(text, block):
    """Return text with its shared block replaced by `block` (appended if missing)."""
    current = extract_block(text)
    if current is not None:
        return text.replace(current, block)
    return text.rstrip("\n") + "\n\n" + block + "\n"


def read_text(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    args = [a for a in argv if a != "--check"]
    root = Path(args[0] if args else ".").resolve()

    block = extract_block(read_text(root / SOURCE))
    if block is None:
        print(f"ERROR: {SOURCE} must contain exactly one {BEGIN} ... {END} block")
        return 1

    stale = []
    for path in sorted((root / ".github" / "agents").glob("*.agent.md")):
        text = read_text(path)
        updated = apply_block(text, block)
        if updated != text:
            stale.append(path.name)
            if not check:
                path.write_bytes(updated.encode("utf-8"))

    verb = "out of date" if check else "updated"
    print(f"{len(stale)} profile(s) {verb}" + (": " + ", ".join(stale) if stale else ""))
    return 1 if (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
