import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "rr-loop", "scripts"))
import rr  # noqa: E402

SHA = "a" * 40


def run(*argv, stdin=""):
    """Возвращает (код, разобранный stdout либо текст stderr)."""
    out, err, old_stdin = io.StringIO(), io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(stdin)
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rr.main(list(argv))
    except SystemExit as exit_:
        code = exit_.code
    finally:
        sys.stdin = old_stdin
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else err.getvalue().strip())


class RrTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.realpath(self.tmp.name)
        self.git("init", "-q")
        self.commit("a.txt", "one")
        self.ledger = os.path.join(self.repo, ".scratch", "rr-loop", "task-1")
        code, result = run("init", "--ledger", self.ledger, "task=T-1")
        self.assertEqual(code, 0, result)
        self.base = result["base"]

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", self.repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, name, text):
        path = os.path.join(self.repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", name)
        return self.git("rev-parse", "HEAD")

    def state(self):
        with open(os.path.join(self.ledger, "state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def handoff(self, role, name, data):
        return run("handoff", "--ledger", self.ledger, "--role", role, "--name", name, stdin=json.dumps(data))

    def review(self, name, data, *extra, role="spec-reviewer"):
        code, result = self.handoff(role, name, data)
        self.assertEqual(code, 0, result)
        return run("review", "--ledger", self.ledger, "--handoff", name, *extra)

    def finding(self, kind="wrong", location="src/A.kt:10", **extra):
        return dict({"type": kind, "location": location, "requirement_ref": "#1", "evidence": "e", "fix": "f"}, **extra)

    def test_init_creates_unverified_state_and_ignores_scratch(self):
        state = self.state()
        self.assertEqual((state["status"], state["quality"], state["task"]), ("RUNNING", "UNVERIFIED", "T-1"))
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_init_refuses_existing_ledger(self):
        code, error = run("init", "--ledger", self.ledger)
        self.assertEqual(code, 1)
        self.assertIn("уже существует", error)

    def test_ledger_must_be_run_directory_under_scratch(self):
        for path in (self.repo, os.path.join(self.repo, ".scratch"), os.path.join(self.repo, ".scratch", "rr-loop")):
            code, _ = run("get", "--ledger", path)
            self.assertEqual(code, 1, path)

    def test_set_get_and_delete_nested_fields(self):
        run("set", "--ledger", self.ledger, "counters.consecutive_red=2", "current_phase=Review")
        _, result = run("get", "--ledger", self.ledger, "counters.consecutive_red", "current_phase", "absent")
        self.assertEqual(result, {"counters.consecutive_red": 2, "current_phase": "Review", "absent": None})
        run("set", "--ledger", self.ledger, "--delete", "counters.consecutive_red")
        self.assertEqual(self.state()["counters"], {})

    def test_get_without_paths_prints_summary_not_content(self):
        _, result = run("get", "--ledger", self.ledger)
        self.assertEqual(result["findings"], 0)

    def test_handoff_extracts_json_from_surrounding_text(self):
        data = {"head": SHA, "checks": [{"cmd": "t", "result": "ok"}], "affected_review_axes": ["Spec"]}
        code, result = run("handoff", "--ledger", self.ledger, "--role", "implementer", "--name", "impl",
                           stdin="Готово.\n" + json.dumps(data) + "\n")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["head"], result["checks"]), (SHA, 1))
        self.assertTrue(os.path.exists(result["ref"]))

    def test_handoff_rejects_missing_field_and_bad_verdict(self):
        code, error = self.handoff("implementer", "impl", {"head": SHA, "checks": []})
        self.assertEqual(code, 1)
        self.assertIn("affected_review_axes", error)
        code, error = self.handoff("spec-reviewer", "spec", {"head": SHA, "verdict": "OPEN"})
        self.assertEqual(code, 1)
        self.assertIn("verdict", error)

    def test_handoff_rejects_inconsistent_verdicts(self):
        code, _ = self.handoff("spec-reviewer", "spec", {"head": SHA, "verdict": "APPROVE",
                                                         "findings": [self.finding()]})
        self.assertEqual(code, 1)
        plan = {"checks": [{"cmd": "t", "result": "fail"}]}
        code, _ = self.handoff("verifier", "gate", {"head": SHA, "verdict": "RED", "validation_plan": plan})
        self.assertEqual(code, 1)
        code, _ = self.handoff("verifier", "gate", {"head": SHA, "verdict": "GREEN", "validation_plan": plan})
        self.assertEqual(code, 0)

    def test_review_assigns_ids_and_maps_severity(self):
        code, result = self.review("spec-1", {"head": SHA, "verdict": "FINDINGS", "findings": [
            self.finding("wrong"),
            self.finding("partial", "docs/a.md:3; docs/b.md"),
            self.finding("partial", scope="outside"),
            self.finding("wrong", scope="outside"),
        ]})
        self.assertEqual(code, 0, result)
        self.assertEqual([(n["id"], n["severity"]) for n in result["new"]],
                         [("F1", "BLOCKER"), ("F2", "MAJOR"), ("F3", "MINOR"), ("F4", "BLOCKER")])
        self.assertEqual([n.get("docs_only", False) for n in result["new"]], [False, True, False, False])
        self.assertEqual(result["critical"], ["F1", "F2", "F4"])
        self.assertEqual(self.state()["axes"]["spec"]["last_reviewed_head"], SHA)

    def test_review_dispositions_close_record_repaired_and_count_no_progress(self):
        self.review("spec-1", {"head": SHA, "verdict": "FINDINGS",
                               "findings": [self.finding(), self.finding(location="src/B.kt:5")]})
        head = "b" * 40
        code, result = self.review("spec-2", {"head": head, "verdict": "FINDINGS", "dispositions": [
            {"id": "F1", "state": "FIXED", "evidence": "e"}, {"id": "F2", "state": "OPEN", "evidence": "e"}]},
            "--ids", "F1,F2", "--full-spec")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["fixed"], result["open"], result["critical"]), (["F1"], ["F2"], ["F2"]))
        state = self.state()
        self.assertEqual(state["repaired"], {"src/A.kt": [{"id": "F1", "fix": "f"}]})
        self.assertEqual(state["findings"]["F2"]["no_progress"], 1)
        self.assertEqual(state["axes"]["spec"], {"last_reviewed_head": head, "full_spec_reviewed_head": head})

    def test_review_without_requested_disposition_changes_nothing(self):
        self.review("spec-1", {"head": SHA, "verdict": "FINDINGS", "findings": [self.finding()]})
        before = self.state()
        code, error = self.review("spec-2", {"head": "b" * 40, "verdict": "APPROVE"}, "--ids", "F1")
        self.assertEqual(code, 1)
        self.assertIn("HUMAN_ATTENTION", error)
        self.assertEqual(self.state(), before)

    def test_review_blocked_context_does_not_advance_coverage(self):
        code, error = self.review("spec-1", {"head": SHA, "verdict": "BLOCKED_CONTEXT", "blocker": "spec changed"})
        self.assertEqual(code, 1)
        self.assertEqual(self.state()["axes"], {})

    def test_standards_review_uses_own_axis(self):
        _, result = self.review("std-1", {"head": SHA, "verdict": "FINDINGS", "findings": [
            {"type": "judgement", "location": "src/A.kt:1", "standard_ref": "AGENTS.md:rule", "evidence": "e",
             "fix": "f"}]}, role="standards-reviewer")
        self.assertEqual((result["axis"], result["new"][0]["severity"], result["critical"]), ("standards", "MINOR", []))

    def test_finding_severity_close_and_list(self):
        self.review("spec-1", {"head": SHA, "verdict": "FINDINGS",
                               "findings": [self.finding("partial", "docs/a.md"), self.finding()]})
        run("finding", "--ledger", self.ledger, "severity", "F1", "MINOR")
        code, _ = run("finding", "--ledger", self.ledger, "close", "F2")
        self.assertEqual(code, 1)
        run("finding", "--ledger", self.ledger, "close", "F2", "WONT_FIX: решение человека")
        _, listed = run("finding", "--ledger", self.ledger, "list")
        self.assertEqual(listed, [{"id": "F1", "axis": "spec", "severity": "MINOR", "location": "docs/a.md"}])
        self.assertEqual(self.state()["human_dispositions"][0]["id"], "F2")

    def test_verify_accepts_clean_new_commit_in_scope(self):
        head = self.commit("src/b.txt", "two")
        code, result = run("verify", "--cwd", self.repo, "--head", head, "--base", self.base, "--new-commit",
                           "--scope", "src")
        self.assertEqual((code, result["ok"], result["changed"]), (0, True, 1))

    def test_verify_reports_every_problem(self):
        head = self.commit("other/c.txt", "three")
        with open(os.path.join(self.repo, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("dirty")
        code, result = run("verify", "--cwd", self.repo, "--head", self.base, "--base", head, "--new-commit",
                           "--scope", "src/*")
        self.assertEqual(code, 1)
        self.assertEqual(len(result["problems"]), 3, result)
        code, result = run("verify", "--cwd", self.repo, "--head", head, "--base", self.base, "--scope", "src/*")
        self.assertEqual(result["outside_scope"], ["other/c.txt"])

    def test_cleanup_only_after_completed(self):
        code, _ = run("cleanup", "--ledger", self.ledger)
        self.assertEqual(code, 1)
        self.assertTrue(os.path.exists(self.ledger))
        run("set", "--ledger", self.ledger, "status=COMPLETED")
        code, _ = run("cleanup", "--ledger", self.ledger)
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(self.ledger))
        self.assertTrue(os.path.isdir(os.path.dirname(self.ledger)))


if __name__ == "__main__":
    unittest.main()
