#!/usr/bin/env python3
"""Механика ledger rr workflows: атомарный state, handoffs, findings, gate, интеграция, сверка Git, cleanup.

Вызывает только primary-controller. Вывод — одна компактная строка JSON; ошибка — строка в stderr и код 1.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

SHA = re.compile(r"^[0-9a-f]{7,64}$")
CHECKS = [{"cmd": str, "result": str}]
WORKER = {"head": "sha", "checks": CHECKS}
REVIEWER = {"head": "sha", "verdict": ("APPROVE", "FINDINGS", "BLOCKED_CONTEXT")}
ROLES = {
    "implementer": WORKER,
    "reviser": WORKER,
    "scout": {"notes": [str]},
    "spec-reviewer": REVIEWER,
    "standards-reviewer": REVIEWER,
    "verifier": {"head": "sha", "verdict": ("GREEN", "RED", "BLOCKED"), "checks": CHECKS},
}
OPTIONAL = {
    "standards_files": [str],
    "rejected": [{"id": str, "evidence": str}],
    "dispositions": [{"id": str, "state": ("FIXED", "OPEN"), "evidence": str}],
    "failures": [{"location": str, "evidence": str}],
}
FINDING = {
    "spec-reviewer": {"type": ("missing", "partial", "wrong"), "location": str, "requirement_ref": str,
                      "evidence": str, "fix": str},
    "standards-reviewer": {"type": ("hard", "judgement"), "location": str, "standard_ref": str,
                           "evidence": str, "fix": str},
}
AXIS = {"spec-reviewer": "spec", "standards-reviewer": "standards"}
SEVERITY = {"wrong": "BLOCKER", "missing": "MAJOR", "partial": "MAJOR", "hard": "MAJOR", "judgement": "MINOR"}
CRITICAL = ("BLOCKER", "MAJOR")
STATUSES = ("RUNNING", "WAITING_FOR_HUMAN", "HUMAN_ATTENTION", "STOPPED_BY_HUMAN", "COMPLETED")
LIMITS = {"critical_iterations": 4, "minor_iterations": 2, "consecutive_red": 3, "no_progress": 2}
DOCS = re.compile(r"\.(md|mdx|txt|rst|adoc|html?)$", re.I)


class Fail(Exception):
    pass


def check(value, schema, where):
    """Проверяет обязательные поля; лишние поля допустимы."""
    if schema == "sha":
        if not isinstance(value, str) or not SHA.match(value):
            raise Fail(f"{where}: нужен SHA")
    elif isinstance(schema, tuple):
        if value not in schema:
            raise Fail(f"{where}: {value!r} не из {'|'.join(schema)}")
    elif isinstance(schema, type):
        if not isinstance(value, schema) or value == "":
            raise Fail(f"{where}: нужен непустой {schema.__name__}")
    elif isinstance(schema, list):
        if not isinstance(value, list):
            raise Fail(f"{where}: нужен список")
        for i, item in enumerate(value):
            check(item, schema[0], f"{where}[{i}]")
    else:
        if not isinstance(value, dict):
            raise Fail(f"{where}: нужен объект")
        for key, sub in schema.items():
            if key not in value:
                raise Fail(f"{where}: нет поля {key}")
            check(value[key], sub, f"{where}.{key}")


def git(cwd, *args, ok=(0,)):
    proc = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode not in ok:
        raise Fail(f"git {' '.join(args)}: {proc.stderr.strip() or proc.returncode}")
    return proc.returncode, proc.stdout.strip()


class Lock:
    """Межпроцессная блокировка: load → save одного вызова не пересекается с другим."""

    def __init__(self, path, timeout=30):
        self.path, self.timeout = path, timeout

    def __enter__(self):
        self.fh = open(self.path, "a+b")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._lock(True)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    self.fh.close()
                    raise Fail(f"занято другим вызовом RR: {self.path}")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            self._lock(False)
        finally:
            self.fh.close()

    def _lock(self, acquire):
        if os.name == "nt":
            import msvcrt
            self.fh.seek(0)
            msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK if acquire else msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB if acquire else fcntl.LOCK_UN)


def ledger_dir(path):
    """LEDGER_DIR = <checkout>/.scratch/<workflow>/<run>, без symlink/junction компонентов."""
    full = os.path.abspath(path)
    parts = full.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[-3] != ".scratch" or not parts[-1] or not parts[-2]:
        raise Fail("ledger должен быть <checkout>/.scratch/<workflow>/<run>, "
                   f"`/` в имени запуска замени на `-`: {full}")
    if os.path.exists(full) and os.path.normcase(os.path.realpath(full)) != os.path.normcase(full):
        raise Fail(f"ledger содержит symlink/junction: {full}")
    return full


def state_path(ledger):
    return os.path.join(ledger, "state.json")


def load(ledger):
    try:
        with open(state_path(ledger), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise Fail(f"нет state.json в {ledger}")
    except ValueError as err:
        raise Fail(f"state.json повреждён: {err}")


def locked(ledger):
    if not os.path.exists(state_path(ledger)):
        raise Fail(f"нет state.json в {ledger}")
    return Lock(os.path.join(ledger, "state.lock"))


def save(ledger, state):
    fd, tmp = tempfile.mkstemp(dir=ledger, prefix="state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        for attempt in range(40):
            try:
                os.replace(tmp, state_path(ledger))
                return
            except PermissionError:  # Windows: state.json открыт читателем
                if attempt == 39:
                    raise
                time.sleep(0.05)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def parse_value(text):
    """JSON только для объектов, списков, строк в кавычках, true/false/null и коротких целых; SHA остаётся текстом."""
    if text[:1] in ("{", "[", '"') or text in ("true", "false", "null") or re.fullmatch(r"-?\d{1,6}", text):
        try:
            return json.loads(text)
        except ValueError:
            pass
    return text


def apply_pairs(state, pairs, cwd):
    for pair in pairs:
        key, sep, text = pair.partition("=")
        if not sep:
            raise Fail(f"нужно path=value: {pair}")
        value = parse_value(text)
        if key == "quality":
            raise Fail("quality вычисляет CLI: RR get quality")
        if key == "status" and value not in STATUSES:
            raise Fail(f"status: {'|'.join(STATUSES)}")
        if key in ("head", "base"):
            code, value = git(cwd, "rev-parse", "--verify", "--quiet", text + "^{commit}", ok=(0, 1, 128))
            if code:
                raise Fail(f"{key}: нет commit {text}")
        node = state
        *parents, leaf = key.split(".")
        for part in parents:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise Fail(f"{key}: {part} не объект")
        node[leaf] = value


def lookup(state, key):
    node = state
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def out(value):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def quality(state):
    """GREEN только для текущего head: gate, обе оси, нет OPEN findings, все задачи плана REVIEWED."""
    head, axes, gate = state.get("head"), state.get("axes", {}), state.get("gate") or {}
    covered = all(axes.get(axis, {}).get("last_reviewed_head") == head
                  or (axes.get(axis, {}).get("skip") or {}).get("head") == head for axis in ("spec", "standards"))
    green = (covered and not state.get("findings") and gate.get("head") == head
             and gate.get("verdict") in ("GREEN", "NOT_APPLICABLE"))
    tasks = state.get("tasks")
    if green and tasks:
        green = (all(task.get("state") == "REVIEWED" for task in tasks.values())
                 and bool(axes.get("spec", {}).get("full_spec_reviewed_head")))
    return "GREEN" if green else "UNVERIFIED"


def checkout(ledger):
    return os.path.dirname(os.path.dirname(os.path.dirname(ledger)))


def run_cwd(state, ledger, override=None):
    return override or (state.get("integration") or {}).get("cwd") or state.get("cwd") or checkout(ledger)


def read_json(a, role):
    """Финальный JSON worker из --file либо stdin; текст вокруг и фигурные скобки в нём допустимы."""
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    decoder, data = json.JSONDecoder(), None
    for match in re.finditer(r"\{", text):
        try:
            data = decoder.raw_decode(text, match.start())[0]
        except ValueError:
            continue
        if isinstance(data, dict) and data:
            break
    if not isinstance(data, dict) or not data:
        raise Fail("handoff не JSON")
    check(data, ROLES[role], role)
    for key, schema in OPTIONAL.items():
        if key in data:
            check(data[key], schema, key)
    if role in FINDING:
        check(data.get("findings", []), [FINDING[role]], "findings")
        has_open = bool(data.get("findings")) or any(d["state"] == "OPEN" for d in data.get("dispositions", []))
        if (data["verdict"] == "FINDINGS") != has_open and data["verdict"] in ("APPROVE", "FINDINGS"):
            raise Fail("verdict FINDINGS должен совпадать с наличием findings/OPEN dispositions")
    if role == "verifier" and (data["verdict"] == "GREEN") == bool(data.get("failures")):
        raise Fail("verifier: failures обязательны при RED/BLOCKED и запрещены при GREEN")
    return data


def applied(ledger, name, role, data, args):
    """Результат уже применённого handoff, если повторный вызов несёт тот же JSON."""
    path = os.path.join(ledger, "handoffs", f"{name}.json")
    if not name or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        old = json.load(fh)
    if {key: value for key, value in old.items() if key not in ("role", "args", "result")} != data:
        return None
    if old.get("role") != role or old.get("args") != args:
        raise Fail(f"handoff {name} уже применён с другими параметрами")
    return old["result"]


def store(ledger, state, role, data, args, result, ref=False):
    """Сохраняет handoff вместе с результатом применения; возвращает имя."""
    name = f"{role}-{state.get('next_handoff_id', 1)}"
    state["next_handoff_id"] = state.get("next_handoff_id", 1) + 1
    path = os.path.join(ledger, "handoffs", name + ".json")
    if ref:
        result["ref"] = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(data, role=role, args=args, result=result), fh, ensure_ascii=False, indent=1)
    return name


def live_runs(root):
    """Незавершённые журналы запусков во всех worktrees репозитория."""
    _, listing = git(root, "worktree", "list", "--porcelain")
    for line in listing.splitlines():
        if not line.startswith("worktree "):
            continue
        for path in glob.glob(os.path.join(glob.escape(line[9:]), ".scratch", "*", "*", "state.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    other = json.load(fh)
            except (OSError, ValueError):
                continue
            if other.get("status") != "COMPLETED":
                yield os.path.dirname(os.path.normpath(path)), other


def cmd_init(a):
    ledger = ledger_dir(a.ledger)
    root = checkout(ledger)
    cwd = a.cwd or root
    _, common = git(root, "rev-parse", "--git-common-dir")
    with Lock(os.path.join(root, common, "rr-init.lock")):
        if os.path.exists(state_path(ledger)):
            status = load(ledger).get("status")
            raise Fail(f"ledger уже существует, status={status}: resume или reset по решению человека")
        _, head = git(cwd, "rev-parse", "HEAD")
        state = {"workflow": os.path.basename(os.path.dirname(ledger)), "status": "RUNNING", "base": head, "head": head,
                 "consent": {"merge": True, "tracker": True, "worktrees": True},
                 "findings": {}, "next_finding_id": 1, "repaired": {}, "axes": {}}
        if a.cwd:
            state["cwd"] = os.path.abspath(a.cwd)
        if a.target:
            state["merge_target"] = a.target
        apply_pairs(state, a.pairs, cwd)
        same = [f"{path} (status {other.get('status')})" for path, other in live_runs(root)
                if any(state.get(key) and state.get(key) == other.get(key) for key in ("task", "spec"))]
        if same:
            raise Fail(f"запуск этой задачи/spec уже идёт: {'; '.join(same)}: resume или reset по решению человека")
        _, exclude = git(root, "rev-parse", "--git-path", "info/exclude")
        exclude = os.path.join(root, exclude)
        text = open(exclude, encoding="utf-8").read() if os.path.exists(exclude) else ""
        if ".scratch/" not in text.splitlines():
            os.makedirs(os.path.dirname(exclude), exist_ok=True)
            with open(exclude, "a", encoding="utf-8") as fh:
                fh.write(("" if not text or text.endswith("\n") else "\n") + ".scratch/\n")
        os.makedirs(ledger, exist_ok=True)
        save(ledger, state)
    out({"ledger": ledger, "base": head})


def cmd_get(a):
    state = load(ledger_dir(a.ledger))
    view = dict(state, quality=quality(state))
    if a.all:
        out(view)
    elif a.paths:
        out({key: lookup(view, key) for key in a.paths})
    else:
        out({key: (len(value) if isinstance(value, (dict, list)) else value) for key, value in view.items()})


def cmd_set(a):
    ledger = ledger_dir(a.ledger)
    with locked(ledger):
        state = load(ledger)
        before = state.get("status")
        apply_pairs(state, a.pairs, run_cwd(state, ledger))
        for key in a.delete:
            *parents, leaf = key.split(".")
            node = lookup(state, ".".join(parents)) if parents else state
            if isinstance(node, dict):
                node.pop(leaf, None)
        if state.get("status") == "COMPLETED" and before != "COMPLETED" and quality(state) != "GREEN":
            raise Fail("COMPLETED только при quality GREEN")
        save(ledger, state)
    out({"ok": True})


def inspect(cwd, head, base=None, new_commit=False, scope=None, dirty_ok=False):
    """Сверка Git metadata handoff: HEAD, чистота, ancestry, изменённые пути против write_scope."""
    problems = []
    _, actual = git(cwd, "rev-parse", "HEAD")
    if not actual.startswith(head):
        problems.append(f"HEAD {actual[:12]} != {head[:12]}")
    _, dirty = git(cwd, "status", "--porcelain")
    if dirty and not dirty_ok:
        problems.append(f"dirty: {len(dirty.splitlines())} paths")
    result = {"head": actual}
    if base:
        code, _ = git(cwd, "merge-base", "--is-ancestor", base, actual, ok=(0, 1))
        if code:
            problems.append("base не ancestor HEAD")
        _, base = git(cwd, "rev-parse", base)
        if new_commit and base == actual:
            problems.append("нет нового commit")
        _, names = git(cwd, "diff", "--name-only", base, actual)
        changed = names.splitlines()
        result["changed"] = len(changed)
        if scope:
            outside = [p for p in changed
                       if not any(fnmatch.fnmatch(p, s) or p.startswith(s.rstrip("/") + "/") for s in scope)]
            if outside:
                problems.append(f"вне scope: {len(outside)}")
                result["outside_scope"] = outside[:10]
    result["ok"] = not problems
    if problems:
        result["problems"] = problems
    return result


def apply_worker(state, ledger, a, task, data, ids, result):
    """Сверяет commit implementer/reviser и продвигает head запуска либо задачи."""
    cwd = a.cwd or (task or {}).get("cwd") or run_cwd(state, ledger)
    prev = (task.get("head") or task.get("base")) if task is not None else state["head"]
    if not prev:
        raise Fail(f"{a.task}: у задачи нет base")
    blocked = bool(data.get("blocker"))
    info = inspect(cwd, data["head"], prev, not blocked, a.scope or (task or {}).get("write_scope"), blocked)
    if not info["ok"]:
        out(info)
        sys.exit(1)
    result.update(head=info["head"], checks=len(data["checks"]), changed=info["changed"], ok=True)
    if task is not None:
        task["head"] = info["head"]
        if not blocked and task.get("state") == "RUNNING":
            task["state"] = "READY_TO_INTEGRATE"
        result["state"] = task.get("state")
    else:
        state["head"] = info["head"]
    if data.get("standards_files"):
        state["standards"] = sorted(set(state.get("standards", [])) | set(data["standards_files"]))
    if state.get("standards"):
        result["standards"] = state["standards"]
    findings = state.get("findings", {})
    for item in data.get("rejected", []):
        if item["id"] in findings:
            findings[item["id"]]["rejected"] = item["evidence"]
    rejected = [item["id"] for item in data.get("rejected", [])]
    if rejected:
        result["rejected"] = rejected
        if any(findings.get(i, {}).get("severity") in CRITICAL for i in rejected):
            result["stop"] = "critical_rejected"
    if a.role == "reviser" and ids:
        critical = any(findings.get(i, {}).get("severity") in CRITICAL for i in ids)
        kind = "critical_iterations" if critical else "minor_iterations"
        counters = state.setdefault("counters", {})
        counters[kind] = counters.get(kind, 0) + 1


def cmd_handoff(a):
    ledger = ledger_dir(a.ledger)
    data = read_json(a, a.role)
    ids = [i for i in (a.ids or "").split(",") if i]
    args = {"task": a.task, "ids": ids}
    with locked(ledger):
        state = load(ledger)
        task = (state.get("tasks") or {}).get(a.task) if a.task else None
        if a.task and task is None:
            raise Fail(f"нет задачи {a.task}")
        slot, key = (task, "handoff") if task is not None else (state, "scout" if a.role == "scout" else "worker")
        result = applied(ledger, slot.get(key), a.role, data, args)
        if result is None:
            result = {}
            if a.role == "scout":
                state["notes"] = result["notes"] = sorted(set(state.get("notes", [])) | set(data["notes"]))
            else:
                apply_worker(state, ledger, a, task, data, ids, result)
            if data.get("blocker"):
                result["blocker"] = data["blocker"]
            slot[key] = store(ledger, state, a.role, data, args, result)
            save(ledger, state)
    out(result)


def cmd_verify(a):
    info = inspect(a.cwd, a.head, a.base, a.new_commit, a.scope)
    out(info)
    if not info["ok"]:
        sys.exit(1)


def location_file(location):
    return re.split(r"[:,;\s]", location.strip(), maxsplit=1)[0]


def number(fid):
    return int(fid[1:]) if fid[1:].isdigit() else 0


def apply_review(state, axis, data, asked, full_spec):
    """Атомарно: dispositions заданных IDs, repaired, новые IDs с severity, coverage оси, признаки лимитов."""
    if data["verdict"] == "BLOCKED_CONTEXT":
        out({"axis": axis, "verdict": "BLOCKED_CONTEXT", "blocker": data.get("blocker"), "stop": "blocked_context"})
        sys.exit(1)
    head, findings = state["head"], state.setdefault("findings", {})
    if not head.startswith(data["head"]):
        raise Fail(f"HEAD reviewer {data['head'][:12]} != {head[:12]}: HUMAN_ATTENTION, coverage не обновлён")
    dispositions = {d["id"]: d for d in data.get("dispositions", [])}
    missing = [i for i in asked if i not in dispositions or i not in findings]
    if missing:
        raise Fail(f"нет explicit FIXED|OPEN либо записи для {','.join(missing)}: HUMAN_ATTENTION")
    foreign = [i for i in asked if findings[i]["axis"] != axis]
    if foreign:
        raise Fail(f"{','.join(foreign)}: замечания другой оси, не {axis}")
    fixed, still_open, new = [], [], []
    for fid in asked:
        if dispositions[fid]["state"] == "FIXED":
            entry = findings.pop(fid)
            state.setdefault("repaired", {}).setdefault(location_file(entry["location"]), []).append(
                {"id": fid, "fix": entry.get("fix", "")})
            fixed.append(fid)
        else:
            findings[fid]["no_progress"] = findings[fid].get("no_progress", 0) + 1
            still_open.append(fid)
    for item in data.get("findings", []):
        fid = f"F{state.get('next_finding_id', 1)}"
        state["next_finding_id"] = state.get("next_finding_id", 1) + 1
        severity = SEVERITY[item["type"]]
        if item.get("scope") == "outside" and item["type"] != "wrong":
            severity = "MINOR"
        findings[fid] = dict(item, axis=axis, severity=severity)
        files = re.findall(r"[\w./\\\-\[\]]+\.[A-Za-z]\w*", item["location"])
        entry = {"id": fid, "severity": severity, "location": item["location"]}
        if files and all(DOCS.search(f) for f in files):
            entry["docs_only"] = True
        new.append(entry)
    record = state["axes"][axis]
    record["last_reviewed_head"] = head
    record.pop("skip", None)
    if full_spec:
        record["full_spec_reviewed_head"] = head
    counters = state.get("counters", {})
    critical = sorted((i for i, f in findings.items() if f["severity"] in CRITICAL), key=number)
    result = {"axis": axis, "head": head, "fixed": fixed, "open": still_open, "new": new, "critical": critical,
              "quality": quality(state)}
    if any(findings[i].get("no_progress", 0) >= LIMITS["no_progress"] for i in critical):
        result["stop"] = "no_progress"
    elif critical and counters.get("critical_iterations", 0) >= LIMITS["critical_iterations"]:
        result["stop"] = "critical_limit"
    if len(findings) > len(critical) and counters.get("minor_iterations", 0) >= LIMITS["minor_iterations"]:
        result["minor_limit"] = True
    return result


def cmd_review(a):
    ledger = ledger_dir(a.ledger)
    if a.skip is not None:
        if not a.axis:
            raise Fail("--skip требует --axis")
        with locked(ledger):
            state = load(ledger)
            state.setdefault("axes", {}).setdefault(a.axis, {})["skip"] = {"head": state["head"], "reason": a.skip}
            save(ledger, state)
        out({"axis": a.axis, "skip": a.skip, "quality": quality(state)})
        return
    if not a.role:
        raise Fail("review: нужна --role либо --axis со --skip")
    data = read_json(a, a.role)
    axis = AXIS[a.role]
    asked = [i for i in (a.ids or "").split(",") if i]
    args = {"ids": asked, "full_spec": a.full_spec}
    with locked(ledger):
        state = load(ledger)
        record = state.setdefault("axes", {}).setdefault(axis, {})
        result = applied(ledger, record.get("handoff"), a.role, data, args)
        if result is None:
            result = apply_review(state, axis, data, asked, a.full_spec)
            record["handoff"] = store(ledger, state, a.role, data, args, result)
            save(ledger, state)
    out(result)


def cmd_gate(a):
    ledger = ledger_dir(a.ledger)
    data = None if a.reuse is not None or a.not_applicable is not None else read_json(a, "verifier")
    with locked(ledger):
        state = load(ledger)
        head = state["head"]
        if a.not_applicable is not None:
            state["gate"] = {"head": head, "verdict": "NOT_APPLICABLE", "reason": a.not_applicable}
            result = {"head": head, "verdict": "NOT_APPLICABLE", "quality": quality(state)}
        elif a.reuse is not None:
            green, cwd = state.get("green"), run_cwd(state, ledger)
            if not green:
                raise Fail("нет полного GREEN для reuse")
            same_tree = git(cwd, "rev-parse", green["head"] + "^{tree}") == git(cwd, "rev-parse", head + "^{tree}")
            if not same_tree and not a.reuse:
                raise Fail(f"reuse GREEN {green['head'][:12]}: дерево отличается, нужен proof")
            state["gate"] = {"head": head, "verdict": "GREEN", "reuse_of": green["head"]}
            if a.reuse:
                state["gate"]["proof"] = a.reuse
            result = {"head": head, "verdict": "GREEN", "reuse_of": green["head"], "quality": quality(state)}
        else:
            result = applied(ledger, (state.get("gate") or {}).get("handoff"), "verifier", data, {})
            if result is not None:
                out(result)
                return
            if not head.startswith(data["head"]):
                raise Fail(f"HEAD verifier {data['head'][:12]} != {head[:12]}: HUMAN_ATTENTION")
            counters = state.setdefault("counters", {})
            if data["verdict"] == "GREEN":
                counters["consecutive_red"] = 0
            elif data["verdict"] == "RED":
                counters["consecutive_red"] = counters.get("consecutive_red", 0) + 1
            state["gate"] = {"head": head, "verdict": data["verdict"]}
            result = {"head": head, "verdict": data["verdict"], "consecutive_red": counters.get("consecutive_red", 0),
                      "quality": quality(state)}
            if data.get("failures"):
                result["failures"] = len(data["failures"])
            if result["consecutive_red"] >= LIMITS["consecutive_red"]:
                result["stop"] = "red_limit"
            state["gate"]["handoff"] = store(ledger, state, "verifier", data, {}, result, ref=True)
            if data["verdict"] == "GREEN":
                state["green"] = {"head": head, "ref": result["ref"]}
        save(ledger, state)
    out(result)


def cmd_finding(a):
    ledger = ledger_dir(a.ledger)
    if a.action == "list":
        out([{"id": i, "axis": f["axis"], "severity": f["severity"], "location": f["location"],
              **({"no_progress": f["no_progress"]} if f.get("no_progress") else {})}
             for i, f in load(ledger).get("findings", {}).items()])
        return
    ids = [i for i in (a.ids or "").split(",") if i]
    with locked(ledger):
        state = load(ledger)
        findings = state.setdefault("findings", {})
        missing = [i for i in ids if i not in findings]
        if not ids or missing:
            raise Fail(f"нет OPEN finding {','.join(missing) or '(ID не заданы)'}")
        if a.action == "severity":
            if a.value not in ("BLOCKER", "MAJOR", "MINOR"):
                raise Fail("severity: BLOCKER|MAJOR|MINOR")
            for fid in ids:
                findings[fid]["severity"] = a.value
        elif a.action == "leave":  # оставленные замечания: в итог запуска без решения человека
            critical = [i for i in ids if findings[i]["severity"] in CRITICAL]
            if critical:
                raise Fail(f"leave только для MINOR: {','.join(critical)}")
            for fid in ids:
                entry = findings.pop(fid)
                state.setdefault("left", []).append(
                    {"id": fid, "axis": entry["axis"], "location": entry["location"], "fix": entry.get("fix", "")})
        else:  # close: решение человека (WONT_FIX, linked task, REJECTED)
            if not a.value:
                raise Fail("close требует reason")
            for fid in ids:
                entry = findings.pop(fid)
                state.setdefault("human_dispositions", []).append(
                    {"id": fid, "location": entry["location"], "reason": a.value})
        save(ledger, state)
    out({"ok": True})


def merged_by(cwd, tip, before, source):
    """Tip объясняется интеграцией source поверх before: fast-forward либо merge commit этих двух родителей."""
    if tip == source:
        return git(cwd, "merge-base", "--is-ancestor", before, tip, ok=(0, 1))[0] == 0
    code, parents = git(cwd, "rev-parse", tip + "^1", tip + "^2", ok=(0, 128))
    return code == 0 and parents.split() == [before, source]


def cmd_integrate(a):
    ledger = ledger_dir(a.ledger)
    with locked(ledger):
        state = load(ledger)
        tasks = state.get("tasks") or {}
        task, cwd = tasks.get(a.task), a.cwd or (state.get("integration") or {}).get("cwd")
        if task is None or not cwd:
            raise Fail(f"нет задачи {a.task} либо integration.cwd")
        intent = state.get("integrating")
        if intent and intent.get("task") != a.task:
            raise Fail(f"не завершена интеграция {intent.get('task')}: сначала её")
        _, tip = git(cwd, "rev-parse", "HEAD")
        if not intent:
            if task.get("state") != "READY_TO_INTEGRATE" or not task.get("head"):
                raise Fail(f"{a.task}: state {task.get('state')}, нужен READY_TO_INTEGRATE")
            if tip != state["head"] or git(cwd, "status", "--porcelain")[1]:
                raise Fail(f"integration {tip[:12]}: ожидался чистый {state['head'][:12]}: HUMAN_ATTENTION")
            intent = state["integrating"] = {"task": a.task, "source": task["head"], "before": tip}
            save(ledger, state)
        source, before = intent["source"], intent["before"]
        if os.path.exists(os.path.join(cwd, git(cwd, "rev-parse", "--git-path", "MERGE_HEAD")[1])):
            git(cwd, "merge", "--abort")  # собственный зависший merge
            _, tip = git(cwd, "rev-parse", "HEAD")
        if tip == before:
            code, _ = git(cwd, "merge", "--no-edit", "-m", f"Merge {task.get('branch') or a.task}", source, ok=(0, 1))
            if code:
                _, files = git(cwd, "diff", "--name-only", "--diff-filter=U")
                git(cwd, "merge", "--abort")
                del state["integrating"]
                save(ledger, state)
                out({"task": a.task, "conflict": True, "files": files.splitlines()})
                sys.exit(1)
            _, tip = git(cwd, "rev-parse", "HEAD")
        elif not merged_by(cwd, tip, before, source):
            raise Fail(f"integration {tip[:12]} не объясняется merge {a.task}: HUMAN_ATTENTION")
        task["state"], state["head"] = "INTEGRATED", tip
        del state["integrating"]
        save(ledger, state)
    done = ("INTEGRATED", "REVIEWED")
    out({"task": a.task, "head": tip, "state": "INTEGRATED",
         "unblocked": sorted(name for name, other in tasks.items() if other.get("state") == "PENDING"
                             and all(tasks.get(dep, {}).get("state") in done for dep in other.get("deps", [])))})


def cmd_cleanup(a):
    ledger = ledger_dir(a.ledger)
    state = load(ledger)
    untouched = state.get("head") == state.get("base") and not os.path.exists(os.path.join(ledger, "handoffs"))
    if state.get("status") != "COMPLETED" and not untouched:
        raise Fail(f"cleanup только после COMPLETED либо для нетронутого запуска, сейчас {state.get('status')}")
    shutil.rmtree(ledger)
    out({"removed": ledger})


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rr")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, ledger=True):
        p = sub.add_parser(name)
        p.set_defaults(func=func)
        if ledger:
            p.add_argument("--ledger", required=True)
        return p

    p = add("init", cmd_init)
    p.add_argument("--cwd")
    p.add_argument("--target")
    p.add_argument("pairs", nargs="*")
    p = add("get", cmd_get)
    p.add_argument("--all", action="store_true")
    p.add_argument("paths", nargs="*")
    p = add("set", cmd_set)
    p.add_argument("--delete", action="append", default=[])
    p.add_argument("pairs", nargs="*")
    p = add("handoff", cmd_handoff)
    p.add_argument("--role", required=True, choices=("implementer", "reviser", "scout"))
    p.add_argument("--task")
    p.add_argument("--cwd")
    p.add_argument("--scope", action="append")
    p = add("review", cmd_review)
    p.add_argument("--role", choices=sorted(AXIS))
    p.add_argument("--full-spec", action="store_true")
    p.add_argument("--axis", choices=sorted(AXIS.values()))
    p.add_argument("--skip")
    p = add("gate", cmd_gate)
    p.add_argument("--reuse", nargs="?", const="")
    p.add_argument("--not-applicable")
    for name in ("handoff", "review", "gate"):
        sub.choices[name].add_argument("--file")
    for name in ("handoff", "review"):
        sub.choices[name].add_argument("--ids")
    p = add("finding", cmd_finding)
    p.add_argument("action", choices=("list", "severity", "close", "leave"))
    p.add_argument("ids", nargs="?")
    p.add_argument("value", nargs="?")
    p = add("integrate", cmd_integrate)
    p.add_argument("--task", required=True)
    p.add_argument("--cwd")
    p = add("verify", cmd_verify, ledger=False)
    p.add_argument("--cwd", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--base")
    p.add_argument("--new-commit", action="store_true")
    p.add_argument("--scope", action="append")
    add("cleanup", cmd_cleanup)

    args = parser.parse_args(argv)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        args.func(args)
    except (Fail, OSError) as err:
        print(f"rr: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
