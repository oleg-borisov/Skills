import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "skills/setup-agents/scripts/render.py"


class RenderAgentsTest(unittest.TestCase):
    def run_cli(self, *args, check=True):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(RENDER), *map(str, args)],
            capture_output=True, encoding="utf-8", check=check,
        )

    def render(self, host, *args):
        result = json.loads(self.run_cli("render", host, *args).stdout)
        stage = Path(result["stage"])
        self.addCleanup(shutil.rmtree, stage)
        self.assertEqual(ROOT / ".tmp", stage.parent)
        self.assertEqual(6, len(result["files"]))
        return stage

    def test_codex_renders_thin_profiles_with_tier_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as destination:
            stage = self.render("codex", "--install-dir", destination,
                                "--model", "reviser=custom-model")
            self.assertFalse(list(Path(destination).iterdir()))
        with (stage / "spec-reviewer.toml").open(encoding="utf-8") as profile:
            fields = dict(line.rstrip().split(" = ", 1) for line in profile)
        self.assertEqual("gpt-6.2-sol", json.loads(fields["model"]))
        self.assertEqual("high", json.loads(fields["model_reasoning_effort"]))
        self.assertEqual("read-only", json.loads(fields["sandbox_mode"]))
        instructions = json.loads(fields["developer_instructions"])
        contract = ROOT / "skills/spec-delivery/references/roles/spec-reviewer.md"
        self.assertIn(str(contract), instructions)
        self.assertNotIn("## Output", instructions)
        self.assertIn('model = "custom-model"', (stage / "reviser.toml").read_text("utf-8"))
        self.assertIn('sandbox_mode = "workspace-write"', (stage / "scout.toml").read_text("utf-8"))
        self.assertIn('sandbox_mode = "workspace-write"', (stage / "verifier.toml").read_text("utf-8"))

    def test_existing_models_survive_render_and_role_paths_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "verifier.toml"
            args = ("vibe", "--install-dir", root)
            profile.write_bytes(b'\xef\xbb\xbfactive_model = "existing-model" # old setting\r\n')
            options = json.loads(self.run_cli("options", *args).stdout)
            self.assertIsNone(options["stage"])
            verifier = next(item for item in options["files"] if item["role"] == "verifier")
            self.assertEqual("existing-model", verifier["model"])
            self.assertEqual("existing-model", verifier["installed_model"])
            self.assertEqual("inherit", verifier["recommended_model"])
            stage = self.render(*args, "--spec-delivery",
                                ROOT / "skills/setup-agents/../spec-delivery")
            content = (stage / "verifier.toml").read_bytes()
            self.assertFalse(content.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b'active_model = "existing-model"', content)
            self.assertIn(b'disabled_tools = ["agents_spawn"]', content)
            self.assertIn(b'[tools.write_file]\npermission = "never"', content)
            self.assertIn(b'[tools.edit]\npermission = "never"', content)
            self.assertNotIn(b"setup-agents", content)
            self.assertNotIn(b"[tools.edit]", (stage / "scout.toml").read_bytes())

    def test_markdown_hosts_keep_role_enforcement_and_render_only_to_stage(self):
        expected = {
            "antigravity": ("model: \"flash\"", "  - run_command", "mainAgent: false"),
            "claude": ("model: \"haiku\"", "  - Bash", "effort: medium"),
            "cursor": ('model: "composer-2.5-fast"',),
            "devin": ("allowed-tools:", "  - exec"),
            "opencode": ("mode: subagent", "  edit: deny", "  task: deny"),
            "qoder": ("model: \"efficient\"", "temperature: 0.1", "  - Bash"),
            "zcode": ("tools:", "  - Bash"),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, fields in expected.items():
                with self.subTest(host=host):
                    stage = self.render(host, "--install-dir", root)
                    content = (stage / "verifier.md").read_text("utf-8")
                    self.assertTrue(content.startswith("---\nname: verifier\n"))
                    for field in fields:
                        self.assertIn(field, content)
                    self.assertNotIn("## Output", content)
                    if host == "cursor":
                        self.assertNotIn("readonly:", content)
                        reviewer = (stage / "spec-reviewer.md").read_text("utf-8")
                        self.assertIn("readonly: true", reviewer)
                        self.assertNotIn("model:", reviewer)
                    if host == "qoder":
                        writer = (stage / "implementer.md").read_text("utf-8")
                        self.assertIn("disallowedTools:\n  - Agent", writer)
            self.assertFalse(list(root.iterdir()))

    def test_duplicate_model_override_is_rejected(self):
        result = self.run_cli("render", "codex", "--model", "scout=one",
                              "--model", "scout=two", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("scout=two", result.stderr)
