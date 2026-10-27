# Evaluating the agents

This folder holds a repeatable way to measure how well each agent in [.github/agents/](../.github/agents/) does its job, and whether a profile change made it better or worse. It contains the **procedure and the cases only**.

## Two kinds of checks

| Kind | What it proves | How to run |
|---|---|---|
| **Static** (deterministic, free) | Profiles are well formed, follow the library's structure, carry the current shared rules, and have evaluation cases | `python scripts/validate_agents.py`, plus `python -m unittest discover -s scripts -v` for the checker's own tests |
| **Behavioural** (needs a model) | An agent actually does its job on a realistic task | Run the cases in [cases.json](cases.json), then audit and score each run (below) |

Static checks never prove runtime behaviour. A profile can pass every static check and still behave badly.

## Cases

[cases.json](cases.json) lists one or more cases per agent. Each case has a `prompt`, which you use exactly as written, and `acceptance_criteria` a reviewer can check. It also records two statuses: `proxy_status`, the last local proxy run, and `agents_tab_status`, the last run in GitHub's Agents tab.

What the cases deliberately leave out:

- **No expected findings.** Everything in this repository, every branch included, can be read by the agents being evaluated, so answer keys and scorecards must live elsewhere. A private repository is best. The validator rejects case fields that look like stored answers.
- **No fixture code.** The benchmark fixtures (a small Python app, a dependency and CI fixture, a documentation-drift fixture, and a held-out package) contain deliberately vulnerable code and unsafe configuration, some of which GitHub would act on if it were pushed. They are **kept local, not published**. To run the cases yourself, build equivalent fixtures in a private repository or a local branch you never push. Keep the matching answer key outside that repository too.

## Running a behavioural case

1. Write or confirm the answer key for the fixture **before** any run, and store it outside the repository.
2. Start every run from a fresh, clean, detached worktree at the fixture commit, so one agent never sees another agent's changes:
   ```bash
   git worktree add --detach ../runs/<agent>-<case> <fixture-commit>
   ```
3. Run the agent with the case's prompt:
   - **Agents tab (authoritative):** select the agent in GitHub's Agents tab, against a private repository containing the fixture. This is the only way to measure GitHub Copilot itself.
   - **Local proxy:** give the profile body to a model you already have access to as its instructions, with tools limited to the profile's `tools` list. This measures the profile's instructions, not Copilot's model or runtime. Always label these as proxy results.
4. Audit the run without relying on the agent's own report:
   ```bash
   python scripts/audit_run.py ../runs/<agent>-<case> <agent>
   ```
   This checks that read-only agents changed nothing, the documentation engineer touched only docs, and the test engineer touched only tests. Then:
   - re-run every test or benchmark the agent claims to have run;
   - check every `path:line` and external citation;
   - for optimizations, compare old and new outputs on generated inputs.
5. Score the run with the rubric below, and record false positives and missed findings separately, outside the repository.

## Rubric (0–4 per dimension, 24 maximum)

| Dimension | 4 | 2 | 0 |
|---|---|---|---|
| Correctness of findings | All expected findings, no false positives | About half, or notable false positives | Wrong or absent |
| Quality of evidence | Every claim cites a `path:line` or source that checks out | Some claims uncited or generic | No evidence |
| Root-cause reasoning | Causal chain explained and correct | Symptom described, cause partly right | Wrong cause |
| Quality of recommendations | Specific, correct, minimal, actionable | Generic or partly wrong | Absent or harmful |
| Verification and regression testing | Ran (or, for read-only agents, specified) the right checks and quoted real results | Some checks missing, or results narrated rather than shown | Success claimed without evidence |
| Scope control | Stayed within its boundary; unrelated code untouched | Minor out-of-scope edits | A read-only agent changed files, or unrelated code was damaged |

Generic advice without evidence caps "evidence" and "recommendations" at 2.

Totals bunch near the top for capable models. Track specific behaviours as pass/fail as well (for example, "quoted red and green output"), because they show changes more clearly than the totals do.

## Improvement loop

This is a manual loop. Nothing here learns or updates itself.

1. Run the cases for the agents you plan to change, and record a baseline outside the repository.
2. Describe each weakness as a general behaviour (for example, "describes checks it did not run"), not as a missed planted defect.
3. Change the profile, or the shared rules in [docs/playbooks/shared-rules.md](../docs/playbooks/shared-rules.md) followed by `python scripts/sync_shared_rules.py`, so that it addresses the behaviour in general.
4. Run `python scripts/validate_agents.py` and the unit tests.
5. Re-run the same cases **and at least one held-out case** the change was not designed around, with both the old and the new profile.
6. Keep the change only if the targeted behaviour improves on both, and nothing regresses. A fix can introduce a new failure mode, so read the new outputs, not only the scores.
7. Update `proxy_status` or `agents_tab_status` in [cases.json](cases.json) to the new results.
8. Add new held-out cases from time to time. A case you have tuned against no longer tells you how the agent generalizes.

## Current status (2026-10-27)

- **Static checks:** pass.
- **Proxy runs:** with the final profiles, 11 cases were re-run locally: one per agent, plus `H-test`. Every run met its acceptance criteria when audited independently: `scripts/audit_run.py`, re-running every test the agent ran, and checking optimized output against the original. The other held-out cases were last run with the previous profile version. Observed weaknesses that remain: one code review missed a lower-severity finding that earlier runs caught, and it worded some "How to verify" steps as expected outcomes, although it labelled them `[Unverified]`.
- **Agents tab:** **no case has been run there yet.** Behaviour in GitHub Copilot is unverified.
