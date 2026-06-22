# 5 分钟部署 AI Incident Commander

> 从零到生产：用 Railway 一键部署 AI 驱动的事故根因分析系统

**预计时间**: 5 分钟 | **难度**: 简单 | **成本**: 免费起步

---

## 🎯 你会得到什么

- ✅ 一个公网可访问的 AI Incident Commander 实例
- ✅ PagerDuty/OpsGenie webhook 端点
- ✅ Lark/Slack 实时通知
- ✅ AI 驱动的根因分析（87.31% 准确率）

---

## 📋 前置条件

| 需求 | 说明 |
|------|------|
| GitHub 账号 | 用于连接 Railway |
| DeepSeek API Key | 从 [platform.deepseek.com](https://platform.deepseek.com) 获取 |
| Lark Webhook URL（可选） | 用于接收通知 |

---

## 🚀 5 分钟部署步骤

### Step 1: Fork 仓库 (30 秒)

```bash
# 访问 GitHub 仓库
https://github.com/aisre-io/ai-incident-commander

# 点击右上角 "Fork" 按钮
# 选择你的 GitHub 账号
```

### Step 2: 连接 Railway (1 分钟)

```bash
# 访问 Railway
https://railway.app/new

# 选择 "Deploy from GitHub repo"
# 授权 Railway 访问你的 GitHub
# 选择刚 fork 的仓库
```

### Step 3: 配置环境变量 (2 分钟)

在 Railway 仪表板中，进入 **Variables** 标签，添加：

```bash
# 必需
DEEPSEEK_API_KEY=sk-your-api-key-here

# 可选（用于通知）
NOTIFIER_TYPE=lark
LARK_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
LARK_REGION=cn

# 可选（用于关联代码）
GITHUB_TOKEN=ghp-your-github-token
```

### Step 4: 生成公网域名 (30 秒)

```bash
# 在 Railway 仪表板
# 进入 Settings → Networking
# 点击 "Generate Domain"
# 
# 你会得到一个类似这样的 URL:
# https://ai-incident-commander-production.up.railway.app
```

### Step 5: 验证部署 (1 分钟)

```bash
# 1. 健康检查
curl https://your-app.up.railway.app/health

# 预期输出:
# {"status":"ok","version":"0.1.0","env":"production"}

# 2. 访问 Demo 页面
# 在浏览器中打开你的 Railway URL
# 看到交互式 Demo 页面 ✓

# 3. 发送测试事故
curl -X POST https://your-app.up.railway.app/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "id": "test-001",
      "title": "High CPU usage on web-server-01",
      "severity": "critical",
      "service": {"name": "web-frontend"},
      "created_at": "2026-06-22T10:00:00Z"
    }
  }'
```

---

## 🎉 完成！

你的 AI Incident Commander 现在已经：

- ✅ **公网可访问** — 任何人可以访问 Demo 页面
- ✅ **接收告警** — PagerDuty/OpsGenie webhook 已就绪
- ✅ **AI 分析** — 事故发生时自动分析根因
- ✅ **发送通知** — Lark/Slack 实时推送分析结果

---

## 📊 下一步

### 配置告警源

```bash
# PagerDuty
# 在 PagerDuty → Services → your service → Integrations
# 添加 Webhook: https://your-app.up.railway.app/webhook/pagerduty

# OpsGenie
# 在 OpsGenie → Settings → Notification Rules
# 添加 Webhook: https://your-app.up.railway.app/webhook/opsgenie
```

### 自定义配置

```bash
# 查看所有配置选项
https://your-app.up.railway.app/openapi.json

# 关键配置:
# - DEEPSEEK_MODEL: 使用的模型 (default: deepseek-v4-flash)
# - RCA_CONFIDENCE_THRESHOLD: RCA 置信度阈值 (default: 0.7)
# - CACHE_TTL: 缓存过期时间 (default: 3600)
```

### 监控和日志

```bash
# Railway 日志
# 在 Railway 仪表板 → Deployments → 查看实时日志

# 健康监控
# 设置 UptimeRobot 或类似服务监控 /health 端点
```

---

## 💰 成本说明

| 项目 | 费用 |
|------|------|
| **Railway** | 免费额度 500 小时/月 + $5 信用额度 |
| **DeepSeek API** | ~$0.002/次事故分析 |
| **总计** | 每月 $5-10（中等使用量）|

---

## 🔧 故障排除

### 问题: 部署失败

```bash
# 检查 Railway 构建日志
# 常见原因:
# - Dockerfile 路径错误
# - 依赖安装失败
# - 环境变量未设置
```

### 问题: webhook 无响应

```bash
# 检查应用日志
# 常见原因:
# - DEEPSEEK_API_KEY 无效
# - LARK_WEBHOOK_URL 格式错误
# - 网络连接问题
```

### 问题: 通知未收到

```bash
# 验证 Lark Webhook
curl -X POST https://open.feishu.cn/open-apis/bot/v2/hook/your-token \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"Test"}}'

# 预期: {"StatusCode":0,"StatusMessage":"success"}
```

---

## 📚 更多资源

- **完整文档**: [DEPLOY.md](../../DEPLOY.md)
- **API 文档**: `https://your-app.up.railway.app/openapi.json`
- **GitHub 仓库**: [github.com/aisre-io/ai-incident-commander](https://github.com/aisre-io/ai-incident-commander)
- **Gitee 仓库**: [gitee.com/ai-sre/ai-incident-commander](https://gitee.com/ai-sre/ai-incident-commander)

---

## 🤝 需要帮助？

- **GitHub Issues**: [github.com/aisre-io/ai-incident-commander/issues](https://github.com/aisre-io/ai-incident-commander/issues)
- **Email**: jacky_yzq@139.com

---

**最后更新**: 2026-06-22  
**版本**: 0.1.0  
**状态**: ✅ 生产就绪
