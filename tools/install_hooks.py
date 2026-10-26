"""装 pre-push 钩子：推之前跑技能自检，不绿就不让推。

    python tools/install_hooks.py
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

HOOK = """#!/bin/sh
set -e
python tools/check_skill.py --check
python tools/sync_capabilities.py --check
python -m pytest tests -q
"""


def main() -> int:
    git_dir = subprocess.run(["git", "-C", ROOT, "rev-parse", "--git-dir"],
                             capture_output=True, text=True)
    if git_dir.returncode != 0:
        print("不是 git 仓库：%s" % ROOT)
        return 1
    path = os.path.join(ROOT, git_dir.stdout.strip(), "hooks", "pre-push")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(HOOK)
    if os.name != "nt":
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("[ok] 已装 pre-push：%s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
