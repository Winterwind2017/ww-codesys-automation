"""从本机内核生成技能仓库的 `capabilities.json` 快照，并刷新 SKILL.md 里的能力块。

技能是独立仓库：装到别的机器上时可能没装内核。所以能力清单落成**带出处**的 JSON，
技能自带、离线可校验；刷新时在本机跑一次（前提：内核可 import 或是 git 仓库）。

    python tools/sync_capabilities.py            # 刷新快照 + 重渲染 SKILL.md 索引
    python tools/sync_capabilities.py --check    # 只比对，不写
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SNAPSHOT = os.path.join(ROOT, "capabilities.json")
SKILL = os.path.join(ROOT, "SKILL.md")

BEGIN = "<!-- gen:capabilities:BEGIN -->"
END = "<!-- gen:capabilities:END -->"

KERNEL_REPO = "https://github.com/Winterwind2017/codesyskit"
KERNEL_DIR = os.environ.get("CODESYSKIT_SRC", r"D:\bililive\codesyskit")

FAMILY_LABEL = {
    "svc": "常驻服务（进程/协议）",
    "dev": "设备仓库",
    "proj": "工程",
    "code": "程序与文本",
    "build": "编译与判据",
    "engine": "引擎行为（实测事实）",
    "cli": "命令行",
}

# id -> (family, level, 证据)
# L1 只读 · L2 会话/协议 · L3 写工程 · L4 编译判据
CAPS: dict[str, tuple[str, str, str]] = {
    # ---- 常驻服务 ----
    "svc.start": ("svc", "L2", "live_service：service.start 7.3 s，返回 ping 成功后的 state"),
    "svc.stop": ("svc", "L2", "live_service：quit 后 1.2 s 退出；残留 taskkill 兜底"),
    "svc.status": ("svc", "L2", "cli：status 在无服务时退出码 2"),
    "svc.token": ("svc", "L2", "live_service + test_client：错 token -> E_TOKEN，先于命令查找"),
    "svc.timeout": ("svc", "L2", "test_client：0.5 s 超时对 3 s 慢命令 -> E_TIMEOUT 且提前返回"),
    "svc.batch": ("svc", "L2", "live_service + test_client：逐条 ok/code，部分失败不丢"),
    "svc.errors": ("svc", "L2", "errors.ALL 11 个码封闭集合，test_protocol 校验唯一性"),
    "svc.random_port": ("svc", "L2", "port=0 由引擎选端口并写入 service.json（实测 64054 等）"),
    "svc.one_request": ("svc", "L2", "一连接一请求：keep-alive 会饿死第二个客户端（实测 10 s 超时）"),
    # ---- 设备仓库 ----
    "dev.list": ("dev", "L1", "live_service：get_all_devices 1562 条"),
    "dev.filter": ("dev", "L1", "live_service：filter=CODESYS Control Win V3 命中 2 条"),
    # ---- 工程 ----
    "proj.create": ("proj", "L3", "live_service：project.create(+device+task) 3.6 s，返回 program/task 路径"),
    "proj.create_bare": ("proj", "L3", "project.create(bare=True) 只加设备，不建 POU/任务"),
    "proj.open": ("proj", "L3", "live_service：projects.open 重开同一工程"),
    "proj.save": ("proj", "L3", "live_service：save 后 dirty=False"),
    "proj.close": ("proj", "L3", "live_service：close -> {closed: path}"),
    "proj.info": ("proj", "L2", "live_service：application 路径为 /PLC/Plc Logic/Application"),
    "proj.tree": ("proj", "L2", "tree 按 /A/B/C 行走 get_children，段不存在 -> E_STATE"),
    # ---- 程序与文本 ----
    "code.pou_create": ("code", "L3", "live_service：create_program(language=ImplementationLanguages.st)"),
    "code.pou_read": ("code", "L2", "live_service：declaration 45 字符回读一致"),
    "code.pou_write": ("code", "L3", "live_service：replace(0,len,text) + readback_match=True"),
    "code.tasks": ("code", "L3", "live_service：task.create/tasks，MainTask 20 ms 绑定 PLC_PRG"),
    # ---- 编译与判据 ----
    "build.compile": ("build", "L4", "live_service：合法 ST -> 0 错误（Service.compile）"),
    "build.diagnostics": ("build", "L4", "live_service：写坏代码 -> 12 错误 2 警告，码 C189/C139/C9/C190"),
    "build.restore": ("build", "L4", "live_service：改回合法代码 -> 重新 0 错误（可来回）"),
    "build.task_required": ("build", "L4", "live_service：无任务配置的 bare 工程对同样乱码报 0 错误（假绿灯）"),
    "build.readback": ("build", "L4", "live_service：close -> open -> 读 implementation 与写入一致"),
    "build.log_parse": ("build", "L4", "test_engine_log：解析编译完成 N错误,M警告 与 C 码，丢弃 Text 进度行"),
    # ---- 引擎行为 ----
    "engine.headless": ("engine", "L2", "live_service：ui_present=False，全程无窗口"),
    "engine.profile_quoting": ("engine", "L2", "实测：--profile 必须带字面引号，否则退出 1 并提示 --noUI 模式"),
    "engine.ironpython": ("engine", "L1", "sys.version = CODESYS.exe 3.5.22.20, ScriptEngine.plugin 4.2.0.0（IronPython 2.7）"),
    # ---- 命令行 ----
    "cli.verbs": ("cli", "L2", "cli 冒烟：start/status/devices/call/stop，退出码 0/1/2/3/4 实测"),
}

# 还没打通 / 已证伪（技能里"别试这些"用）
PENDING = [
    ("online.login", "ScriptOnline 19 类 112 方法，但需要可达的 PLC 或本地软 PLC，未实测"),
    ("online.download", "下载/RUN-STOP 同理，需要目标 PLC"),
    ("monitor.live", "在线读变量需要登录成功后才有值"),
    ("lib.manage", "LibManager 74 方法未验证；客户工程的库版本是单独问题"),
    ("pkg.manage", "PackageManagerCLI/IPMCLI 可跑但未验证装包对设备仓库的影响"),
    ("trace.configure", "ScriptTraceObject/可视化资源存在，没有实测配方"),
    ("archive.exchange", "save_archive/export_xml/import_xml 未实测"),
    ("com.register",
     "已证伪：ScriptEngine3.dll 只有 3 个 attribute/exception 类可注册，_3S.CoDeSys* 注册表 0 命中"),
    ("exec.arbitrary", "exec 命令在引擎内跑任意 IronPython，默认关闭，需 --allow-exec"),
]


def kernel_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", KERNEL_DIR, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - 快照不需要这个字段也能用
        return "unknown"


def cli_commands() -> list[str]:
    if KERNEL_DIR not in sys.path:
        sys.path.insert(0, os.path.join(KERNEL_DIR, "src"))
    try:
        from codesyskit import cli  # noqa: F401

        text = inspect.getsource(cli)
        return sorted(set(re.findall(r'sub\.add_parser\(\s*"([a-z0-9_\-]+)"', text)))
    except Exception:  # noqa: BLE001
        return []


def build_snapshot() -> dict:
    families = {}
    for cap_id, (family, _level, _evidence) in CAPS.items():
        families[family] = families.get(family, 0) + 1
    return {
        "schema": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provenance": {
            "kernel": "codesyskit",
            "kernel_repo": KERNEL_REPO,
            "kernel_commit": kernel_commit(),
            "engine": "CODESYS Development System 3.5.22.20 (ScriptEngine.plugin 4.2.0.0)",
        },
        "cli_commands": cli_commands(),
        "counts": {"verified": len(CAPS), "families": len(families), "pending": len(PENDING)},
        "verified": {cap: info[0] for cap, info in CAPS.items()},
        "levels": {cap: info[1] for cap, info in CAPS.items()},
        "evidence": {cap: info[2] for cap, info in CAPS.items()},
        "pending": [{"id": cap, "reason": reason} for cap, reason in PENDING],
    }


def render_block() -> str:
    lines = [BEGIN, "", "| 能力 | 族 | 级别 | 证据 |", "| --- | --- | --- | --- |"]
    for family in FAMILY_LABEL:
        for cap, info in CAPS.items():
            if info[0] != family:
                continue
            lines.append("| `%s` | %s | %s | %s |" % (cap, FAMILY_LABEL[family], info[1], info[2]))
    lines += ["", "<!-- 由 tools/sync_capabilities.py 生成，勿手改 -->", END]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只比对")
    args = parser.parse_args(argv)

    snapshot = build_snapshot()
    rendered = render_block()

    skill_text = open(SKILL, encoding="utf-8").read()
    if BEGIN in skill_text and END in skill_text:
        head, rest = skill_text.split(BEGIN, 1)
        _old, tail = rest.split(END, 1)
        new_skill = head + rendered + tail
    else:
        new_skill = skill_text + "\n\n" + rendered + "\n"

    current = open(SNAPSHOT, encoding="utf-8").read() if os.path.exists(SNAPSHOT) else ""
    new_json = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"

    json_same = json.loads(current)["verified"] == snapshot["verified"] if current else False
    skill_same = new_skill == skill_text

    if args.check:
        if json_same and skill_same:
            print("capabilities: 一致（%d 条 verified / %d 条 pending）" %
                  (snapshot["counts"]["verified"], snapshot["counts"]["pending"]))
            return 0
        print("capabilities: **不一致**，跑一次 tools/sync_capabilities.py")
        return 3

    with open(SNAPSHOT, "w", encoding="utf-8") as handle:
        handle.write(new_json)
    md = ["# 能力清单（快照）", "",
          "由 `tools/sync_capabilities.py` 从内核生成；出处 `%s@%s`。" % (
              snapshot["provenance"]["kernel"], snapshot["provenance"]["kernel_commit"]),
          "", "## 已打通（%d）" % snapshot["counts"]["verified"], "",
          "| 能力 | 族 | 级别 | 证据 |", "| --- | --- | --- | --- |"]
    for cap, info in CAPS.items():
        md.append("| `%s` | %s | %s | %s |" % (cap, FAMILY_LABEL[info[0]], info[1], info[2]))
    md += ["", "## 未打通 / 已证伪（%d）" % snapshot["counts"]["pending"], ""]
    for cap, reason in PENDING:
        md.append("- `%s` — %s" % (cap, reason))
    with open(os.path.join(ROOT, "capabilities.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(md) + "\n")
    with open(SKILL, "w", encoding="utf-8") as handle:
        handle.write(new_skill)
    print("wrote %s (%d verified / %d pending, kernel %s)" % (
        os.path.basename(SNAPSHOT), snapshot["counts"]["verified"],
        snapshot["counts"]["pending"], snapshot["provenance"]["kernel_commit"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
