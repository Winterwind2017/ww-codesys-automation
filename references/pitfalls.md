# 踩过的坑（都带复现方式）

## 1. 没有任务配置的工程，编译永远"0 错误"

**现象**

```
编译: Text: C0: ------ 开始构建应用程序 PLC.Application -------
编译: Text: C0: 代码典型化...
编译: Text: C0: 编译完成 -- 0错误,0警告
```

即使 POU 的实现里写着 `THIS IS NOT ST !!!`。

**复现**：`client.create(path, device=..., bare=True)` → `create_pou("PLC_PRG")` →
`client.write(pou, "THIS IS NOT ST !!!\n", "implementation")` → `service.compile(client)`，
得到 `errors=0`、`messages=[]`。

**原因**：编译从任务配置出发；POU 没被任何任务调用 ⇒ 没有对象被编译 ⇒ "0 错误"是空转。

**修法**：`application.create_task_configuration()` → `create_task("MainTask")` →
`task.pous.add("PLC_PRG")`。同样代码立刻变成 `12错误,2警告`（`C189/C139/C9/C190`）。
内核的 `project.create(device=…)` 默认就建这套骨架；`bare=True` 才给你裸工程。

## 2. 编译诊断不在消息存储里

**现象**：编译器明明报了 12 个错误，`system.get_messages()`、`get_message_objects()`、
`get_messages(<category Guid>)` 全是 0 条。

**原因**：诊断走进程 **stderr**。

**修法**：由**宿主**接管子进程的 stderr（`Service` 把它落到 `engine.stderr.log`），
`build()` 前后切片、解析：

```
编译: Error: C189: 应该用';' 替换'IS'
编译: Text: C0: 编译完成--12错误,2警告        ← 计数以这行为准
```

`Text:` 行是进度噪声，丢掉。`Service.compile()` 已封装，别自己再写一遍。

## 3. `create_program(name)` 的默认语言不是 ST

**现象**：文本写进去了、回读也对，编译却完全不提这段代码（有时甚至 0 错误）。

**原因**：默认实现语言由设备/profile 决定，可能不是 ST；`textual_implementation`
对一个非 ST 对象是"自由文本"，不参与编译。

**修法**：显式传语言 GUID：

```python
application.create_program("PLC_PRG", language=scriptengine.ImplementationLanguages.st)
```

`language` 取值：`st / cfc / page_oriented_cfc / fbd / ld / il / sfc`。

## 4. `doc.text` 只读；`remove` 的参数是 `(offset, length)`

**现象**：`doc.text = "..."` → `can't assign to read-only property of type 'ScriptTextDocument'`。

**修法**：`doc.replace(0, doc.length, text)`（一步），或 `doc.remove(0, doc.length)` +
`doc.append(text)`。

**坑中坑**：`doc.remove(length, 0)` 是"在 offset=length 处删 0 个字符"，等于**没删**；
接着 `append` 就得到 **旧文本 + 新文本**，而编译仍然 0 错误（因为语法可能刚好合法）。
判据：写完必须比较 `document.text == 写入文本`（`pou.write` 返回 `readback_match`）。

## 5. `--profile` 必须带字面引号

**现象**：进程 1.6 s 退出，退出码 1，stderr：

```
启动参数 --noUI 模式, 请使用 --profile="profile name" 指定配置文件.
```

**原因**：`subprocess.Popen([...])` 会重新加引号/转义，引擎拿不到引号。

**修法**：用**单条命令字符串**：

```python
'"%s" --profile="%s" --noUI --runscript="%s"' % (exe, profile, script)
```

## 6. `print()` 会污染 IDE 消息列表

`--noUI` 下 `print` 被塞进 `system.get_messages()`，于是"编译消息"和"你的调试输出"混在一起。
服务端因此**一行 print 都没有**（`tools/selfcheck.py` 会检查这一条）。

## 7. 脚本不退出，进程就挂着

脚本引擎不会自己结束；生成的 server 脚本以 `SYSTEM.exit(0)` 收尾，一次性脚本也必须自己写。

## 8. IronPython 2.7 的四个具体差异

| 写法 | 结果 |
| --- | --- |
| `os.makedirs(p, exist_ok=True)` | `TypeError: unexpected keyword` |
| `f"..."` | 语法错误 |
| `socket.Accept()` 解包成 `(conn, addr)` | `TypeError: 'Socket' object is not iterable`（返回**单个** Socket） |
| `open(p, "w")` 写中文 | `UnicodeEncodeError`；用 `codecs.open(p, "w", "utf-8")` |

## 9. 一连接一请求是故意的

脚本引擎单线程。若服务端在一条连接上 keep-alive 循环读，**第二个客户端会被饿死**
（实测：第一个客户端空闲占着连接时，第二个客户端等 10 s 超时）。
所以服务端"读一行、答一行、关连接"；客户端每次调用新建连接（loopback 约 1 ms）。

## 10. COM 是死路（别再试了）

- `RegAsm /regfile` 干跑 `ScriptEngine3.dll`：只产生 **3 个 coclass**，全是
  `…HideFromScriptDocuAttribute`、`…IncludeIntoScriptDocuAttribute`、`…SyntaxErrorException`；
  没有引擎类，也没有 `IScriptEngine` 的 CLSID。
- `HKCR` / `HKLM\SOFTWARE\Classes` / `HKCU\SOFTWARE\Classes` 里 `_3S.CoDeSys*` **0 命中**。
- `ScriptEngine3.dll` 引用 25 个程序集（24 个是 CODESYS 自己的），且是 **x86**。
  就算有类，InprocServer32 也是"把半个 IDE 装进你的进程"，还看不到界面里打开的工程。

结论：**用常驻服务**（loopback JSON），别写注册表。

## 11. 端口与并发

- `--port 0` 让引擎自选端口并写入 `service.json`，多开互不冲突；
- 同一 `--state-dir` 只能有一个服务（第二个 `start` 报 `E_STATE`）；
- 引擎单线程，慢命令（`build`）会阻塞后续请求，客户端超时要按最慢命令配。


## 12. 中文回复会把连接打断（已修，但要知道）

**现象**：任何含中文的回复到达客户端前，服务端日志出现
`connection error: Cannot convert int(36333) to Byte`，客户端只看到
`E_PROTOCOL: service closed the connection`。

**原因**：回复按字符码逐字节写进 `Byte[]`（`ord('中')=20013 > 255`），请求也是按字符拼的。

**修法**：`Encoding.UTF8.GetBytes(text)` + 循环 `Send`；请求按字节累积后 `.decode("utf-8")`。
判据：把 `(* 中文注释 *)` 写进 POU 再读回，必须逐字相等。

## 13. 路径不能靠"对象是不是同一个"来判断

**现象**：`mkdir` 返回 `{"path": "/"}`，接着 `move(pou, "/")` 把 POU 搬到了工程根；
`delete("/")` 又去删工程根，报 `'ScriptProject' object has no attribute 'remove'`。

**原因**：引擎每次调用都返回新的 wrapper 对象，`node is project` 永远为假；而 `create_folder`
返回的对象**还没有名字**，`path_of` 立刻就在第一步 break 成 `/`。

**修法**：路径只按**名字**沿 parent 链构建，遇到**无名的工程根**停下；`create_folder` 的路径
由「父路径 + 名字」算出来再回走校验；改名/删除/移动**拒绝**解析到工程根。
改动后 `live_surface` 的 move/rename/delete 往返用例一次通过。

## 14. `Socket.Send` 不保证一次发完

大回复（870 条命令的列表）会被截断，客户端永远等不到换行。必须
`while sent < total: sent += sock.Send(buf, sent, total - sent, flags)`。


## 15. 每次读都重新登录 = 每次都在下载（值全归零）

**现象**：login 成功、`application_state=run`，但连着读两次 `nCounter` 都是 `0`，看起来"任务没跑"。

**原因**：`create_online_application()` + `login()` 不是"连接"那么简单——应用有变化时它就是一次
**增量下载**，程序重启、变量回到初值。我的第一版每条命令都重新建会话，于是每次读都把计数器清零。

**修法**：每个工程只建**一个** `OnlineApplication` 并缓存，只在 `is_logged_in` 为假时才登录
（内核里是 `ONLINE` 字典）。修好后 1.2 s 内 `8 -> 68`。

## 16. `set_prepared_value` 只收字符串

`online_app.set_prepared_value("PLC_PRG.nCounter", 42)` → `TypeError: expected str, got int`。
传 `"42"` 即可；内核的 `online.write` 统一 `unicode(value)`。

## 17. 网关服务：不是"没装"，是"没权限启"

`CODESYS Gateway V3` / `CODESYS Control Win V3 - x64` 都是 `Manual` 服务，`sc start` 报
`Access is denied`（服务 DACL 里 `IU` 只有 `CCLCSWLOCRRC`，没有启动权）；直接把
`GatewayService.exe` 当普通进程跑会立刻退出（它要先 `StartServiceCtrlDispatcher`）。
**所以不要在这条路上耗**：用 `device.set_simulation_mode(True)` 的仿真路径，
登录/下载/读写/监控全都能跑，而且不需要任何提权。


## 18. 模板被"切片拼接"复制三份，新改动被旧副本覆盖

**现象**：明明改了 `cmd_project_save_as`，服务跑起来还是老行为（`E_SCRIPT` + 旧的那句
『所选工程当前正由…使用』），日志里指向 `server.py` 第 3088 行；而源文件里那段在 1264 行。

**原因**：用 `s[:start] + NEW + s[end:]` 改模板时，`end` 取到的是**在前面的** `def cmd_build`，于是
`s[end:]` 把整段又接了一遍 —— 模板长成 3584 行 / 159 个 `def` / 45 个重名，后定义覆盖前定义。

**修法**：从干净基线（`git show <commit>:agentscript.py`）重建，并在 `selfcheck` 加硬门禁
「禁止重复 `cmd_*` 定义」（现在 1778 行 / 69 命令 / 0 重名）。**教训：改长模板后必须查重名。**

## 19. `save_as` 成功但会报"工程正被使用"

`project.save_as(path)` 实际**已经**生成副本并把当前工程改名到新路径，紧接着去
`PROJECTS.open(新路径)` 或访问 `projects.primary` 会抛
`所选工程当前正由'<user>'上的'<machine>'使用`（残留 claim 文件 `.~u`/`.opt`）。
判据应改成：**文件存在 + 大小 > 0 + `project.path` 已等于新路径**，而不是看有没有异常。

## 20. 有些命令"执行成功"但什么都没做（GUI-only）

`导出IEC61131-10...`、`导出OPC UANodeSet`、`计算并导出标准指标`、`目标设置文档导出`
在 `--noUI` 下 `execute` 返回正常，**既不写文件也不产生消息**——它们要弹文件对话框。
所以 `execute` 的返回值永远不能当判据，必须看产物（文件/大小/编译日志/回读值）。

## 21. 任务参数只收字符串；看门狗没时间会编译失败

`task.priority = 20` → `TypeError: expected str, got int`；`"20"` 可以。
只把 `watchdog.enabled` 打开、不设 `watchdog.time`，编译直接报 `MainTask: 无效的看门狗时间`。
