# 能力清单（快照）

由 `tools/sync_capabilities.py` 从内核生成；出处 `codesyskit@86896f4`。

## 已打通（49）

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
| `build.compile` | 编译与判据 | L4 | live_service：合法 ST -> 0 错误（Service.compile） |
| `build.diagnostics` | 编译与判据 | L4 | live_service：写坏代码 -> 12 错误 2 警告，码 C189/C139/C9/C190 |
| `build.restore` | 编译与判据 | L4 | live_service：改回合法代码 -> 重新 0 错误（可来回） |
| `build.task_required` | 编译与判据 | L4 | live_service：无任务配置的 bare 工程对同样乱码报 0 错误（假绿灯） |
| `build.readback` | 编译与判据 | L4 | live_service：close -> open -> 读 implementation 与写入一致 |
| `build.log_parse` | 编译与判据 | L4 | test_engine_log：解析编译完成 N错误,M警告 与 C 码，丢弃 Text 进度行 |
| `obj.info` | 对象结构 | L2 | live_surface：object.info 返回 name/path/is_folder/has_textual_* /children |
| `obj.rename` | 对象结构 | L3 | live_surface：rename -> PLC_MAIN 后回读名字一致 |
| `obj.move` | 对象结构 | L3 | live_surface：move 进子文件夹再移回，路径随动 |
| `obj.delete` | 对象结构 | L3 | live_surface：删除空文件夹；改删/改移工程根会被拒 |
| `obj.folder_create` | 对象结构 | L3 | live_surface：create_folder 后路径由父路径+名字算出并回走校验 |
| `cmd.list` | IDE 命令通道 | L2 | live_surface：870 条命令，带 name/guid/description/tokens |
| `cmd.execute` | IDE 命令通道 | L4 | live_surface：execute 重新编译，用引擎 stderr 判据得到 0 错误 |
| `lib.list` | 库管理 | L2 | live_surface：4 条已引用 + 537 条可用 |
| `lib.add` | 库管理 | L3 | live_surface：add_library(Standard) 后引用表里出现 Standard |
| `xchg.export_xml` | 交换与归档 | L2 | live_surface：应用 1095 B / 设备子树 1988 B |
| `xchg.import_xml` | 交换与归档 | L3 | live_surface：设备子树导入空工程，children 2 -> 3 |
| `xchg.export_native` | 交换与归档 | L2 | live_surface：PLCopen 原生导出 23091 B |
| `xchg.archive` | 交换与归档 | L2 | live_surface：save_archive 5479773 B |
| `xchg.runtime` | 交换与归档 | L2 | live_surface：generate_runtime 产出 surfaceItf.m4 |
| `online.state` | 在线（网关/PLC） | L2 | live_surface：无目标时 logged_in=false / state=none |
| `online.failure_path` | 在线（网关/PLC） | L2 | live_surface：online.login 返回引擎原文 E_CODESYS（网关未配置） |
| `engine.headless` | 引擎行为（实测事实） | L2 | live_service：ui_present=False，全程无窗口 |
| `engine.profile_quoting` | 引擎行为（实测事实） | L2 | 实测：--profile 必须带字面引号，否则退出 1 并提示 --noUI 模式 |
| `engine.ironpython` | 引擎行为（实测事实） | L1 | sys.version = CODESYS.exe 3.5.22.20, ScriptEngine.plugin 4.2.0.0（IronPython 2.7） |
| `cli.verbs` | 命令行 | L2 | cli 冒烟：start/status/devices/call/stop，退出码 0/1/2/3/4 实测 |

## 未打通 / 已证伪（9）

- `online.login` — ScriptOnline 19 类 112 方法，但需要可达的 PLC 或本地软 PLC，未实测
- `online.download` — 下载/RUN-STOP 同理，需要目标 PLC
- `monitor.live` — 在线读变量需要登录成功后才有值
- `lib.manage` — LibManager 74 方法未验证；客户工程的库版本是单独问题
- `pkg.manage` — PackageManagerCLI/IPMCLI 可跑但未验证装包对设备仓库的影响
- `trace.configure` — ScriptTraceObject/可视化资源存在，没有实测配方
- `archive.exchange` — save_archive/export_xml/import_xml 未实测
- `com.register` — 已证伪：ScriptEngine3.dll 只有 3 个 attribute/exception 类可注册，_3S.CoDeSys* 注册表 0 命中
- `exec.arbitrary` — exec 命令在引擎内跑任意 IronPython，默认关闭，需 --allow-exec
