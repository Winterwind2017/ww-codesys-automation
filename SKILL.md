---
name: ww-codesys-automation
description: >
  用 codesyskit 在本机 CODESYS Development System 3.5 上做**无界面**的 PLC 工程自动化，
  并**用回读与编译器日志验证结果**。当用户要求新建工程、加设备、写/读 ST 程序、建任务配置、
  编译并读诊断（C 码/错误数）、批量找代码、改对象结构（改名/移动/删除/建文件夹）、
  管库（537 个可用库）、导出/导入 XML 或 PLCopen 原生格式、整包归档、生成运行时文件、
  跑任意 IDE 命令，或问"CODESYS 能不能被脚本/agent 驱动、COM 能不能注册、怎么常驻调用、
  在线登录为什么失败"时使用。内含实测配方、判据、已证伪路径，以及这台引擎特有的坑
  （必须建任务才真编译、编译诊断只在 stderr、--profile 必须带引号、ScriptTextDocument.text 只读、
  print 污染消息列表、UTF-8 传输与路径 identity 的坑）。英文路由：headless CODESYS 3.5
  automation, project/POU/task creation, ST read-write, compile diagnostics from stderr,
  IDE command channel, library management, PLCopenXML/archive exchange, resident service.
---

# ww-codesys-automation

> **这是独立技能仓库**，不随执行内核一起分发。
> 内核是 [codesyskit](https://github.com/Winterwind2017/codesyskit)（Python 库 + CLI，常驻服务），
> 本仓库只负责"**怎么用 + 怎么验证 + 什么别试**"。
> 能力清单以 `capabilities.json` 快照为准（出处：内核 commit + 引擎版本）。

## 这个技能解决什么

CODESYS 3.5 是**天生可编程**的（`--noUI --runscript` + IronPython 脚本引擎），
但它的"成功"很容易骗人：

- **没建任务配置时，`build()` 编译空转、永远打印 `0错误,0警告`** —— 写 `THIS IS NOT ST !!!`
  也是 0 错误。真编译后同一份代码报 12 个错误。
- 编译诊断**不在** `system.get_messages()` 里（恒为 0 条），只出现在进程 **stderr**。
- `create_program(name)` 的默认语言不是 ST，写进 `textual_implementation` 的文本不参与编译。
- `ScriptTextDocument.text` 只读，写要 `replace(offset, length, text)`；`remove` 的参数是 `(offset, length)`。
- `--noUI` 下 `print()` 会进 IDE 消息列表，把自己的日志和编译消息混在一起。
- `--profile` 的值**必须带字面引号**，否则进程直接退出 1。
- 回复里的中文曾经直接**断连**（按字符码写 `Byte[]`，`Cannot convert int(36333) to Byte`），
  请求也是按字符拼的；现在两端都走 UTF-8，但**别的客户端照抄协议时要自己编码**。
- 路径**不能靠对象身份**判断根：引擎每次都给新 wrapper，`/A/B/C` 要按名字走 parent 链；
  新建文件夹返回的对象**还没有名字**，路径得由父路径+名字算。
- COM 是**死路**：`ScriptEngine3.dll` 没有可注册的引擎类，注册表也没有任何 `_3S.CoDeSys*`。

所以本技能的第一原则是：**回读 + 编译器日志 + 负向对照**，不信返回值。

## 60 秒上手

```powershell
codesyskit start                 # 无界面常驻，随机端口，写 service.json（约 7 s）
codesyskit status                # 能 ping 通才算起来了
codesyskit devices --filter "Control Win" --limit 5
codesyskit stop
```

```python
from codesyskit import Service

service = Service()
service.start()
client = service.client(timeout=300)
try:
    project = client.create(r"D:\work\job.project", device="CODESYS Control Win V3")
    pou = project["program"]                      # 已经建好 ST 程序 + 20 ms 任务
    client.write(pou, "nCounter := nCounter + 1;\n", "implementation")
    result = service.compile(client)              # 解析 stderr，不解析消息窗
    assert result["ok"], result["messages"][:3]
    client.save()
finally:
    client.close()
    service.stop()
```

## 现在能干什么（全部实测）

| 面 | 命令 |
| --- | --- |
| 会话 | `codesyskit start/status/stop`、token、超时、batch |
| 设备 | 1562 个设备描述，按名/厂商过滤 |
| 工程 | 新建（含 ST 程序 + 任务骨架）/打开/保存/关闭/信息/树 |
| 代码 | 建 POU/GVL/DUT/FB、读/写声明与实现、全文搜索（带行号） |
| 结构 | 改名 / 移动 / 删除 / 建文件夹（拒绝改工程根） |
| 编译 | `build` 与 `execute 重新编译`，判据都是引擎 stderr |
| IDE 命令 | **870 条**命令可枚举、可执行（name/guid/tokens） |
| 库 | **537** 个可用、引用了哪些、`add_library` 真的生效 |
| 交换 | PLCopenXML 导出 1–2 KB、原生导出 23 KB、整包归档 5.4 MB、运行时 m4 |
| 在线 | **仿真全通**：`online.simulation` → `login` → `start/stop` → 读写 → `monitor` 采样 → `logout`；真 PLC 走网关仍需可启动的网关 |

## 依赖顺序（错一步就静默失败）

```
profile 带引号 → 引擎无界面启动 → scriptengine 可用
→ device_repository(1562) → projects.create → project.add(name, device_id)
→ active_application → create_program(language=ST)
→ create_task_configuration → create_task → task.pous.add(POU)     ← 少了这行，编译是空转
→ build() → 诊断只在 stderr → Service.compile() 解析
→ save → close → projects.open 回读比对
```

详细推理与实测数字见内核 `docs/ARCHITECTURE.md`；协议与错误码见 `docs/PROTOCOL.md`。

## 能力清单

完整表格在下方生成块里；每条的"证据"列写明是哪个实测/测试支撑的。
未打通与已证伪的路径在 `capabilities.md` 末尾，别在客户工程上试。

## 配方与坑

- 配方（照抄的调用序列）：[`references/recipes.md`](references/recipes.md)
- API 全量目录（50 模块 / 262 类 / 1395 个 def）：内核 `docs/API-SURFACE.md`
  与 `recon/api_catalog.json`（由 `tools/api_inventory.py` 从 stub 生成，可复跑）
- 踩过的坑（含复现方式）：[`references/pitfalls.md`](references/pitfalls.md)
- 验收清单（交付前逐条打勾）：[`references/checklists.md`](references/checklists.md)

## 什么时候不要用这个技能

- 需要**在线**（登录、下载、监控）时：本技能只能到"离线编译通过"。
- 需要 COM/VBA 调用时：改用常驻服务（任何能发 TCP 的进程都能用）。
- 需要改客户桌面上的 GUI 时：不要。引擎已经无界面可脚本化。

<!-- allow:pending:BEGIN -->
- `online.real_plc`：真 PLC 走网关需要能启动网关服务（本机仅 SYSTEM/管理员可启动）；仿真路径已通；
- `com.register`：已证伪（没有可注册的引擎类），别再写注册表；
- `lib.manage` / `pkg.manage` / `trace.configure` / `archive.exchange`：API 存在但没有实测配方；
- `exec.arbitrary`：默认关闭，需要 `--allow-exec`。
<!-- allow:pending:END -->

## 自检

```powershell
python tools\check_skill.py --check     # 文档与快照一致、链接存在
python tools\sync_capabilities.py --check
python -m pytest tests -q
python tools\install_skill.py --check   # 是否已装到 ~/.agents/skills
```


<!-- gen:capabilities:BEGIN -->

| 能力 | 族 | 级别 | 证据 |
| --- | --- | --- | --- |
| `svc.start` | 常驻服务（进程/协议） | L2 | live_service：service.start 7.3 s，返回 ping 成功后的 state |
| `svc.stop` | 常驻服务（进程/协议） | L2 | live_service：quit 后 1.2 s 退出；残留 taskkill 兜底 |
| `svc.status` | 常驻服务（进程/协议） | L2 | cli：status 在无服务时退出码 2 |
| `svc.token` | 常驻服务（进程/协议） | L2 | live_service + test_client：错 token -> E_TOKEN，先于命令查找 |
| `svc.timeout` | 常驻服务（进程/协议） | L2 | test_client：0.5 s 超时对 3 s 慢命令 -> E_TIMEOUT 且提前返回 |
| `svc.batch` | 常驻服务（进程/协议） | L2 | live_service + test_client：逐条 ok/code，部分失败不丢 |
| `svc.errors` | 常驻服务（进程/协议） | L2 | errors.ALL 11 个码封闭集合，test_protocol 校验唯一性 |
| `svc.random_port` | 常驻服务（进程/协议） | L2 | port=0 由引擎选端口并写入 service.json（实测 64054 等） |
| `svc.one_request` | 常驻服务（进程/协议） | L2 | 一连接一请求：keep-alive 会饿死第二个客户端（实测 10 s 超时） |
| `svc.utf8` | 常驻服务（进程/协议） | L2 | live_surface：中文注释写入并逐字读回（修掉 Byte 溢出断连） |
| `dev.list` | 设备仓库 | L1 | live_service：get_all_devices 1562 条 |
| `dev.filter` | 设备仓库 | L1 | live_service：filter=CODESYS Control Win V3 命中 2 条 |
| `proj.create` | 工程 | L3 | live_service：project.create(+device+task) 3.6 s，返回 program/task 路径 |
| `proj.create_bare` | 工程 | L3 | project.create(bare=True) 只加设备，不建 POU/任务 |
| `proj.open` | 工程 | L3 | live_service：projects.open 重开同一工程 |
| `proj.save` | 工程 | L3 | live_service：save 后 dirty=False |
| `proj.close` | 工程 | L3 | live_service：close -> {closed: path} |
| `proj.info` | 工程 | L2 | live_service：application 路径为 /PLC/Plc Logic/Application |
| `proj.tree` | 工程 | L2 | tree 按 /A/B/C 行走 get_children，段不存在 -> E_STATE |
| `code.pou_create` | 程序与文本 | L3 | live_service：create_program(language=ImplementationLanguages.st) |
| `code.pou_read` | 程序与文本 | L2 | live_service：declaration 45 字符回读一致 |
| `code.pou_write` | 程序与文本 | L3 | live_service：replace(0,len,text) + readback_match=True |
| `code.tasks` | 程序与文本 | L3 | live_service：task.create/tasks，MainTask 20 ms 绑定 PLC_PRG |
| `obj.info` | 对象结构 | L2 | live_surface：object.info 返回 name/path/is_folder/has_textual_* /children |
| `obj.rename` | 对象结构 | L3 | live_surface：rename -> PLC_MAIN 后回读名字一致 |
| `obj.move` | 对象结构 | L3 | live_surface：move 进子文件夹再移回，路径随动 |
| `obj.delete` | 对象结构 | L3 | live_surface：删除空文件夹；改删/改移工程根会被拒 |
| `obj.folder_create` | 对象结构 | L3 | live_surface：create_folder 后路径由父路径+名字算出并回走校验 |
| `build.compile` | 编译与判据 | L4 | live_service：合法 ST -> 0 错误（Service.compile） |
| `build.diagnostics` | 编译与判据 | L4 | live_service：写坏代码 -> 12 错误 2 警告，码 C189/C139/C9/C190 |
| `build.restore` | 编译与判据 | L4 | live_service：改回合法代码 -> 重新 0 错误（可来回） |
| `build.task_required` | 编译与判据 | L4 | live_service：无任务配置的 bare 工程对同样乱码报 0 错误（假绿灯） |
| `build.readback` | 编译与判据 | L4 | live_service：close -> open -> 读 implementation 与写入一致 |
| `build.log_parse` | 编译与判据 | L4 | test_engine_log：解析编译完成 N错误,M警告 与 C 码，丢弃 Text 进度行 |
| `cmd.list` | IDE 命令通道 | L2 | live_surface：870 条命令，带 name/guid/description/tokens |
| `cmd.execute` | IDE 命令通道 | L4 | live_surface：execute 重新编译，用引擎 stderr 判据得到 0 错误 |
| `lib.list` | 库管理 | L2 | live_surface：4 条已引用 + 537 条可用 |
| `lib.add` | 库管理 | L3 | live_surface：add_library(Standard) 后引用表里出现 Standard |
| `xchg.export_xml` | 交换与归档 | L2 | live_surface：应用 1095 B / 设备子树 1988 B |
| `xchg.import_xml` | 交换与归档 | L3 | live_surface：设备子树导入空工程，children 2 -> 3 |
| `xchg.export_native` | 交换与归档 | L2 | live_surface：PLCopen 原生导出 23091 B |
| `xchg.archive` | 交换与归档 | L2 | live_surface：save_archive 5479773 B |
| `xchg.runtime` | 交换与归档 | L2 | live_surface：generate_runtime 产出 surfaceItf.m4 |
| `online.simulation` | 在线（网关/PLC） | L3 | live_online：set_simulation_mode(True) 后自动分配 SharedMemory 网关 + 地址 0000 |
| `online.login` | 在线（网关/PLC） | L3 | live_online：login+autostart -> logged_in=true / application_state=run |
| `online.read` | 在线（网关/PLC） | L2 | live_online：读 PLC_PRG.nCounter 得到 INT#8（随后增长到 68） |
| `online.write` | 在线（网关/PLC） | L3 | live_online：写 1000，读回 1007（写生效后被任务继续累加） |
| `online.monitor` | 在线（网关/PLC） | L2 | live_online：5×300ms 采样 1016/1036/1056/1076/1096 |
| `online.start_stop` | 在线（网关/PLC） | L3 | live_online：stop -> state=stop，start -> state=run |
| `online.download` | 在线（网关/PLC） | L3 | live_online：login(change=update)+create_boot_application 返回 True |
| `online.logout` | 在线（网关/PLC） | L2 | live_online：logout 后 logged_in=false |
| `online.failure_path` | 在线（网关/PLC） | L2 | live_online：关掉仿真后 login 诚实返回 E_CODESYS |
| `engine.headless` | 引擎行为（实测事实） | L2 | live_service：ui_present=False，全程无窗口 |
| `engine.profile_quoting` | 引擎行为（实测事实） | L2 | 实测：--profile 必须带字面引号，否则退出 1 并提示 --noUI 模式 |
| `engine.ironpython` | 引擎行为（实测事实） | L1 | sys.version = CODESYS.exe 3.5.22.20, ScriptEngine.plugin 4.2.0.0（IronPython 2.7） |
| `cli.verbs` | 命令行 | L2 | cli 冒烟：start/status/devices/call/stop，退出码 0/1/2/3/4 实测 |

<!-- 由 tools/sync_capabilities.py 生成，勿手改 -->
<!-- gen:capabilities:END -->
