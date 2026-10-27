# Evaluation task prompts

Use these prompts exactly as written, so runs stay comparable across profile versions. Expected results are kept outside this repository (see [README.md](README.md)).

## Case S — sample app

| Agent | Prompt |
|---|---|
| code-reviewer | Review the sample shop app on this branch, everything under app/ and tests/. |
| security-reviewer | Do a security review of this repository's application code. |
| debugging-specialist | Two tests in tests/test_orders.py are failing. Find out why and fix it. |
| performance-engineer | `python -m app.bench` is too slow. Make the code it exercises faster and show me the numbers. |
| test-engineer | Find the coverage gaps in app/ and add tests for the untested behaviour. Don't change production code. |
| software-architect | We want this shop app to serve multiple concurrent users through an HTTP API, with data that survives restarts. Assess the current architecture and recommend how to get there. |
| implementation-planner | Plan adding a `report top-customers` subcommand to the CLI that prints the top N customers by spend, with an optional --csv flag. |
| research-analyst | Three questions about this repo: (1) How does scripts/validate_agents.py decide whether a tool name in an agent profile is valid? (2) What does GitHub actually do when a custom agent profile lists a tool name it doesn't recognise, and which tool aliases don't apply to the Copilot cloud agent? (3) Which module in app/ converts prices between currencies, and what exchange-rate source does it use? |

## Case D — dependency fixture

| Agent | Prompt |
|---|---|
| dependency-supply-chain-reviewer | Audit this repository's dependencies, CI workflow, and container build for supply-chain risk. |

## Case Doc — documentation drift

| Agent | Prompt |
|---|---|
| documentation-engineer | app/README.md seems out of date. Bring it in line with the code, and add a short configuration reference section for the settings in app/config.py. |

## Case H — held-out package

The same tasks as case S, with paths changed to the held-out package (for example, `ledger/` and `tests/test_ledger.py`). Keep the wording otherwise identical, and change the singular/plural only where the number of failing tests differs.
