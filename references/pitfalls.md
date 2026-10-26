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
