# 配方（照抄就能跑）

所有配方都以"服务已 `start`"为前提。每条都给出**判据**，没有判据的步骤不要当成功。

## 1. 起一个可编译的工程（90% 的场景）

```python
project = client.create(r"D:\work\job.project", device="CODESYS Control Win V3")
# -> {"path": ..., "device": "CODESYS Control Win V3",
#     "program": "/PLC/Plc Logic/Application/PLC_PRG",
#     "task": "MainTask", "language": "st"}
```

判据：`client.call("tasks")` 里 `MainTask` 的 `pous` 含 `PLC_PRG`。
没有这条，后面的编译永远是假绿灯。

只想拿一个裸工程（自己搭 POU/任务）：

```python
client.create(path, device="CODESYS Control Win V3", bare=True)
```

## 2. 写 ST 并让它真的进编译

```python
pou = client.create_pou("FB_Axis", kind="function_block", language="st")["path"]
client.write(pou, "FUNCTION_BLOCK FB_Axis\nVAR\n\txEnable : BOOL;\nEND_VAR\n", "declaration")
client.write(pou, "IF xEnable THEN\n\tnCount := nCount + 1;\nEND_IF\n", "implementation")
```

`language="st"` 不能省：默认语言不是 ST，文本会被写进一个不参与编译的文档。

判据：`client.read(pou, "implementation")["text"]` 与写入逐字相等。

## 3. 编译并用负向对照确认

```python
clean = service.compile(client)          # {"ok": True, "errors": 0, ...}

# 负向对照：写坏，必须报错；不报错说明任务没绑上
client.write(pou, "THIS IS NOT ST !!!\n", "implementation")
broken = service.compile(client)
assert broken["errors"] > 0 and broken["codes" if False else "messages"]
client.write(pou, good_text, "implementation")
assert service.compile(client)["ok"]
```

真编译时 `broken["messages"]` 长得像：

```json
{"category": "编译", "severity": "Error",    "code": "C189", "text": "应该用';' 替换'IS'"}
{"category": "编译", "severity": "Warning",  "code": "C139", "text": "代码'THIS;\\n'不可能执行到.这是有目的的吗？"}
```

## 4. 改已有 POU（不新建任务）

```python
client.open(r"D:\work\job.project")
pou = "/PLC/Plc Logic/Application/PLC_PRG"
text = client.read(pou, "implementation")["text"]
client.write(pou, text.replace("nCounter := nCounter + 1;", "nCounter := nCounter + 2;"),
             "implementation")
assert service.compile(client)["ok"]
client.save()
```

路径有 `Plc Logic` 中间层；段名写错返回 `E_STATE`，先 `client.info()` / `client.tree()` 再写。

## 5. 批量动作（省启动时间、保原子性）

```python
client.batch([
    {"cmd": "ping"},
    {"cmd": "pou.create", "args": {"name": "PRG_A", "kind": "program", "language": "st"}},
    {"cmd": "pou.write",  "args": {"path": "/PLC/Plc Logic/Application/PRG_A",
                                   "part": "implementation", "text": "nX := 1;\n"}},
    {"cmd": "task.create", "args": {"name": "MainTask", "pous": ["PRG_A"]}},
], stop_on_error=True)
```

判据：`results` 里每条都有自己的 `ok/code`；`stop_on_error=True` 时后续条目不执行。

## 6. 一次性脚本（不想常驻）

```powershell
codesyskit run my_script.py      # 用 --runscript 跑完就退（实测 6.15 s/次）
```

脚本里必须 `import scriptengine` … `scriptengine.system.exit(0)`，
写文件用 `codecs.open(..., "w", "utf-8")`，**不要 print**。

## 7. 换个版本的 CODESYS / 换 profile

```powershell
codesyskit --exe "D:\...\CODESYS.exe" --profile "CODESYS V3.5 SP22 Patch 2" start
```

环境变量也行：`CODESYSKIT_EXE`、`CODESYSKIT_PROFILE`。
profile 名字要给**真实存在**的那一份（`CODESYS\Profiles\*.profile.xml`）。

## 8. 把服务当 API 给别的进程用

```powershell
codesyskit status --state-dir D:\shared\codesys   # 端口与 token 在 service.json
```

别的语言直接按 `docs/PROTOCOL.md` 发一行 JSON 即可（token 在同一文件里）。
`service.json` 就是凭据，按密钥对待。


## 9. 跑一条 IDE 命令（GUI 能做的都能做）

```python
listing = client.commands(filter="下载", limit=10)      # 先看名字与 tokens
result = service.run_command(client, "重新编译")        # 用引擎 stderr 判据
assert result["errors"] == 0, result["messages"][:3]
client.execute(guid="50dc8f97-9e21-4b15-a504-ea2549ab61e0")   # 名字会随语言变，guid 稳
```

命令名是本地化的（这台是中文）；要跨语言稳，用 `guid` 或 `tokens`。

## 10. 全文搜索

```python
hits = client.find("nCounter", limit=50)
# {"count": 3, "items": [{"path": "/PLC/Plc Logic/Application/PLC_PRG",
#                         "part": "declaration", "line": 3, "text": "\tnCounter : INT;"}]}
```

搜索范围是对象的声明/实现文本（不是文件系统）；`part` 可选 `declaration`/`implementation`。

## 11. 改对象结构（改名/移动/删除/建文件夹）

```python
folder = client.mkdir("Records", "/PLC/Plc Logic/Application")["path"]
moved = client.move(pou, folder, -1)["path"]        # 用返回的新路径继续
client.rename(moved, "PRG_Records")
client.delete(folder)                              # 空文件夹
```

每次都**用返回值里的 path**，不要复用旧路径（对象位置变了）。工程根不可改名/删除/移动。

## 12. 库

```python
libs = client.libraries()        # {"referenced": [...4], "available_count": 537}
client.add_library("Standard")   # 立刻出现在 referenced 里
```

## 13. 交换：XML / 原生 / 归档 / 运行时文件

```python
client.export_xml(r"D:\work\app.xml")                       # 默认导出活动应用
client.export_xml(r"D:\work\plc.xml", target="/PLC")        # 导出设备子树
client.export_native(r"D:\work\app.plcopen")                # PLCopen 原生
client.archive(r"D:\work\job.projectarchive")               # 整包（几 MB）
client.generate_runtime(r"D:\work\rtsys")                   # 产出 *.m4
client.import_xml(r"D:\work\plc.xml")                       # 只对空工程可靠
```

判据：文件存在且 `size > 0`；`import.xml` 看 `children_after > children_before`。
