# Playbook: debugging and recovery

Used by: `debugging-specialist`, `performance-engineer`.

## Loop

1. **Symptom:** write down what was expected, what happened, and how to reproduce it.
2. **Reproduce:** run the failing test or a minimal script, and quote the command and output.
3. **Hypothesize:** list candidate causes, then test them one at a time with targeted evidence.
4. **Root cause:** name the `file:line` and the causal chain from cause to symptom.
5. **Fix:** make the smallest change at the root cause.
6. **Prove it:** run a regression test red then green (see the testing playbook), then the surrounding suite.

## When it does not reproduce

Say so. Continue with code analysis, label the conclusions **[Not reproduced]**, and list what you tried: inputs, environment, and timing.

## Flaky and intermittent failures

Run the test several times and report the pass/fail counts. Look for shared state, ordering, time, randomness, and concurrency. Do not "fix" a flaky test by adding retries or sleeps without naming the cause.

## Causes outside the code

If the root cause is in a dependency, the environment, or configuration, report it with evidence. Do not patch around it silently, and ask before upgrading anything.

## Recovery

- Keep the original state recoverable: no history rewrites, and no deleting work you did not create.
- If a change makes things worse, revert your own change and say so.
- Remove temporary logging and scratch scripts before finishing.
