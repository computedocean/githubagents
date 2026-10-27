#!/usr/bin/env python3
"""Validate the GitHub Copilot custom agent library in this repository.

Checks each profile in .github/agents/ against the format in GitHub's
"Custom agents configuration" reference, plus this library's own rules
(see README.md, "Changing the library safely"):

- all expected agents exist, with valid frontmatter and explicit tools;
- read-only agents grant no edit/execute tools;
- each body has the required sections and an intake step;
- each profile carries an exact copy of docs/playbooks/shared-rules.md;
- playbook links resolve, and every playbook is used by some agent;
- agent descriptions are distinct from each other;
- evals/cases.json gives every agent cases with verifiable acceptance
  criteria and stores no expected answers;
- relative links in the library's Markdown files resolve.

These are static checks. They do not prove how an agent behaves at runtime;
see evals/README.md for behavioural evaluation.

Standard library only. If PyYAML happens to be installed, frontmatter is
also parsed with yaml.safe_load as a cross-check.

Usage:  python scripts/validate_agents.py [repo_root]
Exit code 0 = all checks passed, 1 = at least one error.
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml  # optional cross-check only
except ImportError:
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_shared_rules import SOURCE as SHARED_SOURCE, extract_block  # noqa: E402

MAX_BODY_CHARS = 30_000
FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.agent\.md$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")

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

# The library's agents. Adding or removing one means updating this set,
# README.md, and evals/cases.json together.
EXPECTED_AGENTS = {
    "research-analyst", "software-architect", "code-reviewer",
    "security-reviewer", "test-engineer", "documentation-engineer",
    "performance-engineer", "debugging-specialist",
    "dependency-supply-chain-reviewer", "implementation-planner",
}
READ_ONLY_AGENTS = {
    "research-analyst", "software-architect", "code-reviewer",
    "security-reviewer", "dependency-supply-chain-reviewer",
    "implementation-planner",
}
REQUIRED_SECTIONS = [
    "## Scope", "## Workflow", "## Edge and negative cases",
    "## Output format", "## Completion criteria", "## Playbooks",
]
INTAKE_MARKER = "**Intake.**"
MAX_DESCRIPTION_OVERLAP = 0.35

PLAYBOOKS_DIR = Path("docs") / "playbooks"
CASES_FILE = Path("evals") / "cases.json"
CASE_KEYS = {"id", "agent", "fixture", "prompt", "acceptance_criteria",
             "proxy_status", "agents_tab_status"}
CASE_STATUSES = {"not run", "passed", "failed", "partial"}
LINKED_DOCS = ["README.md", "evals/README.md"]


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


def read_text(path):
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")


def resolve_relative(base_dir, target):
    """Join and normalise a relative link, keeping Windows \\\\?\\ long-path prefixes working.

    The OS does not collapse '..' inside \\\\?\\ paths, so normalise the rest of the path ourselves.
    """
    joined = str(base_dir / target)
    prefix = "\\\\?\\"
    if joined.startswith(prefix):
        return Path(prefix + os.path.normpath(joined[len(prefix):]))
    return Path(os.path.normpath(joined))


def broken_links(path, text):
    """Relative Markdown links in `text` (from file `path`) whose target does not exist."""
    missing = []
    for target in LINK_RE.findall(text):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not resolve_relative(path.parent, target).exists():
            missing.append(target)
    return missing


def check_markdown(body):
    errors = []
    fences = [l for l in body.split("\n") if l.lstrip().startswith("```")]
    if len(fences) % 2:
        errors.append("unbalanced ``` code fences in body")
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^{re.escape(section)}\s*$", body, re.M):
            errors.append(f"missing required section '{section}'")
    workflow = re.search(r"^## Workflow\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if workflow and INTAKE_MARKER not in workflow.group(1):
        errors.append(f"'## Workflow' must start with an {INTAKE_MARKER} step")
    return errors


def validate_profile(path, shared_block=None):
    """Return (name, description, errors, warnings) for one profile file."""
    errors, warnings = [], []
    stem = path.name[: -len(".agent.md")] if path.name.endswith(".agent.md") else path.stem
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
        return stem, "", errors + [str(exc)], warnings

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
        desc = ""

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

    if shared_block is not None:
        block = extract_block(body)
        if block is None:
            errors.append("missing shared rules block; run scripts/sync_shared_rules.py")
        elif block != shared_block:
            errors.append("shared rules block differs from docs/playbooks/shared-rules.md; "
                          "run scripts/sync_shared_rules.py")

    for target in broken_links(path, body):
        errors.append(f"link to missing file: {target}")

    return name, desc, errors, warnings


def description_overlap(a, b):
    words_a = {w for w in re.findall(r"[a-z]+", a.lower()) if len(w) > 3}
    words_b = {w for w in re.findall(r"[a-z]+", b.lower()) if len(w) > 3}
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def check_cases(root, agent_names):
    path = root / CASES_FILE
    if not path.exists():
        return [f"{CASES_FILE} not found"]
    try:
        cases = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        return [f"{CASES_FILE}: invalid JSON: {exc}"]
    if not isinstance(cases, list):
        return [f"{CASES_FILE}: top level must be a list of cases"]

    errors, seen_ids, covered = [], set(), set()
    for i, case in enumerate(cases):
        label = f"{CASES_FILE} case {i}"
        if not isinstance(case, dict):
            errors.append(f"{label}: must be an object")
            continue
        label = f"{CASES_FILE} case '{case.get('id', i)}'"
        extra = set(case) - CASE_KEYS
        if extra:
            errors.append(f"{label}: unexpected keys {sorted(extra)} (expected answers must "
                          "not be stored in the repository)")
        for key in CASE_KEYS - set(case):
            errors.append(f"{label}: missing '{key}'")
        if case.get("id") in seen_ids:
            errors.append(f"{label}: duplicate id")
        seen_ids.add(case.get("id"))
        agent = case.get("agent")
        if agent not in agent_names:
            errors.append(f"{label}: unknown agent '{agent}'")
        else:
            covered.add(agent)
        if not isinstance(case.get("prompt"), str) or not case.get("prompt", "").strip():
            errors.append(f"{label}: 'prompt' must be a non-empty string")
        criteria = case.get("acceptance_criteria")
        if (not isinstance(criteria, list) or len(criteria) < 2
                or not all(isinstance(c, str) and c.strip() for c in criteria)):
            errors.append(f"{label}: 'acceptance_criteria' needs at least 2 non-empty strings")
        for key in ("proxy_status", "agents_tab_status"):
            if key in case and case[key] not in CASE_STATUSES:
                errors.append(f"{label}: '{key}' must be one of {sorted(CASE_STATUSES)}")
    for agent in sorted(agent_names - covered):
        errors.append(f"{CASES_FILE}: no evaluation case for agent '{agent}'")
    return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0] if argv else ".").resolve()
    agents_dir = root / ".github" / "agents"
    profiles = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    if not profiles:
        print(f"ERROR: no profiles found in {agents_dir}")
        return 1

    shared_path = root / SHARED_SOURCE
    shared_block = extract_block(read_text(shared_path)) if shared_path.exists() else None
    print(f"Validating {len(profiles)} profile(s) in {agents_dir}"
          f" (PyYAML cross-check: {'on' if yaml else 'off, not installed'})\n")

    failed, names, descriptions = 0, {}, {}
    for path in profiles:
        name, desc, errors, warnings = validate_profile(path, shared_block)
        if name in names:
            errors.append(f"duplicate agent name also used by {names[name]}")
        names[name] = path.name
        descriptions[name] = desc
        failed += bool(errors)
        print(f"[{'FAIL' if errors else 'PASS'}] {path.name}")
        for e in errors:
            print(f"    error:   {e}")
        for w in warnings:
            print(f"    warning: {w}")

    library = []
    if shared_block is None:
        library.append(f"{SHARED_SOURCE} is missing or has no valid shared rules block")
    for agent in sorted(EXPECTED_AGENTS - names.keys()):
        library.append(f"expected agent '{agent}' is missing")
    for agent in sorted(names.keys() - EXPECTED_AGENTS):
        library.append(f"agent '{agent}' is not in EXPECTED_AGENTS (update the validator, "
                       "README.md, and evals/cases.json together)")
    ordered = sorted(descriptions)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            overlap = description_overlap(descriptions[a], descriptions[b])
            if overlap > MAX_DESCRIPTION_OVERLAP:
                library.append(f"descriptions of '{a}' and '{b}' overlap {overlap:.0%}; "
                               "make their purposes distinct")

    profile_text = "\n".join(read_text(p) for p in profiles)
    playbooks_dir = root / PLAYBOOKS_DIR
    for playbook in sorted(playbooks_dir.glob("*.md")) if playbooks_dir.is_dir() else []:
        if playbook.name != SHARED_SOURCE.name and f"playbooks/{playbook.name}" not in profile_text:
            library.append(f"playbook {playbook.name} is not referenced by any agent profile")

    library.extend(check_cases(root, set(names) & EXPECTED_AGENTS or EXPECTED_AGENTS))

    docs = [root / d for d in LINKED_DOCS] + (sorted(playbooks_dir.glob("*.md"))
                                               if playbooks_dir.is_dir() else [])
    for doc in docs:
        if not doc.exists():
            library.append(f"{doc.relative_to(root).as_posix()} not found")
            continue
        for target in broken_links(doc, read_text(doc)):
            library.append(f"{doc.relative_to(root).as_posix()} links to missing file: {target}")

    print(f"\n[{'FAIL' if library else 'PASS'}] library checks (agent set, shared rules, "
          "distinct purposes, playbooks, eval cases, links)")
    for e in library:
        print(f"    error:   {e}")

    print(f"\n{len(profiles) - failed}/{len(profiles)} profiles passed; "
          f"library checks {'failed' if library else 'passed'}.")
    return 1 if (failed or library) else 0


if __name__ == "__main__":
    sys.exit(main())
