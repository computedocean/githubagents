# GitHub Copilot Custom Agent Library

Ten specialist [custom agents](https://docs.github.com/en/copilot/reference/custom-agents-configuration) for GitHub Copilot. Once the profiles are on a repository's default branch, you can pick any of them in the Agents tab instead of the default Copilot cloud agent.

Each agent has one job, explicit boundaries, the fewest tools it needs, and completion criteria you can check. Every agent must support its claims with evidence and must stop and ask before risky actions. The reviewers and planners are read-only: they cannot change files or run commands.

## Contents

| Path | Purpose |
|---|---|
| [.github/agents/](.github/agents/) | The ten agent profiles (`*.agent.md`) |
| [docs/playbooks/](docs/playbooks/) | Shared rules and detailed playbooks the profiles follow |
| [evals/](evals/README.md) | Evaluation procedure, rubric, improvement loop, and cases ([cases.json](evals/cases.json)) |
| [scripts/validate_agents.py](scripts/validate_agents.py) | Static checks for the whole library |
| [scripts/sync_shared_rules.py](scripts/sync_shared_rules.py) | Copies the shared rules into every profile |
| [scripts/audit_run.py](scripts/audit_run.py) | Checks that an evaluation run stayed within the agent's file boundary |
| [scripts/test_validate_agents.py](scripts/test_validate_agents.py) | Unit tests for the three scripts |

All scripts use only the Python standard library. There are no dependencies, services, or accounts to set up.

## The agents

| Agent | Use it to… | Tools | Access | Example prompt |
|---|---|---|---|---|
| [`research-analyst`](.github/agents/research-analyst.agent.md) | Get a cited, evidence-labelled answer to a technical question | read, search, web, github/* | Read-only | "How does authentication flow through this codebase? Cite the files." |
| [`software-architect`](.github/agents/software-architect.agent.md) | Map the current design, compare options, and get an ADR | read, search, github/* | Read-only | "Propose options for adding background jobs, with an ADR." |
| [`implementation-planner`](.github/agents/implementation-planner.agent.md) | Turn a goal into ordered, verifiable steps | read, search, github/* | Read-only | "Plan CSV export for reports, following the PDF export pattern." |
| [`code-reviewer`](.github/agents/code-reviewer.agent.md) | Get correctness and maintainability findings, ranked by severity | read, search, github/* | Read-only | "Review pull request #42; focus on error handling." |
| [`security-reviewer`](.github/agents/security-reviewer.agent.md) | Get source-to-sink security findings, rated by impact × reachability | read, search, github/* | Read-only | "Security review the upload endpoint and everything it calls." |
| [`dependency-supply-chain-reviewer`](.github/agents/dependency-supply-chain-reviewer.agent.md) | Audit dependencies, Actions pinning, and base images | read, search, web, github/* | Read-only | "Audit our dependencies and workflows for supply-chain risk." |
| [`test-engineer`](.github/agents/test-engineer.agent.md) | Add tests, probe edge cases, and get exact per-test results | read, search, edit, execute | Edits tests | "Add tests for `parseInvoice`, including malformed input, and run them." |
| [`debugging-specialist`](.github/agents/debugging-specialist.agent.md) | Find a root cause and get a minimal fix with a red/green regression test | read, search, edit, execute | Edits code | "`test_refund_partial` fails intermittently. Find the cause and fix it." |
| [`performance-engineer`](.github/agents/performance-engineer.agent.md) | Measure, optimize, re-measure, with a characterization test | read, search, edit, execute | Edits code | "`/search` is slow on large result sets. Profile it and fix the main bottleneck." |
| [`documentation-engineer`](.github/agents/documentation-engineer.agent.md) | Make docs match the code | read, search, edit | Edits docs, no shell | "Update the README's setup section to match the scripts in package.json." |

The restrictions "edits tests" and "edits docs" are instructions in the profile, not technical limits: GitHub's `edit` tool cannot be restricted to particular paths. Review those agents' pull requests as you would any other, or audit their changes with `scripts/audit_run.py`.

## How a profile is built

Every profile has the same structure:

1. **Scope:** what is in scope, what is not, and which agent to use instead.
2. **Workflow:** starts with an intake step, then the inspect-before-acting steps.
3. **Role-specific rules:** for example, the severity scales and the "quote, don't narrate" reporting rules.
4. **Edge and negative cases:** what to do when the input is missing, contradictory, or out of scope.
5. **Output format and completion criteria.**
6. **Playbooks:** links to the detailed playbooks that apply.
7. **Shared operating rules:** least privilege, untrusted content, secrets, stop-and-ask-a-human points, cost, ambiguity, evidence labels, a final self-check, and a closing Facts / Assumptions / Recommendations / Open questions summary.

Copilot profiles cannot include other files, so section 7 is an **exact copy** of [docs/playbooks/shared-rules.md](docs/playbooks/shared-rules.md), and the validator fails if any copy drifts. The playbooks hold more detail. A profile tells the agent to read them *if they exist in the repository*, and is complete without them, so a profile still works when copied into a repository that has no playbooks.

| Playbook | Used by |
|---|---|
| [research-and-sources](docs/playbooks/research-and-sources.md) | research-analyst, dependency reviewer, architect |
| [planning](docs/playbooks/planning.md) | implementation-planner, architect |
| [safe-repo-modification](docs/playbooks/safe-repo-modification.md) | test, docs, performance, debugging |
| [testing-and-verification](docs/playbooks/testing-and-verification.md) | test, debugging, performance, code reviewer |
| [security-review](docs/playbooks/security-review.md) | security reviewer, dependency reviewer, code reviewer (hand-offs) |
| [debugging-and-recovery](docs/playbooks/debugging-and-recovery.md) | debugging, performance |
| [documentation](docs/playbooks/documentation.md) | documentation-engineer |
| [final-quality-review](docs/playbooks/final-quality-review.md) | all agents |

The agents never coordinate automatically. You run one agent per task. When work is outside an agent's scope, it names the right agent, and you start that task yourself. Typical sequences:
- **New feature:** research-analyst → software-architect → implementation-planner → (implementation) → test-engineer → code-reviewer and security-reviewer.
- **Bug:** debugging-specialist → code-reviewer.

## Using the agents on GitHub

1. Put the profiles in `.github/agents/` on the repository's **default branch**. They appear in the Agents tab only from there.
   - **Other repositories:** copy `.github/agents/`, and optionally `docs/playbooks/`.
   - **Every repository in an organization:** an org owner can put the profiles in a top-level `agents/` folder of the org's `.github` or `.github-private` repository. A repository-level profile with the same name takes precedence.
2. Open the Agents tab at <https://github.com/copilot/agents>, choose the repository, and pick an agent from the agent drop-down. Refresh the page if it is missing.
3. Give it a task. The cases in [evals/cases.json](evals/cases.json) give a realistic prompt and acceptance criteria for each agent.

## Checking the library

Run from the repository root:

```bash
python scripts/validate_agents.py
```

```bash
python -m unittest discover -s scripts -v
```

```bash
python scripts/sync_shared_rules.py --check
```

The validator checks:
- **Frontmatter:** valid, with only documented properties, a required `description`, `name` matching the filename, and recognised tool names. GitHub silently ignores unknown tools, so a typo would quietly remove a permission.
- **Agent set:** all ten expected agents exist, with no duplicates.
- **Tools:** read-only agents grant no `edit`, `execute`, or `*`.
- **Structure:** required sections and an intake step; the body is under 30,000 characters; code fences are balanced.
- **Shared rules:** each profile's block matches the source exactly.
- **Playbooks:** every link resolves, and every playbook is used by some agent.
- **Distinctness:** agent descriptions do not overlap heavily.
- **Evaluation cases:** every agent has cases with at least two acceptance criteria, and no stored answers.
- **Links:** relative links in the README, the eval docs, and the playbooks resolve.

These are static checks. Passing them does not prove an agent behaves well; [evals/README.md](evals/README.md) explains how to test behaviour.

On Windows, if the checkout path is very long, pass the root with the long-path prefix, for example `python scripts/validate_agents.py "\\?\C:\path\to\repo"`.

## Changing the library safely

- **Editing a profile:** change only its role-specific sections, keep the required headings, then run the three commands above.
- **Changing the shared rules:** edit [docs/playbooks/shared-rules.md](docs/playbooks/shared-rules.md), then run `python scripts/sync_shared_rules.py`. Never edit the copies inside profiles by hand.
- **Adding an agent:**
  1. Create `.github/agents/<kebab-name>.agent.md` with the same structure. List tools explicitly, because leaving out `tools` grants everything.
  2. Run the sync script.
  3. Add the agent to `EXPECTED_AGENTS` in the validator, and to `READ_ONLY_AGENTS` if it must not edit or execute.
  4. Add at least one case to `evals/cases.json`, and a row to the table above.
- **Changing tools:** grant the fewest that work. Before giving a review agent `edit` or `execute`, consider handing the work to an editing agent instead.
- **Before merging a behaviour change:** follow the improvement loop in [evals/README.md](evals/README.md). Re-run the affected cases plus a held-out case, with the old and new profile, and keep the change only if nothing regresses.

## Security and privacy

- Every agent treats repository content, issues, and web pages as untrusted data. It never prints secrets, and it stops to ask before pushing, merging, changing settings or CI, changing dependencies, calling external services, or anything it cannot undo.
- No profile adds MCP servers, secrets, or external integrations. `github/*` is GitHub's built-in server, which is read-only by default and scoped to the repository.
- **Never store answer keys or scorecards for the evaluation fixtures in this repository.** The agents can read every file and branch in it. Keep them in a private repository.
- The benchmark fixtures used to evaluate these agents contain deliberately vulnerable code. They are kept local, and are not part of this repository.

## Compatibility and limitations

**Verified against GitHub's docs** ([configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration), checked 2026-10-27):
- profiles are `.md` / `.agent.md` files with the documented frontmatter properties and tool aliases;
- the body limit is 30,000 characters;
- profiles on the default branch are used;
- `web` and `todo` are not available to the cloud agent;
- `argument-hint` and `handoffs` are ignored on GitHub.com;
- `infer` is retired.

**Not verified here:**
- How each agent behaves in GitHub's hosted Agents tab. No case has been run there yet; the local proxy runs measure the profile instructions with a different model and runtime.
- How the cloud agent presents results from read-only agents. They cannot commit files, so the result is expected in the session log or the pull request.
- Whether the cloud agent reads the `docs/playbooks/` files at runtime. The profiles are written to be complete without them.
- Which Copilot plans and organization policies enable custom agents. Org-level agents need a plan that supports them; check your plan.

Other limits:
- `execute` runs in Copilot's sandbox, not on your machine, so tests that need services, secrets, or network may not run there.
- `model` is not set, because it applies only in IDEs.
- Custom agents are still evolving. Re-check the configuration reference from time to time, and update `KNOWN_KEYS` and `TOOL_ALIASES` in the validator when it changes.
