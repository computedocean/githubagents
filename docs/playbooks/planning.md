# Playbook: planning

Used by: `implementation-planner`, `software-architect`.

## Before writing a plan

- Read the code the change will touch, and list what you read.
- Find an existing pattern to follow: a similar feature, helper, or test.
- Split requirements into **given** (stated by the user or the repository) and **assumed** (yours, to be confirmed).
- Look for missing inputs. For example: where does the data come from? Who calls this? What happens on error? A plan that ignores a missing input is wrong, however tidy it looks.

## Shape of a good step

- Small enough to review in one sitting.
- Leaves the build green and the tests passing.
- Names the files, and the functions or classes where known.
- States how to verify it: a specific test or command.
- States what it depends on, so independent steps can run in parallel.

## Scope

- Plan only what was asked. List adjacent clean-ups as optional, separately.
- No new dependencies, services, or infrastructure unless a requirement needs them. When one is needed, also give a no-dependency alternative.
- Size steps as S/M/L and say what drives the size. Do not estimate hours.

## Hand-offs

- An architecture choice is still open → `software-architect` first.
- Security-sensitive steps → note `security-reviewer`.
- Performance-sensitive steps → note `performance-engineer`.
- Writing the tests → `test-engineer`.
