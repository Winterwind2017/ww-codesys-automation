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
