# 验收清单（交付前逐条打勾）

## A. 会话层

- [ ] `codesyskit status` 返回 `running: true` 且带 `ping`
- [ ] `ping.ui_present` 是 `false`（说明真的无界面，不是偷偷开了窗口）
- [ ] 用的是随机端口（`--port 0`），`service.json` 里有 32 位 token
- [ ] 同一 `--state-dir` 只有一个服务；结束用 `codesyskit stop`，进程真的没了

## B. 工程结构

- [ ] `project.info` 的 `application.path` 是真实路径（含 `Plc Logic` 中间层）
- [ ] `tasks` 里至少一个任务，且 `pous` 含你要编译的程序
- [ ] **没有**用 `bare=True` 却指望编译（那就必然假绿灯）

## C. 代码文本

- [ ] `pou.write` 返回 `readback_match: true`
- [ ] 关掉再打开（`project.close` → `project.open`）后 `pou.read` 仍与写入一致
- [ ] 程序是用 `language="st"` 建的（或确认默认语言就是 ST）

## D. 编译判据（最关键）

- [ ] 合法代码：`service.compile()` 的 `errors == 0` 且 `messages == []`
- [ ] **做过负向对照**：故意写坏 → `errors > 0` 且至少一个 `C` 码
- [ ] 恢复合法代码后重新编译回到 `errors == 0`（能来回，不是一次性的）
- [ ] 用的是 `Service.compile()`，不是 `client.build()` 的返回值（后者恒 `None`）

## D2. 扩展面（用到才查）

- [ ] 用 `commands` 先列命令，再 `execute`；**判据仍看引擎 stderr**，不看返回值
- [ ] 中文文本走一轮回读（`(* 中文 *)` 写入 → 读回逐字相等）
- [ ] 改结构后用**返回的新路径**继续，不复用旧路径
- [ ] 导出的文件 `size > 0`；`import.xml` 只在**空工程**上可靠
- [ ] `online.*` 之前确认 `online.state` 与网关状态；无网关时不要把它当成功

## D3. 在线（仿真即可）

- [ ] `online_simulation(True)` 后 `gateway` 不再是 `00000000-…`、`address` 有值
- [ ] 登录后 `application_state == "run"`（不是只看 `logged_in`）
- [ ] **读两次**同一变量，第二次更大（证明周期任务在跑）
- [ ] 写完立刻读回，值符合预期（注意任务还会继续改它）
- [ ] `monitor` 的采样数 = 请求数，且值随时间变化
- [ ] 退出前 `logout()` + `simulation(False)`，别把设备留在仿真态

## D4. 无 PLC 时还能挖的（都已验证）

- [ ] 建对象用 `pou.create_typed`（program/function/fb/gvl/dut/interface），成员用 `pou.member`
- [ ] 建完**必须编译**：0 错误才算真建成（模板写错照样能"创建成功"）
- [ ] 符号配置用 `symbols.create`；一个应用只能有一个
- [ ] 任务参数传字符串；动看门狗必须同时给时间
- [ ] 出编译库前先写 `project.meta`，**company 不能空**
- [ ] `save_as` 判据看文件 + `is_primary`，别被"正被使用"的报错误导
- [ ] 声称"执行成功"的 GUI 命令要查产物，没产物就是没做

## E. 交付物

- [ ] `project.save()` 后 `dirty: false`
- [ ] 工程文件在盘上（`.project` 有大小，不是 0 字节）
- [ ] 需要给别人的话：只给 `.project`，不含 `service.json`（那是凭据）

## F. 收尾

- [ ] `client.close()` 后 `service.stop()`，`taskkill` 兜底没被触发
- [ ] `codesyskit stop` 后 `status` 退出码是 2（说明确实没了）
- [ ] 没有在客户工程目录里留下 `_runs/`、日志或临时脚本

## G. 不该做的事（出现任意一条就停下）

- [ ] 没有写注册表 / 没有尝试注册 COM
- [ ] 没有在 `exec` 里跑"临时试一下"的代码（除非明确 `--allow-exec`）
- [ ] 没有两个 live 测试并行跑
- [ ] 没有把 `service.json`、`engine.stderr.log` 提交进仓库
