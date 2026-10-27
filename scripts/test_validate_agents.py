"""Unit tests for validate_agents.py.

Run from the repository root:  python -m unittest discover -s scripts -v
"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_agents as va  # noqa: E402

GOOD_BODY = "Intro.\n\n## Scope\n\nStuff.\n\n## Completion criteria\n\n- Done.\n"


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


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, text, filename="sample.agent.md", raw=None):
        path = self.dir / filename
        if raw is not None:
            path.write_bytes(raw)
        else:
            path.write_text(text, encoding="utf-8", newline="\n")
        return va.validate_profile(path)

    def assertError(self, errors, fragment):
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_valid_profile_passes(self):
        name, errors, warnings = self.check(profile())
        self.assertEqual((name, errors, warnings), ("sample", [], []))

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
        _, errors, _ = self.check(profile(body="Just text.\n"))
        self.assertError(errors, "'## Scope'")
        self.assertError(errors, "'## Completion criteria'")

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


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".github" / "agents").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self):
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ["validate_agents.py", str(self.root)]
        try:
            with contextlib.redirect_stdout(out):
                code = va.main()
        finally:
            sys.argv = argv
        return code, out.getvalue()

    def test_valid_repository_exits_zero(self):
        (self.root / ".github/agents/sample.agent.md").write_text(profile(), encoding="utf-8")
        (self.root / "README.md").write_text("[a](.github/agents/sample.agent.md)", encoding="utf-8")
        code, out = self.run_main()
        self.assertEqual(code, 0, out)

    def test_broken_readme_link_fails(self):
        (self.root / ".github/agents/sample.agent.md").write_text(profile(), encoding="utf-8")
        (self.root / "README.md").write_text("[a](missing.md) [b](https://x.test/y)", encoding="utf-8")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("missing.md", out)
        self.assertNotIn("x.test", out)

    def test_duplicate_agent_names_fail(self):
        (self.root / ".github/agents/one.agent.md").write_text(profile(name="one"), encoding="utf-8")
        (self.root / ".github/agents/one.md").write_text(profile(name="one"), encoding="utf-8")
        (self.root / "README.md").write_text("", encoding="utf-8")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("duplicate agent name", out)

    def test_no_profiles_fails(self):
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("no profiles found", out)


if __name__ == "__main__":
    unittest.main()
