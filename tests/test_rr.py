import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "spec-delivery", "scripts")
sys.path.insert(0, SCRIPTS)
import rr  # noqa: E402

RR_PY = os.path.join(SCRIPTS, "rr.py")


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
        self.repo = os.path.join(os.path.realpath(self.tmp.name), "repo")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@t")
        self.commit("a.txt", "one")
        self.ledger = os.path.join(self.repo, ".scratch", "spec-delivery", "task-1")
        code, result = run("init", "--ledger", self.ledger, "task=T-1")
        self.assertEqual(code, 0, result)
        self.base = result["base"]

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", cwd or self.repo, *args], check=True, capture_output=True,
                              text=True).stdout.strip()

    def commit(self, name, text, cwd=None):
        path = os.path.join(cwd or self.repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.git("add", "-A", cwd=cwd)
        self.git("commit", "-q", "-m", name, cwd=cwd)
        return self.git("rev-parse", "HEAD", cwd=cwd)

    def rr(self, command, *argv, stdin=""):
        return run(command, "--ledger", self.ledger, *argv, stdin=stdin)

    def state(self):
        with open(os.path.join(self.ledger, "state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def quality(self):
        return self.rr("get", "quality")[1]["quality"]

    def worker(self, head, *extra, role="implementer", **fields):
        data = dict({"head": head, "checks": [{"cmd": "t", "result": "ok"}]}, **fields)
        return self.rr("handoff", "--role", role, *extra, stdin=json.dumps(data))

    def review(self, data, *extra, role="spec-reviewer"):
        return self.rr("review", "--role", role, *extra, stdin=json.dumps(data))

    def gate(self, data, *extra):
        return self.rr("gate", *extra, stdin=json.dumps(data))

    def finding(self, kind="wrong", location="src/A.kt:10", **extra):
        return dict({"type": kind, "location": location, "requirement_ref": "#1", "evidence": "e", "fix": "f"}, **extra)

    def standard(self, kind="hard", location="src/B.kt:1"):
        return {"type": kind, "location": location, "standard_ref": "AGENTS.md:rule", "evidence": "e", "fix": "f"}

    def approve_all(self, head):
        for role in ("spec-reviewer", "standards-reviewer"):
            code, result = self.review({"head": head, "verdict": "APPROVE"}, role=role)
            self.assertEqual(code, 0, result)

    # init

    def test_init_creates_running_unverified_state_and_ignores_scratch(self):
        state = self.state()
        self.assertEqual((state["workflow"], state["status"], state["task"], state["base"], state["head"]),
                         ("spec-delivery", "RUNNING", "T-1", self.base, self.base))
        self.assertNotIn("quality", state)
        self.assertEqual(self.quality(), "UNVERIFIED")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_init_refuses_existing_ledger(self):
        code, error = run("init", "--ledger", self.ledger)
        self.assertEqual(code, 1)
        self.assertIn("уже существует", error)

    def test_ledger_must_be_run_directory_under_scratch(self):
        for path in (self.repo, os.path.join(self.repo, ".scratch"), os.path.join(self.repo, ".scratch", "spec-delivery")):
            code, _ = run("get", "--ledger", path)
            self.assertEqual(code, 1, path)

    def test_init_explains_run_name_for_branch_with_slash(self):
        code, error = run("init", "--ledger", os.path.join(self.repo, ".scratch", "spec-delivery", "feature", "T-2"))
        self.assertEqual(code, 1)
        self.assertIn("замени", error)

    def test_init_keeps_exclude_line_separate_without_trailing_newline(self):
        other = os.path.join(os.path.dirname(self.repo), "other")
        os.makedirs(other)
        self.git("init", "-q", cwd=other)
        self.git("config", "user.name", "t", cwd=other)
        self.git("config", "user.email", "t@t", cwd=other)
        self.commit("a.txt", "one", cwd=other)
        with open(os.path.join(other, ".git", "info", "exclude"), "w", newline="") as fh:
            fh.write("*.tmp")
        code, result = run("init", "--ledger", os.path.join(other, ".scratch", "spec-delivery", "t"))
        self.assertEqual(code, 0, result)
        self.assertEqual(self.git("status", "--porcelain", cwd=other), "")

    def test_init_records_merge_target_and_default_consent(self):
        ledger = os.path.join(self.repo, ".scratch", "spec-delivery", "task-2")
        code, result = run("init", "--ledger", ledger, "--target", "develop", "task=T-2", "consent.merge=false")
        self.assertEqual(code, 0, result)
        with open(os.path.join(ledger, "state.json"), encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["merge_target"], "develop")
        self.assertEqual(state["consent"], {"merge": False, "tracker": True, "worktrees": True})

    def test_init_refuses_live_run_of_same_task_in_another_worktree_across_legacy_workflow(self):
        tree = os.path.join(os.path.dirname(self.repo), "tree")
        self.git("worktree", "add", "-q", "-b", "other", tree, "HEAD")
        ledger = os.path.join(tree, ".scratch", "rr-loop", "other")
        code, error = run("init", "--ledger", ledger, "task=T-1")
        self.assertEqual(code, 1)
        self.assertIn(os.path.join("spec-delivery", "task-1"), error)
        code, result = run("init", "--ledger", ledger, "task=T-9")
        self.assertEqual(code, 0, result)

    # get / set

    def test_set_get_and_delete_nested_fields(self):
        self.rr("set", "counters.retries=2", "current_phase=Review")
        _, result = self.rr("get", "counters.retries", "current_phase", "absent")
        self.assertEqual(result, {"counters.retries": 2, "current_phase": "Review", "absent": None})
        self.rr("set", "--delete", "counters.retries")
        self.assertEqual(self.state()["counters"], {})

    def test_get_without_paths_prints_summary_not_content(self):
        _, result = self.rr("get")
        self.assertEqual((result["findings"], result["quality"]), (0, "UNVERIFIED"))

    def test_set_keeps_sha_like_and_number_like_text(self):
        values = {"a": "12e4567", "b": "0e12345", "c": "1234567", "d": "1.10", "n": "2", "t": "true",
                  "o": '{"k":[1]}', "s": '"7"'}
        self.rr("set", *(f"v.{key}={value}" for key, value in values.items()))
        self.assertEqual(self.state()["v"], {"a": "12e4567", "b": "0e12345", "c": "1234567", "d": "1.10", "n": 2,
                                              "t": True, "o": {"k": [1]}, "s": "7"})

    def test_set_validates_status_and_refuses_quality(self):
        code, error = self.rr("set", "status=DONE")
        self.assertEqual(code, 1)
        self.assertIn("status", error)
        code, error = self.rr("set", "quality=GREEN")
        self.assertEqual(code, 1)
        code, error = self.rr("set", "status=COMPLETED")
        self.assertEqual(code, 1)
        self.assertIn("GREEN", error)
        self.assertEqual(self.state()["status"], "RUNNING")
        code, _ = self.rr("set", "status=WAITING_FOR_HUMAN", "pending_action=target")
        self.assertEqual(code, 0)

    def test_set_head_resolves_revision(self):
        head = self.commit("b.txt", "two")
        code, _ = self.rr("set", f"head={head[:8]}")
        self.assertEqual(code, 0)
        self.assertEqual(self.state()["head"], head)
        code, _ = self.rr("set", "head=1234567")
        self.assertEqual(code, 1)

    def test_set_survives_reader_holding_state(self):
        fh = open(os.path.join(self.ledger, "state.json"), encoding="utf-8")
        threading.Timer(0.3, fh.close).start()
        code, result = self.rr("set", "x=1")
        self.assertEqual(code, 0, result)
        self.assertEqual([name for name in os.listdir(self.ledger) if name.endswith(".tmp")], [])

    # handoff: implementer / reviser / scout

    def test_handoff_extracts_json_from_text_with_braces(self):
        head = self.commit("src/b.txt", "two")
        data = {"head": head, "checks": [{"cmd": "t", "result": "ok"}]}
        code, result = self.rr("handoff", "--role", "implementer",
                               stdin="Итог {см. ниже}:\n" + json.dumps(data) + "\nПримечание: {scope}\n")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["head"], result["checks"], result["changed"]), (head, 1, 1))
        self.assertEqual(os.listdir(os.path.join(self.ledger, "handoffs")), ["implementer-1.json"])
        self.assertEqual(self.state()["head"], head)

    def test_handoff_rejects_missing_field(self):
        head = self.commit("b.txt", "two")
        code, error = self.rr("handoff", "--role", "implementer", stdin=json.dumps({"head": head}))
        self.assertEqual(code, 1)
        self.assertIn("checks", error)
        self.assertEqual(self.state()["head"], self.base)

    def test_handoff_requires_new_clean_commit(self):
        code, result = self.worker(self.base)
        self.assertEqual(code, 1)
        self.assertIn("нет нового commit", result["problems"])
        head = self.commit("b.txt", "two")
        with open(os.path.join(self.repo, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("dirty")
        code, result = self.worker(head)
        self.assertEqual(code, 1)
        self.assertEqual(self.state()["head"], self.base)
        self.assertFalse(os.path.exists(os.path.join(self.ledger, "handoffs")))

    def test_handoff_with_blocker_allows_unfinished_work(self):
        with open(os.path.join(self.repo, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("unfinished")
        code, result = self.worker(self.base, blocker={"reason": "scope", "paths": ["lib/x"]})
        self.assertEqual(code, 0, result)
        self.assertEqual(result["blocker"]["reason"], "scope")
        self.assertEqual(self.state()["head"], self.base)

    def test_handoff_retry_with_same_json_changes_nothing(self):
        head = self.commit("b.txt", "two")
        code, first = self.worker(head)
        self.assertEqual(code, 0, first)
        before = self.state()
        code, second = self.worker(head)
        self.assertEqual((code, second), (0, first))
        self.assertEqual(self.state(), before)

    def test_handoff_collects_standards_union(self):
        head = self.commit("b.txt", "two")
        _, result = self.worker(head, standards_files=["AGENTS.md", "docs/style.md"])
        self.assertEqual(result["standards"], ["AGENTS.md", "docs/style.md"])
        head = self.commit("c.txt", "three")
        _, result = self.worker(head, role="reviser", standards_files=["app/AGENTS.md", "AGENTS.md"])
        self.assertEqual(result["standards"], ["AGENTS.md", "app/AGENTS.md", "docs/style.md"])

    def test_handoff_counts_repair_iterations_and_flags_rejected_critical(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [
            self.finding(), self.finding("partial", scope="outside")]})
        head = self.commit("b.txt", "two")
        code, result = self.worker(head, "--ids", "F1,F2", role="reviser",
                                   rejected=[{"id": "F1", "evidence": "противоречит #2"}])
        self.assertEqual(code, 0, result)
        self.assertEqual((result["rejected"], result["stop"]), (["F1"], "critical_rejected"))
        state = self.state()
        self.assertEqual(state["counters"]["critical_iterations"], 1)
        self.assertEqual(state["findings"]["F1"]["rejected"], "противоречит #2")
        head = self.commit("c.txt", "three")
        self.worker(head, "--ids", "F2", role="reviser")
        self.assertEqual(self.state()["counters"], {"critical_iterations": 1, "minor_iterations": 1})

    def test_handoff_for_task_checks_worktree_base_and_scope(self):
        tree = os.path.join(os.path.dirname(self.repo), "t1")
        self.git("worktree", "add", "-q", "-b", "t1", tree, self.base)
        task = {"deps": [], "write_scope": ["src"], "state": "RUNNING", "cwd": tree, "branch": "t1", "base": self.base}
        self.rr("set", "tasks.T1=" + json.dumps(task))
        outside = self.commit("other/x.txt", "x", cwd=tree)
        code, result = self.worker(outside, "--task", "T1")
        self.assertEqual(code, 1)
        self.assertEqual(result["outside_scope"], ["other/x.txt"])
        self.git("reset", "-q", "--hard", self.base, cwd=tree)
        head = self.commit("src/x.txt", "x", cwd=tree)
        code, result = self.worker(head, "--task", "T1")
        self.assertEqual(code, 0, result)
        state = self.state()
        self.assertEqual((state["tasks"]["T1"]["head"], state["tasks"]["T1"]["state"], state["head"]),
                         (head, "READY_TO_INTEGRATE", self.base))

    def test_handoff_scout_records_notes(self):
        code, result = self.rr("handoff", "--role", "scout", stdin=json.dumps({"notes": ["n/a.md"]}))
        self.assertEqual(code, 0, result)
        self.assertEqual((result["notes"], self.state()["notes"]), (["n/a.md"], ["n/a.md"]))

    # review

    def test_review_rejects_bad_and_inconsistent_verdicts(self):
        code, error = self.review({"head": self.base, "verdict": "OPEN"})
        self.assertEqual(code, 1)
        self.assertIn("verdict", error)
        code, _ = self.review({"head": self.base, "verdict": "APPROVE", "findings": [self.finding()]})
        self.assertEqual(code, 1)
        self.assertEqual(self.state()["axes"], {})

    def test_review_assigns_ids_and_maps_severity(self):
        code, result = self.review({"head": self.base, "verdict": "FINDINGS", "findings": [
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
        state = self.state()
        self.assertEqual(state["axes"]["spec"]["last_reviewed_head"], self.base)
        self.assertNotIn("head", state["findings"]["F1"])

    def test_review_dispositions_close_record_repaired_and_count_no_progress(self):
        self.review({"head": self.base, "verdict": "FINDINGS",
                     "findings": [self.finding(), self.finding(location="src/B.kt:5")]})
        head = self.commit("b.txt", "two")
        self.worker(head, "--ids", "F1,F2", role="reviser")
        code, result = self.review({"head": head, "verdict": "FINDINGS", "dispositions": [
            {"id": "F1", "state": "FIXED", "evidence": "e"}, {"id": "F2", "state": "OPEN", "evidence": "e"}]},
            "--ids", "F1,F2", "--full-spec")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["fixed"], result["open"], result["critical"]), (["F1"], ["F2"], ["F2"]))
        state = self.state()
        self.assertEqual(state["repaired"], {"src/A.kt": [{"id": "F1", "fix": "f"}]})
        self.assertEqual(state["findings"]["F2"]["no_progress"], 1)
        spec = state["axes"]["spec"]
        self.assertEqual((spec["last_reviewed_head"], spec["full_spec_reviewed_head"]), (head, head))

    def test_review_without_requested_disposition_changes_nothing(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [self.finding()]})
        before = self.state()
        code, error = self.review({"head": self.base, "verdict": "APPROVE"}, "--ids", "F1")
        self.assertEqual(code, 1)
        self.assertIn("HUMAN_ATTENTION", error)
        self.assertEqual(self.state(), before)

    def test_review_blocked_context_does_not_advance_coverage(self):
        code, result = self.review({"head": self.base, "verdict": "BLOCKED_CONTEXT", "blocker": "spec недоступна"})
        self.assertEqual(code, 1)
        self.assertEqual(result["stop"], "blocked_context")
        self.assertEqual(self.state()["axes"], {})

    def test_review_rejects_foreign_head(self):
        head = self.commit("b.txt", "two")
        code, error = self.review({"head": head, "verdict": "APPROVE"})
        self.assertEqual(code, 1)
        self.assertIn("HUMAN_ATTENTION", error)
        self.assertEqual(self.state()["axes"], {})

    def test_review_rejects_ids_of_another_axis(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [self.finding()]})
        code, error = self.review({"head": self.base, "verdict": "APPROVE",
                                   "dispositions": [{"id": "F1", "state": "FIXED", "evidence": "e"}]},
                                  "--ids", "F1", role="standards-reviewer")
        self.assertEqual(code, 1)
        self.assertIn("F1", error)
        self.assertIn("F1", self.state()["findings"])

    def test_review_retry_with_same_json_changes_nothing(self):
        data = {"head": self.base, "verdict": "FINDINGS", "findings": [self.finding()]}
        _, first = self.review(data)
        _, second = self.review(data)
        self.assertEqual(second, first)
        self.assertEqual(sorted(self.state()["findings"]), ["F1"])
        delta = {"head": self.base, "verdict": "FINDINGS",
                 "dispositions": [{"id": "F1", "state": "OPEN", "evidence": "e"}]}
        self.review(delta, "--ids", "F1")
        self.review(delta, "--ids", "F1")
        self.assertEqual(self.state()["findings"]["F1"]["no_progress"], 1)

    def test_review_standards_uses_own_axis(self):
        _, result = self.review({"head": self.base, "verdict": "FINDINGS", "findings": [self.standard("judgement")]},
                                role="standards-reviewer")
        self.assertEqual((result["axis"], result["new"][0]["severity"], result["critical"]), ("standards", "MINOR", []))

    def test_review_flags_no_progress_and_iteration_limits(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [self.finding()]})
        head = self.base
        for round_ in range(2):
            head = self.commit(f"r{round_}.txt", "x")
            self.worker(head, "--ids", "F1", role="reviser")
            _, result = self.review({"head": head, "verdict": "FINDINGS", "dispositions": [
                {"id": "F1", "state": "OPEN", "evidence": f"e{round_}"}]}, "--ids", "F1")
        self.assertEqual(result["stop"], "no_progress")
        self.rr("set", "counters.critical_iterations=4", "findings.F1.no_progress=0")
        head = self.commit("r9.txt", "x")
        self.worker(head, role="reviser")
        _, result = self.review({"head": head, "verdict": "FINDINGS", "dispositions": [
            {"id": "F1", "state": "OPEN", "evidence": "e9"}]}, "--ids", "F1")
        self.assertEqual(result["stop"], "critical_limit")

    def test_review_reports_minor_limit(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [self.standard("judgement")]},
                    role="standards-reviewer")
        self.rr("set", "counters.minor_iterations=2")
        head = self.commit("b.txt", "two")
        self.worker(head, role="reviser")
        _, result = self.review({"head": head, "verdict": "FINDINGS", "dispositions": [
            {"id": "F1", "state": "OPEN", "evidence": "e"}]}, "--ids", "F1", role="standards-reviewer")
        self.assertTrue(result["minor_limit"])
        self.assertNotIn("stop", result)

    def test_review_skip_marks_axis_covered_for_current_head_only(self):
        code, result = self.rr("review", "--axis", "standards", "--skip", "правил нет")
        self.assertEqual(code, 0, result)
        self.review({"head": self.base, "verdict": "APPROVE"})
        self.rr("gate", "--not-applicable", "только неисполняемый текст")
        self.assertEqual(self.quality(), "GREEN")
        head = self.commit("b.txt", "two")
        self.worker(head)
        self.assertEqual(self.quality(), "UNVERIFIED")

    def test_concurrent_reviews_keep_both_axes(self):
        spec = {"head": self.base, "verdict": "FINDINGS", "findings": [self.finding()]}
        standards = {"head": self.base, "verdict": "FINDINGS", "findings": [self.standard()]}
        procs = [subprocess.Popen([sys.executable, RR_PY, "review", "--ledger", self.ledger, "--role", role],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8")
                 for role in ("spec-reviewer", "standards-reviewer")]
        threads = [threading.Thread(target=proc.communicate, args=(json.dumps(data),))
                   for proc, data in zip(procs, (spec, standards))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([proc.returncode for proc in procs], [0, 0])
        state = self.state()
        self.assertEqual((sorted(state["findings"]), sorted(state["axes"])), (["F1", "F2"], ["spec", "standards"]))

    # gate / quality

    def test_gate_rejects_inconsistent_verdicts(self):
        checks = [{"cmd": "t", "result": "fail"}]
        code, _ = self.gate({"head": self.base, "verdict": "RED", "checks": checks})
        self.assertEqual(code, 1)
        code, _ = self.gate({"head": self.base, "verdict": "GREEN", "checks": checks,
                             "failures": [{"location": "t", "evidence": "e"}]})
        self.assertEqual(code, 1)
        self.assertNotIn("gate", self.state())

    def test_gate_green_gives_quality_only_for_covered_current_head(self):
        head = self.commit("b.txt", "two")
        self.worker(head)
        code, result = self.gate({"head": head, "verdict": "GREEN", "checks": [{"cmd": "t", "result": "ok"}]})
        self.assertEqual((code, result["verdict"], result["quality"]), (0, "GREEN", "UNVERIFIED"))
        self.assertTrue(os.path.exists(result["ref"]))
        self.approve_all(head)
        self.assertEqual(self.quality(), "GREEN")
        head2 = self.commit("c.txt", "three")
        self.rr("set", f"head={head2}")
        self.assertEqual(self.quality(), "UNVERIFIED")
        self.assertEqual(self.state()["green"]["head"], head)

    def test_gate_rejects_foreign_head(self):
        head = self.commit("b.txt", "two")
        code, error = self.gate({"head": head, "verdict": "GREEN", "checks": []})
        self.assertEqual(code, 1)
        self.assertIn("HUMAN_ATTENTION", error)

    def test_gate_counts_consecutive_red_and_retry_is_idempotent(self):
        def red(n):
            return {"head": self.base, "verdict": "RED", "checks": [{"cmd": "t", "result": f"fail {n}"}],
                    "failures": [{"location": "t", "evidence": f"e{n}"}]}
        _, result = self.gate(red(1))
        self.assertEqual((result["consecutive_red"], result["failures"]), (1, 1))
        _, again = self.gate(red(1))
        self.assertEqual(again, result)
        self.gate(red(2))
        _, result = self.gate(red(3))
        self.assertEqual((result["consecutive_red"], result["stop"]), (3, "red_limit"))
        _, result = self.gate({"head": self.base, "verdict": "GREEN", "checks": []})
        self.assertEqual(result["consecutive_red"], 0)

    def test_gate_reuse_needs_proof_unless_tree_is_same(self):
        self.approve_all(self.base)
        code, _ = self.rr("gate", "--reuse")
        self.assertEqual(code, 1)
        self.gate({"head": self.base, "verdict": "GREEN", "checks": []})
        self.git("commit", "-q", "--allow-empty", "-m", "same tree")
        same = self.git("rev-parse", "HEAD")
        self.rr("set", f"head={same}")
        self.approve_all(same)
        code, result = self.rr("gate", "--reuse")
        self.assertEqual((code, result["quality"]), (0, "GREEN"))
        other = self.commit("docs.md", "text")
        self.rr("set", f"head={other}")
        self.approve_all(other)
        code, _ = self.rr("gate", "--reuse")
        self.assertEqual(code, 1)
        code, result = self.rr("gate", "--reuse", "diff только docs.md, проверки те же")
        self.assertEqual((code, result["quality"]), (0, "GREEN"))
        self.assertEqual(self.state()["green"]["head"], self.base)

    def test_quality_with_tasks_needs_all_reviewed_and_full_spec(self):
        self.rr("set", 'tasks.T1={"state":"INTEGRATED"}')
        self.approve_all(self.base)
        self.gate({"head": self.base, "verdict": "GREEN", "checks": []})
        self.assertEqual(self.quality(), "UNVERIFIED")
        self.rr("set", "tasks.T1.state=REVIEWED")
        self.assertEqual(self.quality(), "UNVERIFIED")
        self.review({"head": self.base, "verdict": "APPROVE", "blocker": "full"}, "--full-spec")
        self.assertEqual(self.quality(), "GREEN")

    # finding

    def test_finding_severity_close_leave_and_list_accept_id_lists(self):
        self.review({"head": self.base, "verdict": "FINDINGS", "findings": [
            self.finding("partial", "docs/a.md"), self.finding("partial", "docs/b.md"), self.finding(),
            self.finding(location="src/C.kt:1")]})
        code, _ = self.rr("finding", "severity", "F1,F2", "MINOR")
        self.assertEqual(code, 0)
        code, _ = self.rr("finding", "close", "F3")
        self.assertEqual(code, 1)
        code, _ = self.rr("finding", "leave", "F1,F4")
        self.assertEqual(code, 1)
        self.rr("finding", "leave", "F1")
        self.rr("finding", "close", "F3,F4", "WONT_FIX: решение человека")
        _, listed = self.rr("finding", "list")
        self.assertEqual(listed, [{"id": "F2", "axis": "spec", "severity": "MINOR", "location": "docs/b.md"}])
        state = self.state()
        self.assertEqual([entry["id"] for entry in state["human_dispositions"]], ["F3", "F4"])
        self.assertEqual(state["left"], [{"id": "F1", "axis": "spec", "location": "docs/a.md", "fix": "f"}])

    # verify

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

    # integrate

    def parallel(self):
        """Integration worktree и две задачи: T2 зависит от T1."""
        integration = os.path.join(os.path.dirname(self.repo), "integration")
        self.git("worktree", "add", "-q", "-b", "integration", integration, self.base)
        tasks = {name: {"deps": deps, "write_scope": [name.lower()], "state": "PENDING"}
                 for name, deps in (("T1", []), ("T2", ["T1"]))}
        self.rr("set", "integration=" + json.dumps({"cwd": integration, "branch": "integration"}),
                "tasks=" + json.dumps(tasks))
        return integration

    def start_task(self, name, base):
        tree = os.path.join(os.path.dirname(self.repo), name.lower())
        self.git("worktree", "add", "-q", "-b", name.lower(), tree, base)
        self.rr("set", f"tasks.{name}.cwd={tree}", f"tasks.{name}.branch={name.lower()}", f"tasks.{name}.base={base}",
                f"tasks.{name}.state=RUNNING")
        return tree

    def test_integrate_merges_ready_task_and_reports_unblocked(self):
        integration = self.parallel()
        tree = self.start_task("T1", self.base)
        head = self.commit("t1/x.txt", "x", cwd=tree)
        code, result = self.rr("integrate", "--task", "T1")
        self.assertEqual(code, 1, result)
        self.worker(head, "--task", "T1")
        code, result = self.rr("integrate", "--task", "T1")
        self.assertEqual(code, 0, result)
        tip = self.git("rev-parse", "HEAD", cwd=integration)
        self.assertEqual((result["head"], result["state"], result["unblocked"]), (tip, "INTEGRATED", ["T2"]))
        state = self.state()
        self.assertEqual((state["head"], state["tasks"]["T1"]["state"]), (tip, "INTEGRATED"))
        self.assertNotIn("integrating", state)
        self.git("merge-base", "--is-ancestor", head, tip, cwd=integration)

    def test_integrate_conflict_aborts_merge_and_keeps_state(self):
        integration = self.parallel()
        tree = self.start_task("T1", self.base)
        head = self.commit("a.txt", "task", cwd=tree)
        self.worker(head, "--task", "T1", "--scope", "a.txt")
        tip = self.commit("a.txt", "integration", cwd=integration)
        self.rr("set", f"head={tip}")
        code, result = self.rr("integrate", "--task", "T1")
        self.assertEqual(code, 1)
        self.assertEqual((result["conflict"], result["files"]), (True, ["a.txt"]))
        self.assertEqual(self.git("status", "--porcelain", cwd=integration), "")
        state = self.state()
        self.assertEqual((state["head"], state["tasks"]["T1"]["state"]), (tip, "READY_TO_INTEGRATE"))
        self.assertNotIn("integrating", state)

    def test_integrate_recovers_finished_merge_without_result(self):
        integration = self.parallel()
        tree = self.start_task("T1", self.base)
        head = self.commit("t1/x.txt", "x", cwd=tree)
        self.worker(head, "--task", "T1")
        other = self.commit("z.txt", "z", cwd=integration)
        self.rr("set", f"head={other}")
        self.git("merge", "-q", "--no-edit", head, cwd=integration)
        merged = self.git("rev-parse", "HEAD", cwd=integration)
        self.rr("set", "integrating=" + json.dumps({"task": "T1", "source": head, "before": other}))
        code, result = self.rr("integrate", "--task", "T1")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["head"], result["state"]), (merged, "INTEGRATED"))
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=integration), merged)

    # cleanup

    def test_cleanup_removes_untouched_run(self):
        code, result = self.rr("cleanup")
        self.assertEqual(code, 0, result)
        self.assertFalse(os.path.exists(self.ledger))

    def test_cleanup_only_after_completed(self):
        self.worker(self.commit("b.txt", "two"))
        code, _ = self.rr("cleanup")
        self.assertEqual(code, 1)
        self.assertTrue(os.path.exists(self.ledger))
        self.rr("set", f"head={self.base}")
        self.git("reset", "-q", "--hard", self.base)
        code, _ = self.rr("cleanup")
        self.assertEqual(code, 1)
        self.approve_all(self.base)
        self.rr("gate", "--not-applicable", "только неисполняемый текст")
        code, result = self.rr("set", "status=COMPLETED")
        self.assertEqual(code, 0, result)
        code, _ = self.rr("cleanup")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(self.ledger))
        self.assertTrue(os.path.isdir(os.path.dirname(self.ledger)))


if __name__ == "__main__":
    unittest.main()
