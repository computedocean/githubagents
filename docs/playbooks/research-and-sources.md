# Playbook: research and source verification

Used by: `research-analyst`, `dependency-supply-chain-reviewer`, `software-architect`.

## Order of sources

1. The repository itself: code, tests, config, docs, and git history.
2. GitHub metadata the tools can read: issues, pull requests, advisories.
3. Primary external sources: official documentation, specifications, release notes, advisory databases (GitHub Advisory Database, OSV.dev, the ecosystem's own feed).
4. Secondary sources (blogs, forum answers), only for leads you then confirm in a primary source.

## Checking a claim

- Open the source and find the exact sentence or line. A search-result snippet is not a citation.
- Record the URL or `path:line`, plus the version or date when it is visible.
- If two sources disagree, report both, say which you trust more, and why.
- If a question rests on a false premise (for example, it asks about a module that does not exist), say so plainly. Do not invent an answer to fit the question.
- If you cannot find a source, say "not found" and list where you looked.

## When web access is missing

The `web` tool does not work on the GitHub.com cloud agent. Without it, answer from the repository and the `github` tools, and mark anything you would need the web to confirm as **[Unverified]**, saying what would confirm it.

## Red flags

- A citation you have not opened in this task.
- A version number, CVE ID, or API name written from memory.
- A summary that is more confident than its sources.
