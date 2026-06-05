# Railway / Fly.io / Render one-click deploy

## Railway (easiest)

1. Push this repo to GitHub
2. Go to https://railway.app/new → "Deploy from GitHub repo"
3. Railway auto-detects Dockerfile and builds
4. Set environment variables in Railway dashboard:
   - `DEEPSEEK_API_KEY` (required)
   - `LARK_WEBHOOK_URL` (required for notifications)
   - `LARK_REGION` = `cn`
   - `NOTIFIER_TYPE` = `lark`
   - `GITHUB_TOKEN` (optional)
   - `PAGERDUTY_API_KEY` (optional)
   - `OPSGENIE_API_KEY` (optional)
5. Generate domain → Settings → Networking → "Generate Domain"
6. Webhook URL: `https://<your-app>.up.railway.app/api/webhook/pagerduty`

## Fly.io (most control)

```bash
# Install fly CLI: https://fly.io/docs/hands-on/install-flyctl/
fly launch --copy-config --name ai-incident-commander
fly secrets set DEEPSEEK_API_KEY=sk-xxx LARK_WEBHOOK_URL=https://open.feishu.cn/...
fly deploy
```

## Render (zero-config alternative)

1. New → Web Service → Connect repo
2. Environment: Docker
3. Add same env vars as Railway above
4. Deploy

## Verify deploy

```bash
curl https://<your-domain>/health
# Expected: {"status":"ok","version":"0.1.0","env":"production"}

# Send a test PagerDuty webhook (replace URL)
curl -X POST https://<your-domain>/api/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d @simulation/incident_sample.json
```

A Lark card should appear in your test group within 5-15 seconds.

## Cost

- Railway free tier: 500 hrs/mo + $5 credit → sufficient for MVP
- Fly.io free tier: 3 shared VMs
- Render free tier: spins down after 15 min idle (use paid plan for production)
- DeepSeek V4 Flash API: ~$0.28 / 1M output tokens (Flash is 6x cheaper than V3.2-era pricing)
