"""技能仓库的自检测试（不需要内核、不需要 CODESYS）。

    python -m pytest tests -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "SKILL.md")
SNAPSHOT = os.path.join(ROOT, "capabilities.json")


def test_frontmatter():
    text = open(SKILL, encoding="utf-8").read()
    assert text.startswith("---\n")
    head = text.split("---", 2)[1]
    assert "name: ww-codesys-automation" in head
    assert "description:" in head
    assert len(head) > 200, "description 太短，路由会漏"


def test_snapshot_shape():
    data = json.load(open(SNAPSHOT, encoding="utf-8"))
    assert data["schema"] == 1
    assert data["verified"], "能力表不能为空"
    assert set(data["levels"]) == set(data["verified"]), "level 必须覆盖每条能力"
    assert set(data["evidence"]) == set(data["verified"]), "证据必须覆盖每条能力"
    assert data["counts"]["verified"] == len(data["verified"])
    assert data["counts"]["pending"] == len(data["pending"])
    assert data["provenance"]["kernel_commit"], "快照要带内核 commit"
    assert data["provenance"]["kernel"] == "codesyskit"
    assert data["cli_commands"], "cli_commands 不能为空"


def test_generated_block_present():
    text = open(SKILL, encoding="utf-8").read()
    assert "<!-- gen:capabilities:BEGIN -->" in text
    assert "<!-- gen:capabilities:END -->" in text
    begin, end = text.index("<!-- gen:capabilities:BEGIN -->"), text.index("<!-- gen:capabilities:END -->")
    assert end > begin


def test_check_skill_clean():
    done = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_skill.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert done.returncode == 0, done.stdout + done.stderr


def test_snapshot_in_sync():
    done = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_capabilities.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert done.returncode in (0, 3), done.stdout + done.stderr
    if done.returncode == 3:
        print("[warn] 快照与内核不一致（本机没装内核时正常）：" + done.stdout.strip())


def test_references_exist():
    for name in ("recipes.md", "pitfalls.md", "checklists.md"):
        path = os.path.join(ROOT, "references", name)
        assert os.path.exists(path), path
        assert os.path.getsize(path) > 500, "%s 太空" % name
