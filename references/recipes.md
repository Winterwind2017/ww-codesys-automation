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


## 14. 在线：登录 / 下载 / 监控（用仿真，不需要网关、不需要管理员）

```python
client.online_simulation(True)                 # 设备对象自带仿真开关，网关自动分配
client.online_login(autostart=True)            # logged_in / application_state=run
client.online_read("PLC_PRG.nCounter")         # "INT#8"
client.online_write("PLC_PRG.nCounter", "1000")
client.online_monitor(expression="PLC_PRG.nCounter", samples=5, interval_ms=300)
# [{...'INT#1016'}, 1036, 1056, 1076, 1096]  <- 周期任务在跑
client.online_stop(); client.online_start()
client.online_download()                        # login(update) + create_boot_application
client.online_logout(); client.online_simulation(False)
```

判据（三条都要）：① 读两次同一个变量，第二次**变大**（任务真在跑）；② 写 1000 读回 ≥1000；
③ `stop` 后 `application_state == "stop"`。只看 `logged_in` 会漏掉"登录了但程序没跑"。

真 PLC 的话把 `simulation=False`，并在设备通信设置里指向一个**已启动**的网关：
`device.set_gateway_and_address(<网关 guid>, "192.168.1.10")`（IP 会被规范成 `0127.0000.0000.0001` 这种形式）。


## 15. 建一整套 IEC 对象（无 PLC 也行）

```python
app = "/PLC/Plc Logic/Application"
client.create_typed("gvl", "GVL", text="VAR_GLOBAL\n\tnGlobal : INT;\nEND_VAR\n")
client.create_typed("dut", "ST_Data", text="TYPE ST_Data :\nSTRUCT\n\tnX : INT;\nEND_STRUCT\nEND_TYPE\n")
client.create_typed("interface", "I_Run")
fb = client.create_typed("function_block", "FB_Motor",
                         text="FUNCTION_BLOCK FB_Motor\nVAR_INPUT\n\tbStart : BOOL;\nEND_VAR\n")
client.add_member(fb["path"], "method", "Start", return_type="BOOL", text="bRun := bStart;\n")
client.add_member(fb["path"], "property", "Speed", return_type="INT")
client.add_member(fb["path"], "action", "Reset")
client.create_typed("function", "F_Add", return_type="INT")
assert client.members(fb["path"])["count"] == 3
service.compile(client)          # 判据：0 错误（实测通过）
```

## 16. 符号配置 / 文本表 / 任务参数

```python
client.symbols_create(export_comments=True)      # 内部用 Guid.Empty 作为 layout calculator
client.symbols_info("/PLC/Plc Logic/Application/Symbols")   # build 后：138 datatypes / 69 signatures

client.textlist_create("Texts", languages=["zh-CN", "en"])
client.textlist_languages("/PLC/Plc Logic/Application/Texts", add="fr")
client.textlist_export("/PLC/Plc Logic/Application/Texts", r"D:\work\texts.xml")

client.task_update("/PLC/Plc Logic/Application/Task Configuration/MainTask",
                   priority="20", interval="10")   # 只能传字符串
```

## 17. 工程元数据 → 编译库 → 另存

```python
client.project_meta(title="DemoKit", version="1.0.0.0", company="Winterwind")   # company 必须有
lib = client.export_library(r"D:\work\DemoKit.compiled-library")               # 4308 B
saved = client.save_as(r"D:\work\job_copy.project")   # 副本成为 primary
assert saved["is_primary"] and saved["size"] > 0       # 别信引擎那句『正由…使用』
client.io_export(r"D:\work\io.csv")                  # I/O 映射 CSV
client.project_integrity(enable=True)
client.project_users()                                # 只读；创建会被 (nobody) 拒
```
