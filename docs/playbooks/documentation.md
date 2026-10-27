# Playbook: documentation

Used by: `documentation-engineer`, `research-analyst`.

## The code is the source of truth

Verify every command, flag, default, path, and example against the code. If the docs and the code disagree, fix the docs and report the discrepancy. Do not change the code to match the docs.

## Drift classes to check in existing text

- entry-point commands and module paths;
- subcommands and flags;
- test commands and where the tests live;
- environment variables and configuration sources;
- files and modules named in layout tables;
- third-party tools assumed to be installed.

## Writing

- Name the audience (user, contributor, operator) and the task they are trying to do.
- Put procedures in numbered steps, with commands you can paste.
- Keep relative links working, and check that each target exists.
- Never document a feature, flag, or module you cannot find in the code.
- Never include secret values. Describe a secret setting by name and purpose only.

## Verification checklist

If you cannot run a documented command, list it with what the user should look for. Describe only what the source determines. Never predict whether tests pass or how many will run; write "outcome not checked" instead.
