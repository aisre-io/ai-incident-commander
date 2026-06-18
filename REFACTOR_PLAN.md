# AI Incident Commander — 重构计划

> **日期**: 2026-06-10
> **基准版本**: 0.1.0
> **基准准确率**: 87.31%（26 个模拟故障，LLM-as-Judge 评分）

---

## 一、现状审计摘要

### 项目结构（实际）
```
app/
├── agents/              # alert_clustering, rca_investigation, supervisor, synthesis
├── api/                 # webhook.py, slack.py (FastAPI 入口)
├── integrations/        # deepseek, github, lark_bot, slack_bot, pagerduty, opsgenie, notifier
├── models/              # schemas.py (Pydantic 数据模型)
├── services/            # incident_service, cache_service
├── utils/               # logger
├── config.py            # 配置 / 模型路由
└── main.py              # FastAPI 应用
simulation/              # 评测框架（26 个故障场景）
tests/                   # 单元测试
docs/postmortems/        # Cloudflare 复盘案例（手动撰写）
```

### 当前架构管线
```
Webhook → IncidentService → AlertClusteringAgent → RCAInvestigationAgent → SynthesisAgent → Notifier
```

### 已识别的关键问题

| # | 问题 | 严重程度 | 说明 |
|---|------|---------|------|
| 1 | **单视角 RCA** | 高 | 每次调查只调用一次 LLM，缺少多维度交叉验证 |
| 2 | **GitHub commit 永远为空** | 高 | `rca_investigation.py` 调用 `get_recent_commits("", "")` → 始终返回 `[]` |
| 3 | **无数据库持久化** | 中 | `IncidentService` 和 `ContentHashCache` 都是内存存储，重启即丢失 |
| 4 | **Synthesis 层过于薄弱** | 中 | 只把数据打包成报告，没有做信息提炼或扩展分析 |
| 5 | **无自动复盘报告** | 中 | `docs/postmortems/` 中的 Cloudflare 分析是手动写的 |
| 6 | **弱类别准确率低** | 中 | dep_timeout (70%), config_error (70%), deploy_regression (70%) |
| 7 | **无重试 / 降级机制** | 低 | `DeepSeekClient.chat()` 单次调用，失败即返回空字符串 |
| 8 | **pagerduty/opsgenie 集成不完整** | 低 | PagerDutyClient 和 OpsgenieClient 存在但 webhook 中没有实际使用它们的 API |

---

## 二、重构目标

1. **准确率从 87% → 95%+**（尤其修复 dep_timeout / config_error / deploy_regression）
2. **GitHub commit 数据真正注入 RCA**
3. **数据库持久化**（SQLite 起步，可选 PostgreSQL）
4. **自动复盘报告生成**
5. **保持架构简洁，不引入过度设计**

---

## 三、三阶段执行计划

### Phase 1：核心修复（优先级最高）

**目标**: 解决最容易修复的问题，快速提升准确率

| 任务 | 文件 | 改动 |
|------|------|------|
| 1.1 修复 GitHub commit 注入 | `app/agents/rca_investigation.py` | 从 env 读取 `GITHUB_OWNER/REPO`，或在 webhook 请求中传递仓库信息 |
| 1.2 多视角 RCA 提示词 | `app/agents/rca_investigation.py` | 分解为 3 个子提示词分别分析（时序 / 代码变更 / 依赖关系），然后合成最终结论 |
| 1.3 弱类别专项优化 | `app/config.py` + `rca_investigation.py` | 降低 dep_timeout/config_error 的质量门禁阈值，或为这些类型设计专用提示词 |
| 1.4 LLM 调用重试 | `app/integrations/deepseek.py` | 加入指数退避重试（最多 3 次） |
| 1.5 提交缓存 | `app/services/cache_service.py` | 将 `ContentHashCache` 接入文件或 SQLite 持久化 |

### Phase 2：深度分析层（新能力）

**目标**: 引入多维度分析能力，提升 RCA 的可解释性和覆盖范围

| 任务 | 文件（新建） | 说明 |
|------|-------------|------|
| 2.1 多视角分析器 | `app/agents/deep_analyzer.py` | 从 3 个视角独立分析：时序指标、代码变更、依赖链路，每个视角单独调用 LLM |
| 2.2 根因提炼器 | `app/agents/cause_extractor.py` | 接收多视角分析结果，交叉验证后输出最可能的根因，附带置信度分解 |
| 2.3 影响范围分析 | `app/agents/blast_radar.py` | 分析根因的影响范围：受影响的服务数、用户数、功能面 |
| 2.4 DAG 依赖建模 | `app/agents/dag_deps.py` | 根据服务依赖图谱构建有向无环图，分析故障传播路径 |
| 2.5 复盘报告生成器 | `app/agents/postmortem_gen.py` | 自动生成结构化复盘报告（Markdown），包含时间线、根因、影响、改进项 |

### Phase 3：基础设施加固

**目标**: 让系统能投入生产使用

| 任务 | 说明 |
|------|------|
| 3.1 SQLite 持久化 | 将 `IncidentService` 和缓存后端迁移到 SQLite（`database.py`） |
| 3.2 Supabase 可选后端 | 当 `SUPABASE_URL` 配置时，使用 Supabase 替代 SQLite |
| 3.3 告警去重优化 | 改进 `_find_matching_event` 的匹配逻辑，支持更多字段对比 |
| 3.4 评测扩展 | 在 `simulation/dataset.json` 中增加更多故障类型：dns_failure, tls_mismatch, quota_exceeded |
| 3.5 CI 流水线 | `simulation/evaluate.py --judge --save` 作为 CI 门禁 |

---

## 四、不做的范围（Anti-Goals）

- ❌ 不引入 `v2/` 子包 —— 新模块直接放在 `app/agents/` 下，扁平化
- ❌ 不做微前端 / Web UI
- ❌ 不替换 LLM 提供商（保持 DeepSeek）
- ❌ 不引入消息队列（当前同步调用链足够）

---

## 五、准确率提升目标

| 故障类型 | 当前 | Phase 1 目标 | Phase 2 目标 |
|---------|------|-------------|-------------|
| memory_leak | 100% | - | - |
| null_pointer | 100% | - | - |
| network_partition | 100% | - | - |
| cpu_spike | 90% | 95% | 100% |
| slow_query | 85% | 90% | 95% |
| disk_full | 85% | 90% | 95% |
| cert_expiry | 85% | 90% | 95% |
| dep_timeout | **70%** | 85% | 95% |
| config_error | **70%** | 85% | 95% |
| deploy_regression | **70%** | 85% | 95% |
| **整体** | **87.31%** | **92%** | **97%** |

---

## 六、验证方式

每次 Phase 完成后，运行：

```bash
python simulation/evaluate.py --judge --save
```

确保准确率不低于目标阈值，且没有回归。
