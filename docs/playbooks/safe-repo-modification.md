# Playbook: safe repository modification

Used by: `test-engineer`, `documentation-engineer`, `performance-engineer`, `debugging-specialist`.

## Before the first edit

- Read the files you will change, plus their callers and tests.
- Note the repository's conventions (naming, formatting, line endings, test layout) and match them.
- Run the relevant tests first, so you know which failures already exist.

## While editing

- Change only what the task needs. Do not refactor, rename, reformat, or upgrade along the way.
- Keep edits inside your agent's boundary: tests only, docs only, or the minimal production change.
- Never weaken, skip, or delete a test or assertion to make something pass.
- Do not add dependencies or configuration without asking (see the shared rules).
- Preserve the existing line endings and encoding of each file.

## After editing

- Re-run the tests and quote the summary lines.
- Review your own diff: no debug prints, scratch files, generated files, or unrelated changes.
- List every file you changed and why.
- Leave the work uncommitted unless the user asked you to commit. Never push.
