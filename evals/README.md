# Agent evaluation harness

A repeatable way to measure how well each agent in [.github/agents/](../.github/agents/) does its job, and whether a profile change made it better or worse.

This folder holds the **procedure, rubric, and task prompts only**. Expected findings (answer keys) and scorecards are deliberately **not** stored here, because every file in this repository is visible to the agents being evaluated. Keep them somewhere the agents cannot read. A private repository is best; a local, never-pushed branch also works.

## What a run measures

Each run gives one agent one task against one fixed starting state, then checks the result against an answer key written **before** the run. A run is a proxy for a real Agents-tab task in one of two ways:

- **Agents tab (authoritative):** start the task on GitHub with the agent selected. This is the only way to measure GitHub Copilot itself.
- **Local proxy:** give the profile body to a capable model as its system instructions, with tools limited to the profile's `tools`. This measures the profile's instructions, not Copilot's model or runtime. Label proxy results as proxy results.

## Benchmark cases

| Case | Starting state | Used for |
|---|---|---|
| S | Sample app (`app/`, `tests/`) | code-reviewer, security-reviewer, debugging-specialist, performance-engineer, test-engineer, software-architect, implementation-planner, research-analyst |
| D | S plus manifests, a CI workflow, and a Dockerfile | dependency-supply-chain-reviewer |
| Doc | S with a deliberately out-of-date `app/README.md` | documentation-engineer |
| H | A held-out package with different defect types | Generalization check: run old and new profiles on it |

Fixture branches are kept local and are never pushed, because some of them contain deliberately unsafe code or CI configuration. Never deploy them or expose them to a network.

Add new held-out cases regularly. An agent tuned against a case you have already looked at no longer tells you how it generalizes.

## Procedure

1. Write or update the answer key for the case **before** running anything. Store it outside the repository.
2. For every run, create a fresh, clean, detached worktree at the case's commit, so one agent can never see another agent's fixes:
   ```bash
   git worktree add --detach ../runs/<agent>-<case> <case-commit>
   ```
3. Give the agent the exact prompt from [tasks.md](tasks.md) for that case. Do not add hints.
4. After the run, audit it independently. Do not rely on the agent's report:
   - `git -C <worktree> status --porcelain` and `git diff`: read-only agents must leave no changes; editing agents must stay within their boundaries.
   - Re-run every test or benchmark the agent says it ran.
   - Check every `path:line` citation and every external citation you can.
   - For optimizations, compare old and new outputs on generated inputs.
5. Score the run with the rubric below and record false positives and missed findings separately.
6. To compare profile versions, run both versions on the same case, including at least one held-out case, and compare totals and misses.

## Rubric (0–4 per dimension, 24 maximum)

| Dimension | 4 | 2 | 0 |
|---|---|---|---|
| Correctness of findings | All expected findings, no false positives | About half found, or notable false positives | Wrong or absent |
| Quality of evidence | Every claim cites `path:line` or a source that checks out | Some claims uncited or generic | No evidence |
| Root-cause reasoning | Causal chain explained and correct | Symptom described, cause partly right | Wrong cause |
| Quality of recommendations | Specific, correct, minimal, and actionable | Generic or partly wrong | Absent or harmful |
| Verification and regression testing | Ran (or, for read-only agents, specified) the right checks and quoted real results | Some checks missing, or results narrated rather than shown | Claims of success without evidence |
| Scope control | No changes outside the agent's boundaries; unrelated code untouched | Minor out-of-scope edits | Read-only agent changed files, or unrelated code damaged |

Generic advice without evidence caps "evidence" and "recommendations" at 2.

## Files

- [tasks.md](tasks.md): the exact task prompts per agent and case.
