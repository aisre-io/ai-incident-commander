# Lark 端到端验证 — Checklist

> **状态**: ✅ 已完成（2026-06-05 12:24）
> **最终结果**: 飞书群收到 critical 红色 incident 卡片，含 Root Cause / Fix Suggestion / Evidence
> **过程中发现并修复**: `lark_bot.py` URL 拼接 bug（用户填完整 URL 时 httpx 收到畸形 URL 静默失败）

---

## 前置条件

- [x] `.env` 里 `DEEPSEEK_API_KEY` 已配置
- [x] Python 3.12 venv + 依赖已装
- [x] 飞书建好测试群（如 "AI Incident 验证"）
- [x] 群机器人 → 自定义机器人 → 复制 webhook URL

---

## 步骤

### 1. 配 .env

```env
NOTIFIER_TYPE=lark
LARK_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的-token
LARK_REGION=cn   # 国内 cn / 海外 intl
```

> ⚠️ **`LARK_WEBHOOK_URL` 接受两种格式**（已修复兼容）：
> - 完整 URL：`https://open.feishu.cn/open-apis/bot/v2/hook/abc-xyz` ✅ 推荐（飞书 UI 复制的格式）
> - Bare token：`abc-xyz` ✅（程序拼接 base URL）

### 2. 一键启动 + 验证 + 触发

**单窗口（推荐）**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restart_and_test.ps1
```

这个脚本会:
1. 杀掉端口 8000 上的旧 server
2. 清空 `out/server.log` / `out/server.err.log`
3. 后台启动新 uvicorn（带日志重定向）
4. 等 4 秒 → curl `/health`
5. 触发 `simulation/send_test_incident.py`（POST 到 `/webhook/pagerduty`）
6. 拉 server stdout + stderr 最后 30 行

### 3. 飞书群验证

5-15 秒后应该看到一张卡片:
- **红色头部**（critical severity）
- 标题：`Incident Report: [P0 验证] AI Incident Commander E2E Test`
- Service / Severity / Alert Count / Confidence 字段
- Root Cause 段
- Fix Suggestion 段
- Evidence 段

截图保存到 `outreach/screenshots/lark-e2e-success.png`（用于 outreach 素材 + 第 1 篇 postmortem）。

---

## 失败排查

| 症状 | 排查 |
|---|---|
| `curl /health` 失败 | 端口 8000 被占 → `Get-NetTCPConnection -LocalPort 8000` 找进程杀 |
| Server 启动后立刻崩 | 看 `out/server.err.log`（常见：缺依赖、Python 版本不匹配）|
| `POST /webhook/pagerduty` 404 | 检查 `app/api/webhook.py:8` 路由 prefix，应为 `/webhook`（不是 `/api/webhook`）|
| 200 OK 但飞书无卡片 | 跑 `scripts/diagnose_lark.ps1` — 4 步隔离 |
| 飞书 401 / 失效 | Webhook URL 错/机器人被禁 → 重新创建机器人复制 URL |

### 关键诊断脚本

```powershell
# 4 步隔离问题（直连 → server 触发 → stdout → stderr）
powershell -ExecutionPolicy Bypass -File scripts\diagnose_lark.ps1
```

- **Test 1 直连成功 + Test 2 失败** → server 端 notifier 链路有问题
- **Test 1 直连就失败** → Lark webhook URL 本身无效
- **Test 2 server 200 + 无卡片** → 历史上 100% 是 `lark_bot.py` URL 拼接 bug

---

## 已踩过的坑（避坑指南）

### 🐛 Bug #1: Lark URL 拼接（已修）

**位置**: `app/integrations/lark_bot.py:44`（修复前）

**症状**: Server 200 OK，飞书群无卡片，`server.err.log` 没有 `Notifier failed` 错误

**根因**: 代码假设 `LARK_WEBHOOK_URL` 是 bare token，拼 base URL；但用户在 .env 填的是飞书 UI 复制的完整 URL，结果 httpx 收到：
```
https://open.feishu.cn/open-apis/bot/v2/hook/https://open.feishu.cn/open-apis/bot/v2/hook/51b2a635-...
```
畸形 URL，httpx 抛 `RequestError`，被 `webhook.py:67` 的 `try/except Exception` 静默吞掉

**修复**:
- `lark_bot.py` 新增 `_resolve_webhook_url(base, raw)`：检测 `http(s)://` 前缀自动原样使用
- 加 `logger.debug(f"Lark POST -> {url}")` 让发出去的 URL 可见
- `webhook.py` 的 notifier 错误日志保留（但 P2 要重构：通知失败要发到监控/告警，不只 log）

### 🐛 Bug #2: send_test_incident.py 默认路径错（已修）

**位置**: `simulation/send_test_incident.py`

**症状**: HTTP 404 `{"detail": "Not Found"}`

**根因**: 默认 `--path /api/webhook/pagerduty`，但 `app/api/webhook.py:8` 的 prefix 是 `/webhook`（不是 `/api/webhook`）

**修复**: 默认路径改为 `/webhook/pagerduty`

### 🐛 Bug #3: 后台 server 看不见状态（已修）

**症状**: `Start-Process` 后不知道 server 起没起来，日志看不到

**根因**: PowerShell `Start-Process -NoNewWindow` 不直接输出，要 redirect

**修复**:
- `out/` 目录必须先建（已写进 `start_server.ps1`）
- `RedirectStandardOutput` + `RedirectStandardError` 到 `out/server.log` / `out/server.err.log`
- `scripts/start_server.ps1` 封装好，4 秒后自动健康检查

---

## 验证记录

### 2026-06-05 12:21 — Lark 直连测试
```
URL: https://open.feishu.cn/open-apis/bot/v2/hook/51b2a635-d461-4eec-9d41-c96db32e0e8d
Response: {"StatusCode":0,"StatusMessage":"success","code":0,"data":{},"msg":"success"}
✅ 飞书群收到 "[Direct test] Webhook is alive"
```

### 2026-06-05 12:24 — Lark 全链路 e2e
```
POST /webhook/pagerduty → HTTP 200 in 0.6s
Server logs: PagerDuty webhook received: incident-mock-001
✅ 飞书群收到 critical 红色 incident 卡片
```

---

## 自动化测试（待补 P1）

- `tests/test_lark_url_resolution.py` — 单测 `_resolve_webhook_url` 的 4 种输入：
  - bare token
  - 完整 feishu.cn URL
  - 完整 larksuite.com URL
  - 空字符串
- `tests/test_notifier_e2e.py` — 用 mocked httpx 验证 `LarkNotifier.send_report` 调用的 URL 正确

这两个测试能防止类似的静默失败 bug 再发生。

---

## 关联文件

| 文件 | 用途 |
|---|---|
| `app/integrations/lark_bot.py` | LarkNotifier 实现 + `_resolve_webhook_url` |
| `app/integrations/notifier.py` | Notifier Protocol |
| `app/integrations/notifier_factory.py` | `get_notifier()` 单例 |
| `app/api/webhook.py` | PagerDuty/Opsgenie 端点 + `_notify` 封装 |
| `simulation/send_test_incident.py` | 客户端 e2e 触发器 |
| `simulation/samples/pagerduty-incident.json` | 真实格式 payload |
| `scripts/diagnose_lark.ps1` | 4 步诊断 |
| `scripts/restart_and_test.ps1` | 一键重启 + 验证 |
| `scripts/start_server.ps1` | 干净启动 + 健康检查 |
| `PROGRESS.md` | 项目仪表板（含 Lark 验证状态）|
