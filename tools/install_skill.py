"""把本仓库装成技能：在 `~/.agents/skills/` 下建一个指回仓库的链接。

Windows 用 junction（不需要管理员），其它平台用符号链接；已经装过则原地更新。

    python tools/install_skill.py            # 安装 / 更新
    python tools/install_skill.py --check    # 只检查
    python tools/install_skill.py --remove   # 卸掉
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAME = os.path.basename(ROOT)                     # ww-autoshop-automation
HOME = os.path.expanduser("~")
TARGETS = [
    os.path.join(HOME, ".agents", "skills", NAME),
]


def is_link(path: str) -> bool:
    if os.path.islink(path):
        return True
    return bool(os.path.exists(path) and os.path.isdir(path)
                and os.stat(path, follow_symlinks=False).st_file_attributes & 0x400)  # junction


def points_here(path: str) -> bool:
    try:
        return os.path.realpath(path) == os.path.realpath(ROOT)
    except OSError:
        return False


def install_one(target: str, check_only: bool) -> int:
    if os.path.exists(target) or is_link(target):
        if points_here(target):
            print("[ok] 已装：%s" % target)
            return 0
        if check_only:
            print("[!!] 已存在但指向别处：%s" % target)
            return 4
        if is_link(target):
            os.remove(target)
        else:
            shutil.rmtree(target)
        print("[..] 旧目录已移除：%s" % target)
    if check_only:
        print("[!!] 未安装：%s" % target)
        return 4
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", target, ROOT],
                              capture_output=True, text=True)
        if done.returncode != 0:
            print("[!!] mklink 失败：%s" % (done.stderr or done.stdout).strip())
            return 1
    else:
        os.symlink(ROOT, target, target_is_directory=True)
    print("[ok] 已安装：%s -> %s" % (target, ROOT))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)

    if args.remove:
        for target in TARGETS:
            if os.path.exists(target) or is_link(target):
                os.remove(target) if is_link(target) else shutil.rmtree(target)
                print("[ok] 已移除：%s" % target)
        return 0

    code = 0
    for target in TARGETS:
        code |= install_one(target, args.check)
    return code


if __name__ == "__main__":
    sys.exit(main())
