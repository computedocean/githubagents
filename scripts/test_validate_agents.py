"""Unit tests for validate_agents.py, sync_shared_rules.py, and audit_run.py.

Run from the repository root:  python -m unittest discover -s scripts -v
"""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_run  # noqa: E402
import sync_shared_rules as sync  # noqa: E402
import validate_agents as va  # noqa: E402

SHARED = f"{sync.BEGIN}\n## Shared operating rules\n\nBe careful.\n{sync.END}"
GOOD_BODY = (
    "Intro.\n\n## Scope\n\nStuff.\n\n## Workflow\n\n1. **Intake.** Restate it.\n\n"
    "## Edge and negative cases\n\n- None.\n\n## Output format\n\nText.\n\n"
    "## Completion criteria\n\n- Done.\n\n## Playbooks\n\nNone here.\n\n" + SHARED + "\n"
)


def profile(name="sample", description="Does a thing.", tools='["read", "search"]',
            extra="", body=GOOD_BODY):
    lines = ["---", f"name: {name}"]
    if description is not None:
        lines.append(f"description: {description}")
    if tools is not None:
        lines.append(f"tools: {tools}")
    if extra:
        lines.append(extra)
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, text, filename="sample.agent.md", raw=None, shared=SHARED):
        path = self.dir / filename
        if raw is not None:
            path.write_bytes(raw)
        else:
            write(path, text)
        name, _desc, errors, warnings = va.validate_profile(path, shared)
        return name, errors, warnings

    def assertError(self, errors, fragment):
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_valid_profile_passes(self):
        self.assertEqual(self.check(profile()), ("sample", [], []))

    def test_crlf_line_endings_accepted(self):
        _, errors, _ = self.check(None, raw=profile().replace("\n", "\r\n").encode())
        self.assertEqual(errors, [])

    def test_missing_description(self):
        _, errors, _ = self.check(profile(description=None))
        self.assertError(errors, "'description' is required")

    def test_unknown_property(self):
        _, errors, _ = self.check(profile(extra="color: red"))
        self.assertError(errors, "unknown frontmatter property 'color'")

    def test_retired_infer_warns(self):
        _, errors, warnings = self.check(profile(extra="infer: false"))
        self.assertEqual(errors, [])
        self.assertTrue(any("retired" in w for w in warnings))

    def test_name_must_match_filename(self):
        _, errors, _ = self.check(profile(name="other"))
        self.assertError(errors, "should match the filename stem")

    def test_invalid_filename(self):
        _, errors, _ = self.check(profile(name="bad name"), filename="bad name.agent.md")
        self.assertError(errors, "filename may contain only")

    def test_invalid_target(self):
        _, errors, _ = self.check(profile(extra="target: browser"))
        self.assertError(errors, "'target' must be one of")

    def test_boolean_property_type(self):
        _, errors, _ = self.check(profile(extra="disable-model-invocation: yes"))
        self.assertError(errors, "must be true or false")

    def test_unrecognized_tool(self):
        _, errors, _ = self.check(profile(tools='["read", "raed"]'))
        self.assertError(errors, "unrecognized tool 'raed'")

    def test_mcp_tool_references_accepted(self):
        _, errors, _ = self.check(profile(tools='["read", "github/*", "playwright/browser_click"]'))
        self.assertEqual(errors, [])

    def test_duplicate_tools(self):
        _, errors, _ = self.check(profile(tools='["read", "Read"]'))
        self.assertError(errors, "duplicates")

    def test_omitted_tools_warns(self):
        _, errors, warnings = self.check(profile(tools=None))
        self.assertEqual(errors, [])
        self.assertTrue(any("ALL tools" in w for w in warnings))

    def test_read_only_agent_cannot_edit_or_execute(self):
        for tools in ('["read", "edit"]', '["read", "execute"]', '["*"]'):
            with self.subTest(tools=tools):
                _, errors, _ = self.check(profile(name="code-reviewer", tools=tools),
                                          filename="code-reviewer.agent.md")
                self.assertError(errors, "read-only agent grants")

    def test_body_length_limit(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY + "x" * va.MAX_BODY_CHARS))
        self.assertError(errors, "maximum is")

    def test_unbalanced_code_fence(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY + "```\ncode\n"))
        self.assertError(errors, "unbalanced")

    def test_required_sections(self):
        _, errors, _ = self.check(profile(body="Just text.\n" + SHARED))
        for section in va.REQUIRED_SECTIONS:
            self.assertError(errors, f"'{section}'")

    def test_workflow_needs_intake_step(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY.replace("**Intake.**", "First,")))
        self.assertError(errors, "Intake")

    def test_shared_block_missing(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY.replace(SHARED, "")))
        self.assertError(errors, "missing shared rules block")

    def test_shared_block_drift(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY.replace("Be careful.", "Be bold.")))
        self.assertError(errors, "differs from docs/playbooks/shared-rules.md")

    def test_broken_playbook_link(self):
        _, errors, _ = self.check(profile(body=GOOD_BODY.replace(
            "None here.", "[x](../../docs/playbooks/missing.md)")))
        self.assertError(errors, "link to missing file")

    def test_missing_frontmatter_keeps_filename_error(self):
        _, errors, _ = self.check("no frontmatter", filename="bad name.agent.md")
        self.assertError(errors, "filename may contain only")
        self.assertError(errors, "must start with a '---'")

    def test_unclosed_frontmatter(self):
        _, errors, _ = self.check("---\nname: sample\n")
        self.assertError(errors, "not closed")

    def test_nested_yaml_rejected(self):
        _, errors, _ = self.check(profile(extra="metadata:\n  team: x"))
        self.assertError(errors, "nested YAML")

    def test_bom_rejected(self):
        _, errors, _ = self.check(None, raw=b"\xef\xbb\xbf" + profile().encode())
        self.assertError(errors, "BOM")


class OverlapTests(unittest.TestCase):
    def test_identical_descriptions_overlap_fully(self):
        self.assertEqual(va.description_overlap("reviews code quality", "reviews code quality"), 1.0)

    def test_unrelated_descriptions_do_not_overlap(self):
        self.assertEqual(va.description_overlap("measures latency", "writes documentation"), 0.0)


WORDS = ("alpha bravo charlie delta echoes foxtrot golfer hotel india juliet kilos limas "
         "mikes november oscar papas quebec romeo sierra tango uniform victor whiskey xrays "
         "yankee zulus amber basil cedar dahlia").split()


def make_library(root, agents=va.EXPECTED_AGENTS):
    """Build a minimal valid library under root."""
    write(root / "docs/playbooks/shared-rules.md", "# Shared\n\n" + SHARED + "\n")
    write(root / "docs/playbooks/planning.md", "# Planning\n")
    for i, agent in enumerate(sorted(agents)):
        body = GOOD_BODY.replace("None here.", "[p](../../docs/playbooks/planning.md)")
        # Three words unique to each agent, so the overlap check passes.
        description = " ".join(WORDS[3 * i:3 * i + 3]) + "."
        write(root / f".github/agents/{agent}.agent.md",
              profile(name=agent, description=description, tools='["read", "search"]', body=body))
    cases = [{"id": f"c-{a}", "agent": a, "fixture": "none", "prompt": "Do the task.",
              "acceptance_criteria": ["First check", "Second check"],
              "proxy_status": "not run", "agents_tab_status": "not run"} for a in sorted(agents)]
    write(root / "evals/cases.json", json.dumps(cases))
    write(root / "evals/README.md", "[cases](cases.json)\n")
    write(root / "README.md", "[agents](.github/agents/)\n")


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_library(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = va.main([str(self.root)])
        return code, out.getvalue()

    def test_valid_library_exits_zero(self):
        code, out = self.run_main()
        self.assertEqual(code, 0, out)

    def test_missing_expected_agent(self):
        (self.root / ".github/agents/code-reviewer.agent.md").unlink()
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("expected agent 'code-reviewer' is missing", out)

    def test_unexpected_agent(self):
        write(self.root / ".github/agents/extra.agent.md",
              profile(name="extra", description="Totally separate omega zeta.",
                      body=GOOD_BODY.replace("None here.", "[p](../../docs/playbooks/planning.md)")))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("not in EXPECTED_AGENTS", out)

    def test_duplicate_agent_names_fail(self):
        shutil.copy(self.root / ".github/agents/code-reviewer.agent.md",
                    self.root / ".github/agents/code-reviewer.md")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("duplicate agent name", out)

    def test_overlapping_descriptions_fail(self):
        for agent in ("code-reviewer", "security-reviewer"):
            p = self.root / f".github/agents/{agent}.agent.md"
            write(p, profile(name=agent, description="Reviews code for bugs and quality issues.",
                             body=GOOD_BODY.replace("None here.", "[p](../../docs/playbooks/planning.md)")))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("overlap", out)

    def test_unreferenced_playbook_fails(self):
        write(self.root / "docs/playbooks/orphan.md", "# Orphan\n")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("orphan.md is not referenced", out)

    def test_case_with_expected_answers_fails(self):
        cases = json.loads((self.root / "evals/cases.json").read_text(encoding="utf-8"))
        cases[0]["expected_findings"] = ["secret"]
        write(self.root / "evals/cases.json", json.dumps(cases))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("expected answers must not be stored", out)

    def test_agent_without_case_fails(self):
        cases = json.loads((self.root / "evals/cases.json").read_text(encoding="utf-8"))
        write(self.root / "evals/cases.json", json.dumps(cases[1:]))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("no evaluation case for agent", out)

    def test_case_needs_two_criteria(self):
        cases = json.loads((self.root / "evals/cases.json").read_text(encoding="utf-8"))
        cases[0]["acceptance_criteria"] = ["only one"]
        write(self.root / "evals/cases.json", json.dumps(cases))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("at least 2", out)

    def test_broken_doc_link_fails(self):
        write(self.root / "README.md", "[a](missing.md) [b](https://x.test/y)\n")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("missing.md", out)
        self.assertNotIn("x.test", out)

    def test_no_profiles_fails(self):
        shutil.rmtree(self.root / ".github")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("no profiles found", out)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_library(self.root, agents={"code-reviewer"})
        self.profile = self.root / ".github/agents/code-reviewer.agent.md"

    def tearDown(self):
        self._tmp.cleanup()

    def sync(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.main([str(self.root), *args])

    def test_check_passes_when_in_sync(self):
        self.assertEqual(self.sync("--check"), 0)

    def test_check_detects_drift_without_writing(self):
        write(self.root / "docs/playbooks/shared-rules.md",
              SHARED.replace("Be careful.", "Be very careful.") + "\n")
        before = self.profile.read_text(encoding="utf-8")
        self.assertEqual(self.sync("--check"), 1)
        self.assertEqual(self.profile.read_text(encoding="utf-8"), before)

    def test_sync_rewrites_block(self):
        write(self.root / "docs/playbooks/shared-rules.md",
              SHARED.replace("Be careful.", "Be very careful.") + "\n")
        self.assertEqual(self.sync(), 0)
        self.assertIn("Be very careful.", self.profile.read_text(encoding="utf-8"))
        self.assertEqual(self.sync("--check"), 0)

    def test_sync_appends_missing_block(self):
        text = self.profile.read_text(encoding="utf-8").replace(SHARED, "")
        write(self.profile, text)
        self.assertEqual(self.sync(), 0)
        self.assertEqual(sync.extract_block(self.profile.read_text(encoding="utf-8")), SHARED)

    def test_malformed_source_fails(self):
        write(self.root / "docs/playbooks/shared-rules.md", "no markers\n")
        self.assertEqual(self.sync(), 1)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class AuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git = ["git", "-C", str(self.repo)]
        subprocess.run(git + ["init", "-q"], check=True)
        write(self.repo / "app.py", "x = 1\n")
        write(self.repo / "README.md", "# r\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                              "commit", "-q", "-m", "init"], check=True)

    def tearDown(self):
        self._tmp.cleanup()

    def audit(self, agent):
        with contextlib.redirect_stdout(io.StringIO()):
            return audit_run.main([str(self.repo), agent])

    def test_clean_worktree_passes_for_read_only_agent(self):
        self.assertEqual(self.audit("code-reviewer"), 0)

    def test_read_only_agent_change_fails(self):
        write(self.repo / "app.py", "x = 2\n")
        self.assertEqual(self.audit("security-reviewer"), 1)

    def test_docs_agent_may_change_markdown_only(self):
        write(self.repo / "README.md", "# changed\n")
        self.assertEqual(self.audit("documentation-engineer"), 0)
        write(self.repo / "app.py", "x = 3\n")
        self.assertEqual(self.audit("documentation-engineer"), 1)

    def test_test_engineer_may_add_tests_only(self):
        write(self.repo / "tests/test_app.py", "pass\n")
        self.assertEqual(self.audit("test-engineer"), 0)
        write(self.repo / "app.py", "x = 4\n")
        self.assertEqual(self.audit("test-engineer"), 1)

    def test_unknown_agent_fails(self):
        self.assertEqual(self.audit("nobody"), 1)

    def test_test_path_patterns(self):
        for path in ("tests/test_x.py", "src/foo_test.go", "web/a.spec.ts", "test_y.py"):
            with self.subTest(path=path):
                self.assertEqual(audit_run.violations("test-engineer", [path]), [])
        self.assertNotEqual(audit_run.violations("test-engineer", ["src/app.py"]), [])


if __name__ == "__main__":
    unittest.main()
