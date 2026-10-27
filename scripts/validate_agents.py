#!/usr/bin/env python3
"""Validate GitHub Copilot custom agent profiles in .github/agents/.

Checks each profile against the format described in GitHub's
"Custom agents configuration" reference, plus this library's own
conventions (see README.md, "Maintaining the library").

Standard library only. If PyYAML happens to be installed, the frontmatter
is additionally parsed with yaml.safe_load as a cross-check.

Usage:  python scripts/validate_agents.py [repo_root]
Exit code 0 = all checks passed, 1 = at least one error.
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml  # optional cross-check only
except ImportError:
    yaml = None

MAX_BODY_CHARS = 30_000
FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.agent\.md$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")

# Properties documented for repository-level agent profiles.
KNOWN_KEYS = {
    "name", "description", "target", "tools", "model",
    "disable-model-invocation", "user-invocable", "infer",
    "mcp-servers", "metadata",
    # IDE-only; ignored on GitHub.com but not invalid.
    "argument-hint", "handoffs",
}
BOOL_KEYS = {"disable-model-invocation", "user-invocable", "infer"}
TARGETS = {"vscode", "github-copilot"}
TOOL_ALIASES = {
    "execute", "shell", "bash", "powershell",
    "read", "notebookread",
    "edit", "multiedit", "write", "notebookedit",
    "search", "grep", "glob",
    "agent", "custom-agent", "task",
    "web", "websearch", "webfetch",
    "todo", "todowrite",
    "*",
}
MCP_TOOL_RE = re.compile(r"^[A-Za-z0-9._-]+/([A-Za-z0-9._-]+|\*)$")
WRITE_TOOLS = {"edit", "multiedit", "write", "notebookedit",
               "execute", "shell", "bash", "powershell"}

# Library policy: these agents must stay read-only.
READ_ONLY_AGENTS = {
    "research-analyst", "software-architect", "code-reviewer",
    "security-reviewer", "dependency-supply-chain-reviewer",
    "implementation-planner",
}
REQUIRED_SECTIONS = ["## Scope", "## Completion criteria"]


def parse_scalar(raw):
    raw = raw.strip()
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith("["):
        return json.loads(raw)  # flow lists in this library are JSON-compatible
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def split_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("file must start with a '---' frontmatter delimiter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise ValueError("frontmatter is not closed with '---'")


def parse_frontmatter(fm):
    data = {}
    for n, line in enumerate(fm.split("\n"), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t-":
            raise ValueError(f"line {n}: nested YAML is not supported by this validator; "
                             "use single-line 'key: value' entries")
        m = KEY_RE.match(line)
        if not m:
            raise ValueError(f"line {n}: not a 'key: value' entry: {line!r}")
        key, value = m.groups()
        if key in data:
            raise ValueError(f"line {n}: duplicate key '{key}'")
        try:
            data[key] = parse_scalar(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {n}: invalid list for '{key}': {exc}") from None
    return data


def check_markdown(body):
    errors = []
    fences = [l for l in body.split("\n") if l.lstrip().startswith("```")]
    if len(fences) % 2:
        errors.append("unbalanced ``` code fences in body")
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^{re.escape(section)}\b", body, re.M):
            errors.append(f"missing required section '{section}'")
    return errors


def validate_profile(path):
    errors, warnings = [], []
    stem = path.name[: -len(".agent.md")]
    if not FILENAME_RE.match(path.name):
        errors.append("filename may contain only letters, digits, '.', '-', '_' and must end in .agent.md")

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("file has a UTF-8 BOM; save without BOM")
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")

    try:
        fm, body = split_frontmatter(text)
        data = parse_frontmatter(fm)
    except ValueError as exc:
        return stem, errors + [str(exc)], warnings

    if yaml is not None:
        try:
            if yaml.safe_load(fm) != data:
                errors.append("PyYAML parse differs from validator parse; simplify the frontmatter")
        except yaml.YAMLError as exc:
            errors.append(f"PyYAML rejected the frontmatter: {exc}")

    for key in data:
        if key not in KNOWN_KEYS:
            errors.append(f"unknown frontmatter property '{key}'")
    if "infer" in data:
        warnings.append("'infer' is retired; use 'disable-model-invocation' / 'user-invocable'")

    desc = data.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("'description' is required and must be a non-empty string")

    name = data.get("name", stem)
    if not isinstance(name, str) or not name.strip():
        errors.append("'name' must be a non-empty string")
    elif name != stem:
        errors.append(f"'name' ({name}) should match the filename stem ({stem})")

    if "target" in data and data["target"] not in TARGETS:
        errors.append(f"'target' must be one of {sorted(TARGETS)}")
    for key in BOOL_KEYS & data.keys():
        if not isinstance(data[key], bool):
            errors.append(f"'{key}' must be true or false")

    tools = data.get("tools")
    if tools is None:
        warnings.append("'tools' omitted: the agent gets ALL tools; list them explicitly")
        tools = []
    elif not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        errors.append("'tools' must be a list of strings")
        tools = []
    for tool in tools:
        if tool.lower() not in TOOL_ALIASES and not MCP_TOOL_RE.match(tool):
            errors.append(f"unrecognized tool '{tool}' (GitHub silently ignores unknown tools)")
    if len({t.lower() for t in tools}) != len(tools):
        errors.append("'tools' contains duplicates")
    if stem in READ_ONLY_AGENTS:
        granted = WRITE_TOOLS & {t.lower() for t in tools}
        if granted or "*" in tools:
            errors.append(f"read-only agent grants write/exec tools: {sorted(granted) or ['*']}")

    if not body.strip():
        errors.append("body (agent instructions) is empty")
    if len(body) > MAX_BODY_CHARS:
        errors.append(f"body is {len(body)} chars; maximum is {MAX_BODY_CHARS}")
    errors.extend(check_markdown(body))

    return name, errors, warnings


def check_readme_links(root):
    readme = root / "README.md"
    if not readme.exists():
        return ["README.md not found"]
    errors = []
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", readme.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("mailto:"):
            continue
        if not (root / target).exists():
            errors.append(f"README.md links to missing file: {target}")
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    agents_dir = root / ".github" / "agents"
    profiles = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    if not profiles:
        print(f"ERROR: no profiles found in {agents_dir}")
        return 1

    print(f"Validating {len(profiles)} profile(s) in {agents_dir}"
          f" (PyYAML cross-check: {'on' if yaml else 'off, not installed'})\n")
    failed, names = 0, {}
    for path in profiles:
        name, errors, warnings = validate_profile(path)
        if name in names:
            errors.append(f"duplicate agent name also used by {names[name]}")
        names[name] = path.name
        status = "FAIL" if errors else "PASS"
        failed += bool(errors)
        print(f"[{status}] {path.name}")
        for e in errors:
            print(f"    error:   {e}")
        for w in warnings:
            print(f"    warning: {w}")

    link_errors = check_readme_links(root)
    print(f"\n[{'FAIL' if link_errors else 'PASS'}] README.md relative links")
    for e in link_errors:
        print(f"    error:   {e}")

    total_fail = failed + bool(link_errors)
    print(f"\n{len(profiles) - failed}/{len(profiles)} profiles passed; "
          f"README links {'failed' if link_errors else 'passed'}.")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
