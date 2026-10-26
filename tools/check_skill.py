"""校验技能文档与 `capabilities.json` 快照一致（**不依赖内核**）。

五条规则：

1. SKILL.md 里出现的每个能力 id（`<族>.<名>`）都必须在快照里（verified 或 pending）；
2. pending 能力只允许出现在 `<!-- allow:pending --> … END` 区块内；
3. `codesyskit <cmd>` 的 `<cmd>` 必须在 `cli_commands` 里；
4. 散文里禁止会漂移的数量断言（"31 条能力"、"16/16 通过"）——数量只出现在生成块里；
5. SKILL.md 里的相对链接必须指向真实文件。

    python tools/check_skill.py          # 报告
    python tools/check_skill.py --check  # 有问题退出 4
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL = os.path.join(ROOT, "SKILL.md")
SNAPSHOT = os.path.join(ROOT, "capabilities.json")

ALLOW_BEGIN = "<!-- allow:pending:BEGIN -->"
ALLOW_END = "<!-- allow:pending:END -->"
GEN_BEGIN = "<!-- gen:capabilities:BEGIN -->"
GEN_END = "<!-- gen:capabilities:END -->"

# `app.py`、`capabilities.json` 这类不是能力 id
NOT_ID_SUFFIX = {"py", "md", "json", "toml", "yaml", "yml", "sh", "ps1", "exe", "dll",
                 "log", "txt", "project", "jsonl"}


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def strip_generated(text: str) -> str:
    if GEN_BEGIN in text and GEN_END in text:
        head, rest = text.split(GEN_BEGIN, 1)
        _body, tail = rest.split(GEN_END, 1)
        return head + tail
    return text


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    check_only = "--check" in argv

    problems: list[str] = []
    if not os.path.exists(SNAPSHOT):
        print("缺少 capabilities.json，先跑 tools/sync_capabilities.py")
        return 4
    snapshot = json.loads(read(SNAPSHOT))
    verified = set(snapshot.get("verified", {}))
    pending = {entry["id"] for entry in snapshot.get("pending", [])}
    known = verified | pending
    commands = set(snapshot.get("cli_commands", []))

    text = read(SKILL)
    prose = strip_generated(text)

    # 1. 能力 id 必须在快照里（只认已知族前缀）
    families = {cap.split(".", 1)[0] for cap in known}
    candidates = set(re.findall(r"`([a-z]+\.[a-z0-9_]+)`", prose))
    ids = {cap for cap in candidates
           if cap.split(".", 1)[0] in families and cap.rsplit(".", 1)[-1] not in NOT_ID_SUFFIX}
    for cap in sorted(ids - known):
        problems.append("未知能力 id：%s" % cap)

    # 2. pending 只能在 allow 区块里出现
    if ALLOW_BEGIN in prose and ALLOW_END in prose:
        head, rest = prose.split(ALLOW_BEGIN, 1)
        allowed, tail = rest.split(ALLOW_END, 1)
        outside = head + tail
    else:
        allowed, outside = "", prose
    for cap in sorted(pending):
        if cap in outside:
            problems.append("pending 能力出现在 allow 区块外：%s" % cap)

    # 3. codesyskit 子命令必须真实存在
    for verb in sorted(set(re.findall(r"^codesyskit\s+([a-z0-9_\-]+)", prose, re.M))):
        if verb not in commands and not verb.startswith("-"):
            problems.append("未知子命令：codesyskit %s" % verb)

    # 4. 散文里不准写会漂移的数量断言
    for match in re.finditer(r"(\d+)\s*(条能力|项能力|/\s*\1\s*通过|\1\s*/\s*\1)", prose):
        problems.append("散文里有数量断言（会漂移）：%s" % match.group(0))

    # 5. 相对链接必须存在
    for target in sorted(set(re.findall(r"\]\((?!https?:)([^)#]+)", prose))):
        path = os.path.join(ROOT, target)
        if not os.path.exists(path):
            problems.append("相对链接指向不存在的文件：%s" % target)

    # 快照自检
    counts = snapshot.get("counts", {})
    if counts.get("verified") != len(verified):
        problems.append("counts.verified=%s 与 verified 表(%d) 不一致" %
                        (counts.get("verified"), len(verified)))
    if counts.get("pending") != len(pending):
        problems.append("counts.pending 与 pending 表不一致")
    missing_evidence = [cap for cap in verified if not snapshot.get("evidence", {}).get(cap)]
    if missing_evidence:
        problems.append("这些能力没有证据字段：%s" % ", ".join(sorted(missing_evidence)))
    missing_levels = [cap for cap in verified if not snapshot.get("levels", {}).get(cap)]
    if missing_levels:
        problems.append("这些能力没有级别：%s" % ", ".join(sorted(missing_levels)))

    for line in problems:
        print("[!!]", line)
    if problems:
        return 4 if check_only else 0
    print("check_skill: clean（%d verified / %d pending，%d 个 CLI 子命令）" %
          (len(verified), len(pending), len(commands)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
