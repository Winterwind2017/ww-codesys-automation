# ww-codesys-automation

CODESYS 3.5 的**无界面自动化技能**（执行内核：[codesyskit](https://github.com/Winterwind2017/codesyskit)）。

本仓库只放"怎么用、怎么验证、什么别试"：`SKILL.md` 给 agent 路由用，
`capabilities.json` 是离线可校验的能力快照，`references/` 是配方、坑和验收清单。

## 安装

```powershell
python tools\install_skill.py            # 在 ~/.agents/skills 下建 junction
python tools\install_hooks.py            # 装 pre-push 自检（可选）
```

## 自检

```powershell
python tools\check_skill.py --check
python tools\sync_capabilities.py --check
python -m pytest tests -q
```

## 目录

```
SKILL.md              agent 路由用的正文（含自动生成的能力表）
capabilities.json     能力快照（含内核 commit 与逐条证据）
capabilities.md       人读版本
references/           recipes.md / pitfalls.md / checklists.md
tools/                sync_capabilities / check_skill / install_skill / install_hooks
tests/                test_skill.py（不需要内核与 CODESYS）
```

## 三条最容易踩的

1. **没有任务配置的工程编译永远是 0 错误**（假绿灯）；
2. **编译诊断只在 stderr**，`system.get_messages()` 恒空；
3. **COM 注册不了**（没有引擎类），要用常驻服务。
