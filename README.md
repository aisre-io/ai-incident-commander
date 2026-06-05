# AI Incident Commander

> Self-hosted AI SRE that compresses 60+ alerts into a single incident with root cause + fix in ~12 seconds.

[![Gitee stars](https://gitee.com/ai-sre/ai-incident-commander/badge/star.svg?theme=white)](https://gitee.com/ai-sre/ai-incident-commander)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org)
[![Tests](https://img.shields.io/badge/tests-61%2F61-brightgreen)](tests/)
[![Hosted on Gitee](https://img.shields.io/badge/hosted%20on-Gitee-C71D23?logo=gitee&logoColor=white)](https://gitee.com/ai-sre/ai-incident-commander)

## Why

On-call engineers drown in alert noise. 60+ alerts per incident, ~30 min MTTR, manual correlation across PagerDuty + GitHub + logs.

**AI Incident Commander** collapses that:

- **60:1 alert compression** — clusters related alerts into one incident
- **~12s root cause** with suspect commit + fix suggestion
- **$0.14 per million tokens** (DeepSeek V4 Flash), ~$0.002 per incident
- **Self-hosted**, no data leaves your infra

## Quick Start

```bash
git clone https://gitee.com/ai-sre/ai-incident-commander
cd ai-incident-commander
pip install -r requirements.txt
cp .env.example .env       # fill DEEPSEEK_API_KEY and LARK_WEBHOOK_URL
python run.py
```

> **Note**: This repo is currently hosted on **Gitee** (mainland China network conditions). A GitHub mirror will follow once access stabilizes. All issues / PRs are welcome on Gitee.

Send a test incident:

```bash
curl -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d @simulation/samples/pagerduty-incident.json
```

You should see a Lark (or Slack) card in ~12s with: severity, root cause, fix suggestion, suspect commit.

## Architecture

```
                          ┌──────────────────────────────┐
   PagerDuty / Opsgenie   │     AI Incident Commander    │   Lark / Slack
   ────────────────▶      │                              │   ────────────▶
        alert              │  ┌──────────────┐            │   incident card
                          │  │  Clustering  │  Flash     │
                          │  │    Agent     │ ──────────▶│
                          │  └──────────────┘            │
                          │         │                    │
                          │         ▼  cache check       │
                          │  ┌──────────────┐            │
                          │  │     RCA      │ Flash →    │
                          │  │    Agent     │ Pro (conf │
                          │  └──────────────┘ < 0.7)    │
                          │         │                    │
                          │         ▼                    │
                          │  ┌──────────────┐            │
                          │  │  Synthesis   │            │
                          │  │    Agent     │            │
                          │  └──────────────┘            │
                          │         │                    │
                          │         ▼                    │
                          │  ┌──────────────┐            │
                          │  │   Notifier   │  Lark /    │
                          │  │   Protocol   │  Slack /   │
                          │  └──────────────┘  Console  │
                          └──────────────────────────────┘
```

**Key design choices:**

- **Notifier Protocol** (`app/integrations/notifier.py`): Lark is the default implementation (no Slack OAuth pain, works in China). Slack and Console available — switching is a one-env-var change.
- **Content-hash cache** (`app/services/cache_service.py`): identical alert patterns reuse prior RCA, dropping per-incident cost toward zero.
- **Model router** (`app/config.py:get_model_for`): Flash for the 80% case, Pro only when confidence < 0.7. Verified Flash (97%) actually outperforms Pro (94%) on the 10 fault types we tested.

## Validation

| Benchmark | Result | Notes |
|-----------|--------|-------|
| **RCA accuracy** | **87.31%** | LLM-as-judge, **26 samples / 10 fault types** |
| &nbsp;&nbsp;memory_leak / network_partition / null_pointer | 100% | Cleanest signal |
| &nbsp;&nbsp;cpu_spike | 90% | |
| &nbsp;&nbsp;slow_query / disk_full / cert_expiry | 85% | |
| &nbsp;&nbsp;config_error / dep_timeout / deploy_regression | 70% | Need commit-log signal |
| **Tests** | **61/61 passing** | 50 original + 11 Lark URL resolution regression |
| **End-to-end Lark** | ✅ Verified | Critical incident card delivered to Feishu group |
| **Cold-start latency** | ~12s p50, ~20s p95 | Flash 4-19s + LangGraph overhead |

Reproduce the benchmark:

```bash
python simulation/extend_benchmark.py
python simulation/evaluate.py
```

## Deployment

```bash
docker build -t ai-incident-commander .
docker run -p 8000:8000 --env-file .env ai-incident-commander
```

See [`DEPLOY.md`](DEPLOY.md) for one-click deployment to:
- **Fly.io** (`fly.toml` included)
- **Railway**
- **Render**

## Tech Stack

- **Python 3.12** + FastAPI + uvicorn
- **LangGraph** for multi-agent orchestration
- **DeepSeek V4 Flash** (default) + **V4 Pro** (escalation)
- **Lark / Slack / Console** notifiers (Protocol abstraction)
- **pydantic** v2 + pydantic-settings
- **pytest** + httpx (61 tests)

## Project Layout

```
ai-incident-commander/
├── app/
│   ├── agents/                # LangGraph agents (clustering, RCA, synthesis)
│   ├── api/                   # Webhook endpoints
│   ├── config.py              # Model router + settings
│   ├── integrations/          # Notifier Protocol + Lark/Slack/GitHub/PD/Opsgenie
│   ├── models/                # Pydantic schemas
│   ├── services/              # Cache + incident store
│   └── utils/
├── tests/                     # 61 tests
├── simulation/                # Benchmark dataset + LLM-as-judge eval
├── scripts/                   # PowerShell ops helpers
├── Dockerfile + fly.toml      # Deployment
└── DEPLOY.md
```

## License

[MIT](LICENSE)

## Contributing

This is currently a pre-launch project. The full public roadmap, contribution guide, and postmortem series will land after the first 5 Founding Partners sign on. If you run AI Incident Commander in production and want to share a postmortem, open an issue with the `postmortem` label.

---

Built with LangGraph, DeepSeek, and a lot of alert noise.
