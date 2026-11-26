"""Prepare named spec-delivery profiles for inspection before installation."""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
ROLES = ("implementer", "verifier", "standards-reviewer", "spec-reviewer", "reviser", "scout")
READ_ONLY = {"verifier", "standards-reviewer", "spec-reviewer"}
TARGETS = {
    "antigravity": ".gemini/config/plugins/serenity-agents/agents",
    "claude": ".claude/agents",
    "codex": ".codex/agents",
    "devin": ".config/devin/agents",
    "opencode": ".config/opencode/agents",
    "qoder": ".qoder/agents",
    "vibe": ".vibe/agents",
    "zcode": ".zcode/agents",
}
TOML_HOSTS = {"codex", "vibe"}


def install_dir(host):
    if host == "devin" and os.name == "nt":
        return Path(os.environ["APPDATA"]) / "devin/agents"
    if host == "codex" and os.environ.get("CODEX_HOME"):
        return Path(os.environ["CODEX_HOME"]) / "agents"
    if host == "vibe" and os.environ.get("VIBE_HOME"):
        return Path(os.environ["VIBE_HOME"]) / "agents"
    return Path.home() / TARGETS[host]


def quote(value):
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def frontmatter(text):
    return text.split("---\n", 2)[1]


def installed_model(profile, host):
    if not profile.is_file():
        return None
    text = profile.read_text(encoding="utf-8-sig")
    if host in TOML_HOSTS:
        key = "active_model" if host == "vibe" else "model"
        pattern = rf"^{key}[ \t]*=[ \t]*"
        text = re.split(r"^\s*\[", text, maxsplit=1, flags=re.M)[0]
    else:
        if not text.startswith("---\n"):
            return None
        text = frontmatter(text)
        pattern = r"^model[ \t]*:[ \t]*"
    match = re.search(pattern + r"""("(?:[^"\\]|\\.)*"|'[^']*'|[^\s#]+)""", text, re.M)
    if match:
        value = match[1]
        if value.startswith('"'):
            return json.loads(value)
        return value.strip("'")
    return None


def render(host, role, metadata, contract, model):
    description = metadata["description"]
    effort = metadata["reasoning_effort"]
    read_only = role in READ_ONLY
    shim = (
        f"Ты — leaf {role} spec-delivery. Первым шагом прочитай файл `{contract}` "
        "и точно следуй контракту роли. Если файл нечитаем, остановись и сообщи путь и ошибку."
    )
    if host == "codex":
        fields = {
            "name": role, "description": description,
            **({"model": model} if model != "inherit" else {}),
            "model_reasoning_effort": effort,
            "sandbox_mode": "read-only" if read_only else "workspace-write",
            "developer_instructions": shim,
        }
        return "".join(f"{key} = {quote(value)}\n" for key, value in fields.items())
    if host == "vibe":
        lines = [
            'agent_type = "subagent"', f"description = {quote(description)}",
            'disabled_tools = ["agents_spawn"]', f"instructions = {quote(shim)}",
        ]
        if model != "inherit":
            lines.append(f"active_model = {quote(model)}")
        if read_only:
            for tool in ("write_file", "edit"):
                lines += ["", f"[tools.{tool}]", 'permission = "never"']
        return "\n".join(lines) + "\n"

    lines = ["---", f"name: {role}", f"description: {quote(description)}"]
    if model != "inherit":
        lines.append(f"model: {quote(model)}")
    temperature = "0.1" if role == "verifier" else "0.2"
    if host == "antigravity":
        lines += ["mainAgent: false", "subagent: true"]
        if read_only:
            lines += ["tools:", "  - view_file", "  - grep_search", "  - run_command"]
    elif host == "opencode":
        lines += ["mode: subagent", f"temperature: {temperature}", "permission:",
                  "  edit: " + ("deny" if read_only else "allow"), "  bash: allow", "  task: deny"]
    elif host == "devin" and read_only:
        lines += ["allowed-tools:", "  - read", "  - grep", "  - glob", "  - exec"]
    elif host in {"qoder", "zcode", "claude"}:
        if host == "qoder":
            lines.append(f"temperature: {temperature}")
        if host == "claude":
            lines.append(f"effort: {effort}")
        if host == "zcode" and model != "inherit":
            lines.append(f"thoughtLevel: {effort}")
        if read_only:
            lines += ["tools:", "  - Read", "  - Grep", "  - Glob", "  - Bash"]
        elif host in {"claude", "qoder"}:
            lines += ["disallowedTools:", "  - Agent"]
    return "\n".join([*lines, "---", "", shim, ""])


def profiles(args):
    role_dir = args.spec_delivery.expanduser().resolve(strict=True) / "references/roles"
    defaults = {}
    for row in (SKILL / "references/models.md").read_text(encoding="utf-8").splitlines():
        cells = [cell.strip().strip("`") for cell in row.strip("|").split("|")]
        if len(cells) == 3 and cells[0] in TARGETS:
            defaults[cells[0]] = {"strong": cells[1], "cheap": cells[2]}

    overrides = {}
    for assignment in args.model:
        role, _, model = assignment.partition("=")
        if role not in ROLES or not model.strip() or role in overrides:
            raise ValueError(f"Ожидается одна модель на роль: {assignment}")
        overrides[role] = model.strip()

    extension = "toml" if args.host in TOML_HOSTS else "md"
    destination = (args.install_dir or install_dir(args.host)).expanduser().absolute()
    for role in ROLES:
        contract = (role_dir / f"{role}.md").resolve(strict=True)
        metadata = dict(line.split(": ", 1) for line in
                        frontmatter(contract.read_text(encoding="utf-8")).splitlines())
        target = destination / f"{role}.{extension}"
        existing = installed_model(target, args.host)
        recommended = defaults.get(args.host, {}).get(metadata["tier"], "inherit")
        model = overrides.get(role, existing or recommended)
        if args.action == "render" and args.host == "antigravity" and model not in {"inherit", "pro", "flash"}:
            raise ValueError(f"Antigravity: для {role} укажи inherit, pro или flash")
        entry = {
            "role": role, "destination": str(target), "model": model,
            "installed_model": existing, "recommended_model": recommended,
            "reasoning_effort": metadata["reasoning_effort"]
            if args.host in {"codex", "claude", "zcode"} else None,
            "contract": str(contract),
        }
        yield entry, render(args.host, role, metadata, contract, model)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("options", "render"))
    parser.add_argument("host", choices=TARGETS)
    parser.add_argument("--install-dir", type=Path)
    parser.add_argument("--spec-delivery", type=Path, default=SKILL.parent / "spec-delivery")
    parser.add_argument("--model", action="append", default=[], metavar="ROLE=MODEL")
    args = parser.parse_args()
    stage = None
    try:
        prepared = list(profiles(args))
        files = [entry for entry, _ in prepared]
        if args.action == "render":
            staging_root = REPO / ".tmp"
            staging_root.mkdir(exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=f"setup-agents-{args.host}-", dir=staging_root))
            for entry, content in prepared:
                path = stage / Path(entry["destination"]).name
                path.write_bytes(content.encode("utf-8"))
                entry["source"] = str(path)
        print(json.dumps({"stage": str(stage) if stage else None, "files": files}))
    except (OSError, ValueError, KeyError, IndexError) as error:
        if stage:
            shutil.rmtree(stage)
        parser.error(str(error))


if __name__ == "__main__":
    main()
