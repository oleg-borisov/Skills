#!/usr/bin/env python3
"""Механика ledger rr workflows: атомарный state, handoffs, findings, сверка Git, cleanup.

Вызывает только primary-controller. Вывод — одна компактная строка JSON; ошибка — строка в stderr и код 1.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SHA = re.compile(r"^[0-9a-f]{7,64}$")
WORKER = {"head": "sha", "checks": [{"cmd": str, "result": str}], "affected_review_axes": ["Spec", "Standards"]}
ROLES = {
    "implementer": WORKER,
    "reviser": WORKER,
    "scout": {"notes": [str]},
    "spec-reviewer": {"head": "sha", "verdict": ("APPROVE", "FINDINGS", "NO_SPEC", "BLOCKED_CONTEXT")},
    "standards-reviewer": {"head": "sha", "verdict": ("APPROVE", "FINDINGS", "BLOCKED_CONTEXT")},
    "verifier": {"head": "sha", "verdict": ("GREEN", "RED", "BLOCKED"),
                 "validation_plan": {"checks": [{"cmd": str, "result": str}]}},
}
OPTIONAL = {
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
            if isinstance(schema[0], (dict, type)):
                check(item, schema[0], f"{where}[{i}]")
            elif item not in schema:
                raise Fail(f"{where}[{i}]: {item!r} не из {'|'.join(schema)}")
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


def ledger_dir(path):
    """LEDGER_DIR = <checkout>/.scratch/<workflow>/<run>, без symlink/junction компонентов."""
    full = os.path.abspath(path)
    parts = full.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[-3] != ".scratch" or not parts[-1] or not parts[-2]:
        raise Fail(f"ledger должен быть <checkout>/.scratch/<workflow>/<run>: {full}")
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


def save(ledger, state):
    fd, tmp = tempfile.mkstemp(dir=ledger, prefix="state.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, state_path(ledger))


def parse_value(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def assign(state, pairs):
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise Fail(f"нужно path=value: {pair}")
        node = state
        *parents, leaf = key.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = parse_value(value)


def lookup(state, key):
    node = state
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def out(value):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def cmd_init(a):
    ledger = ledger_dir(a.ledger)
    if os.path.exists(state_path(ledger)):
        raise Fail(f"ledger уже существует, status={load(ledger).get('status')}: resume или reset по решению человека")
    root = os.path.dirname(os.path.dirname(os.path.dirname(ledger)))
    _, exclude = git(root, "rev-parse", "--git-path", "info/exclude")
    exclude = os.path.join(root, exclude)
    lines = open(exclude, encoding="utf-8").read().splitlines() if os.path.exists(exclude) else []
    if ".scratch/" not in lines:
        os.makedirs(os.path.dirname(exclude), exist_ok=True)
        with open(exclude, "a", encoding="utf-8") as fh:
            fh.write(".scratch/\n")
    os.makedirs(ledger, exist_ok=True)
    _, head = git(a.cwd or root, "rev-parse", "HEAD")
    state = {"workflow": os.path.basename(os.path.dirname(ledger)), "status": "RUNNING", "quality": "UNVERIFIED",
             "base": head, "head": head, "findings": {}, "next_finding_id": 1, "repaired": {}, "axes": {}}
    assign(state, a.pairs)
    save(ledger, state)
    out({"ledger": ledger, "base": head})


def cmd_get(a):
    state = load(ledger_dir(a.ledger))
    if a.all:
        out(state)
    elif a.paths:
        out({key: lookup(state, key) for key in a.paths})
    else:
        out({key: (len(value) if isinstance(value, (dict, list)) else value) for key, value in state.items()})


def cmd_set(a):
    ledger = ledger_dir(a.ledger)
    state = load(ledger)
    assign(state, a.pairs)
    for key in a.delete:
        *parents, leaf = key.split(".")
        node = lookup(state, ".".join(parents)) if parents else state
        if isinstance(node, dict):
            node.pop(leaf, None)
    save(ledger, state)
    out({"ok": True})


def handoff_path(ledger, name):
    if not re.match(r"^[\w.\-]+$", name):
        raise Fail(f"недопустимое имя handoff: {name}")
    return os.path.join(ledger, "handoffs", name + ".json")


def cmd_handoff(a):
    ledger = ledger_dir(a.ledger)
    load(ledger)
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    try:
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
    except ValueError as err:
        raise Fail(f"handoff не JSON: {err}")
    check(data, ROLES[a.role], a.role)
    for key, schema in OPTIONAL.items():
        if key in data:
            check(data[key], schema, key)
    if a.role in FINDING:
        check(data.get("findings", []), [FINDING[a.role]], "findings")
        has_open = bool(data.get("findings")) or any(d["state"] == "OPEN" for d in data.get("dispositions", []))
        if (data["verdict"] == "FINDINGS") != has_open and data["verdict"] in ("APPROVE", "FINDINGS"):
            raise Fail("verdict FINDINGS должен совпадать с наличием findings/OPEN dispositions")
    if a.role == "verifier" and (data["verdict"] == "GREEN") == bool(data.get("failures")):
        raise Fail("verifier: failures обязательны при RED/BLOCKED и запрещены при GREEN")
    path = handoff_path(ledger, a.name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(data, role=a.role), fh, ensure_ascii=False, indent=1)
    summary = {"ref": path, "head": data.get("head"), "verdict": data.get("verdict")}
    for key in ("findings", "dispositions", "failures", "rejected", "checks", "notes"):
        if data.get(key):
            summary[key] = len(data[key])
    for key in ("affected_review_axes", "blocker"):
        if data.get(key):
            summary[key] = data[key]
    out({key: value for key, value in summary.items() if value is not None})


def cmd_verify(a):
    problems = []
    _, head = git(a.cwd, "rev-parse", "HEAD")
    if not head.startswith(a.head):
        problems.append(f"HEAD {head[:12]} != {a.head[:12]}")
    _, dirty = git(a.cwd, "status", "--porcelain")
    if dirty:
        problems.append(f"dirty: {len(dirty.splitlines())} paths")
    result = {"head": head}
    if a.base:
        code, _ = git(a.cwd, "merge-base", "--is-ancestor", a.base, head, ok=(0, 1))
        if code:
            problems.append("base не ancestor HEAD")
        _, base = git(a.cwd, "rev-parse", a.base)
        if a.new_commit and base == head:
            problems.append("нет нового commit")
        _, names = git(a.cwd, "diff", "--name-only", base, head)
        changed = names.splitlines()
        result["changed"] = len(changed)
        if a.scope:
            outside = [p for p in changed
                       if not any(fnmatch.fnmatch(p, s) or p.startswith(s.rstrip("/") + "/") for s in a.scope)]
            if outside:
                problems.append(f"вне scope: {len(outside)}")
                result["outside_scope"] = outside[:10]
    result["ok"] = not problems
    if problems:
        result["problems"] = problems
    out(result)
    if problems:
        sys.exit(1)


def location_file(location):
    return re.split(r"[:,;\s]", location.strip(), maxsplit=1)[0]


def cmd_review(a):
    ledger = ledger_dir(a.ledger)
    state = load(ledger)
    try:
        with open(handoff_path(ledger, a.handoff), encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise Fail(f"нет handoff {a.handoff}")
    role = data.get("role")
    if role not in AXIS:
        raise Fail(f"{a.handoff}: не handoff reviewer")
    if data["verdict"] in ("NO_SPEC", "BLOCKED_CONTEXT"):
        raise Fail(f"{data['verdict']}: HUMAN_ATTENTION, coverage не обновлён")
    axis, findings = AXIS[role], state.setdefault("findings", {})
    dispositions = {d["id"]: d for d in data.get("dispositions", [])}
    asked = [i for i in (a.ids or "").split(",") if i]
    missing = [i for i in asked if i not in dispositions or i not in findings]
    if missing:
        raise Fail(f"нет explicit FIXED|OPEN либо записи для {','.join(missing)}: HUMAN_ATTENTION")
    fixed, still_open = [], []
    for fid in asked:
        if dispositions[fid]["state"] == "FIXED":
            entry = findings.pop(fid)
            state.setdefault("repaired", {}).setdefault(location_file(entry["location"]), []).append(
                {"id": fid, "fix": entry.get("fix", "")})
            fixed.append(fid)
        else:
            findings[fid]["no_progress"] = findings[fid].get("no_progress", 0) + 1
            still_open.append(fid)
    new = []
    for item in data.get("findings", []):
        fid = f"F{state.get('next_finding_id', 1)}"
        state["next_finding_id"] = state.get("next_finding_id", 1) + 1
        severity = SEVERITY[item["type"]]
        if item.get("scope") == "outside" and item["type"] != "wrong":
            severity = "MINOR"
        findings[fid] = dict(item, axis=axis, severity=severity, head=data["head"])
        files = re.findall(r"[\w./\\\-\[\]]+\.[A-Za-z]\w*", item["location"])
        entry = {"id": fid, "severity": severity, "location": item["location"]}
        if files and all(DOCS.search(f) for f in files):
            entry["docs_only"] = True
        new.append(entry)
    coverage = state.setdefault("axes", {}).setdefault(axis, {})
    coverage["last_reviewed_head"] = data["head"]
    if a.full_spec:
        coverage["full_spec_reviewed_head"] = data["head"]
    save(ledger, state)
    out({"axis": axis, "head": data["head"], "fixed": fixed, "open": still_open, "new": new,
         "critical": sorted(i for i, f in findings.items() if f["severity"] in ("BLOCKER", "MAJOR"))})


def cmd_finding(a):
    ledger = ledger_dir(a.ledger)
    state = load(ledger)
    findings = state.setdefault("findings", {})
    if a.action == "list":
        out([{"id": i, "axis": f["axis"], "severity": f["severity"], "location": f["location"],
              **({"no_progress": f["no_progress"]} if f.get("no_progress") else {})} for i, f in findings.items()])
        return
    if a.id not in findings:
        raise Fail(f"нет OPEN finding {a.id}")
    if a.action == "severity":
        if a.value not in ("BLOCKER", "MAJOR", "MINOR"):
            raise Fail("severity: BLOCKER|MAJOR|MINOR")
        findings[a.id]["severity"] = a.value
    else:  # close: решение человека (WONT_FIX, linked task, REJECTED)
        if not a.value:
            raise Fail("close требует reason")
        entry = findings.pop(a.id)
        state.setdefault("human_dispositions", []).append(
            {"id": a.id, "location": entry["location"], "reason": a.value})
    save(ledger, state)
    out({"ok": True})


def cmd_cleanup(a):
    ledger = ledger_dir(a.ledger)
    status = load(ledger).get("status")
    if status != "COMPLETED":
        raise Fail(f"cleanup только после COMPLETED, сейчас {status}")
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
    p.add_argument("pairs", nargs="*")
    p = add("get", cmd_get)
    p.add_argument("--all", action="store_true")
    p.add_argument("paths", nargs="*")
    p = add("set", cmd_set)
    p.add_argument("--delete", action="append", default=[])
    p.add_argument("pairs", nargs="*")
    p = add("handoff", cmd_handoff)
    p.add_argument("--role", required=True, choices=sorted(ROLES))
    p.add_argument("--name", required=True)
    p.add_argument("--file")
    p = add("verify", cmd_verify, ledger=False)
    p.add_argument("--cwd", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--base")
    p.add_argument("--new-commit", action="store_true")
    p.add_argument("--scope", action="append")
    p = add("review", cmd_review)
    p.add_argument("--handoff", required=True)
    p.add_argument("--ids")
    p.add_argument("--full-spec", action="store_true")
    p = add("finding", cmd_finding)
    p.add_argument("action", choices=("list", "severity", "close"))
    p.add_argument("id", nargs="?")
    p.add_argument("value", nargs="?")
    add("cleanup", cmd_cleanup)

    args = parser.parse_args(argv)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        args.func(args)
    except Fail as err:
        print(f"rr: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
