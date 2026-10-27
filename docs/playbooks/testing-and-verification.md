# Playbook: testing and verification

Used by: `test-engineer`, `debugging-specialist`, `performance-engineer`. Read-only reviewers use the last section.

## Running checks

- Use the command the repository already uses (package scripts, Makefile, CI workflow, README). Do not switch frameworks.
- Run the narrowest relevant check first, then the wider suite.
- Quote each command exactly, with the verbatim summary line of its output. Do not paraphrase results.
- Record failures that existed before your change, and keep them separate from new ones.

## Proving a fix or a regression test

1. Run the new test against the old code and quote the failure.
2. Run it against the new code and quote the pass.
3. Run the surrounding suite and quote the result.

If you cannot do step 1, say so. Do not describe a check you did not run.

## Characterization tests

Before changing code that has no test pinning its output, write a test that passes on the current code. Cover the edges a change could break: empty input, duplicates, ties and ordering, boundaries, and large input. Keep the test.

## Probing for invalid behaviour

Try plausible edge inputs: zero, negative, empty, boundary values, values that do not divide evenly, malformed strings. A clearly invalid result (money going negative or no longer adding up, a crash on ordinary input, silent data loss) is a production issue even when no spec covers it. Report the input and the output.

## Tests that cannot run

If a test needs network access, secrets, or services you do not have, mark it **Not run** and give the exact reason or error. Never replace a real result with an expectation.

## For read-only agents

You cannot run anything. For each claim about runtime behaviour, give the exact command a human can run to confirm it, and never predict its pass or fail result.
