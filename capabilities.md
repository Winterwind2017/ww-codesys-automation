# 能力清单（快照）

由 `tools/sync_capabilities.py` 从内核生成；出处 `codesyskit@9a10093`。

## 已打通（71）

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
| `obj.model` | 对象结构 | L3 | live_deep：GVL/DUT/interface/FB/function 全建成功，建完 0 错误 |
| `obj.members` | 对象结构 | L3 | live_deep：FB 下建 method/property/action，pou.members 回读 3 个 |
| `obj.member_text` | 对象结构 | L2 | live_deep：方法实现体写入后参与编译且 0 错误 |
| `sym.config` | 对象结构 | L3 | live_deep：symbols.create -> create_symbol_config(comments, opc_ua, Guid.Empty)；build 后 138 datatypes / 69 signatures |
| `i18n.textlist` | 对象结构 | L2 | live_deep：textlist.create(zh-CN,en) + add fr -> 3 种语言；export 238 B |
| `proj.meta` | 工程 | L2 | live_deep：title/company/version 写入并可回读 |
| `proj.library` | 工程 | L3 | live_deep：project.meta + export_library -> 4308 B 编译库（缺 company 会被拒） |
| `proj.save_as` | 工程 | L3 | live_deep：副本变 primary，用文件+改名路径判据（引擎会报『正由…使用』但副本已完整） |
| `proj.users` | 工程 | L2 | live_deep：列出 Owner/Everyone；创建被 (nobody) 权限拒绝（诚实报 refused） |
| `proj.integrity` | 工程 | L2 | live_deep：enable_integrity_check 后 false -> true |
| `proj.iomap` | 工程 | L2 | live_deep：导出 I/O 映射 CSV 235 B |
| `app.lifecycle` | 编译与判据 | L3 | live_deep：app.clean -> is_uptodate false；app.generate -> true；is_online_change_possible true |
| `task.timing` | 编译与判据 | L3 | live_deep：task.update priority 1->20、interval 20->10ms（值必须传字符串） |
| `cmd.map` | IDE 命令通道 | L2 | docs/COMMANDS.md：832 条唯一命令 / 90 族，recon/commands.json 可复跑 |
| `online.force` | 在线（网关/PLC） | L3 | live_deep：仿真里把 nCounter 钉在 777；unforce 后 790->888 |
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

## 未打通 / 已证伪（11）

- `compare.projects` — project.compare 实测死路：compare_to 需要第二个工程对象，且同进程只能有一个 primary
- `gui_only_export` — 导出IEC61131-10 / 导出OPC UANodeSet / 计算并导出标准指标 / 目标设置文档导出：execute 返回正常但既无文件也无消息（弹对话框），headless 不可用
- `online.real_plc` — 真 PLC 走网关：Gateway/软 PLC 是 Manual 服务，仅 SYSTEM/管理员可启动（sc start -> Access denied，DACL 里 IU 无启动权）；仿真路径已全通
- `doc.export` — project.export_doc 在 --noUI 下静默不写文件（实测），命令直接回 E_UNAVAILABLE
- `symbol.create` — 本版本 application/device 都没有 create_symbol_configuration（实测 AttributeError）
- `lib.export_compiled` — save_as_compiled_library 需要工程信息（实测『未发现工程信息』）
- `lib.manage` — LibManager 74 方法未全验证；客户工程的库版本是单独问题
- `pkg.manage` — PackageManagerCLI/IPMCLI 可跑但未验证装包对设备仓库的影响
- `trace.configure` — ScriptTraceObject/可视化资源存在，没有实测配方
- `com.register` — 已证伪：ScriptEngine3.dll 只有 3 个 attribute/exception 类可注册，_3S.CoDeSys* 注册表 0 命中
- `exec.arbitrary` — exec 命令在引擎内跑任意 IronPython，默认关闭，需 --allow-exec
