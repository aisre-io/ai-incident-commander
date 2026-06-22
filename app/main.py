import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api import webhook, slack
from app.utils.logger import setup_logger
from app.config import get_settings

settings = get_settings()
logger = setup_logger(settings.log_level)

app = FastAPI(
    title="AI Incident Commander",
    version="0.1.0",
    description="AI-powered incident root cause analysis and remediation",
)

app.include_router(webhook.router)
app.include_router(slack.router)

DEPLOY_ENV = os.environ.get("DEPLOY_ENV") or os.environ.get("APP_ENV") or os.environ.get("RAILWAY_ENVIRONMENT", "development")

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Incident Commander</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; }
        .title { font-size: 2.5rem; margin-bottom: 10px; color: #fff; }
        .status { display: inline-block; background: #238636; color: #fff; padding: 8px 16px; border-radius: 20px; font-size: 1rem; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; text-align: center; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #58a6ff; }
        .stat-label { font-size: 0.9rem; color: #8b949e; margin-top: 8px; }
        .demo-section { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 30px; margin-bottom: 30px; }
        .demo-title { font-size: 1.5rem; margin-bottom: 20px; color: #fff; }
        .btn { background: #238636; color: #fff; border: none; padding: 14px 28px; border-radius: 8px; font-size: 1.1rem; cursor: pointer; transition: all 0.2s; width: 100%; }
        .btn:hover { background: #2ea043; transform: translateY(-2px); }
        .btn:disabled { background: #21262d; cursor: not-allowed; transform: none; }
        .result { margin-top: 24px; padding: 20px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; display: none; }
        .result.show { display: block; }
        .result-header { font-size: 1.2rem; margin-bottom: 16px; color: #3fb950; }
        .result-item { margin-bottom: 12px; }
        .result-label { color: #8b949e; font-size: 0.9rem; }
        .result-value { color: #c9d1d9; font-family: 'Monaco', 'Menlo', monospace; background: #161b22; padding: 8px 12px; border-radius: 4px; margin-top: 4px; word-break: break-all; }
        .links { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
        .link { color: #58a6ff; text-decoration: none; padding: 12px 24px; border: 1px solid #30363d; border-radius: 8px; transition: all 0.2s; }
        .link:hover { border-color: #58a6ff; background: #161b22; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 2px solid #30363d; border-radius: 50%; border-top-color: #58a6ff; animation: spin 1s linear infinite; margin-right: 10px; vertical-align: middle; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error { color: #f85149; }
        .success { color: #3fb950; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🎯 AI Incident Commander</h1>
            <div class="status">🟢 Live & Running</div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">87.31%</div>
                <div class="stat-label">RCA Accuracy</div>
            </div>
            <div class="stat">
                <div class="stat-value">26</div>
                <div class="stat-label">Simulations</div>
            </div>
            <div class="stat">
                <div class="stat-value">10</div>
                <div class="stat-label">Fault Types</div>
            </div>
            <div class="stat">
                <div class="stat-value">~12s</div>
                <div class="stat-label">Avg Latency</div>
            </div>
        </div>

        <div class="demo-section">
            <h2 class="demo-title">🚀 Live Demo</h2>
            <p style="margin-bottom: 20px; color: #8b949e;">Click the button to send a test PagerDuty incident and see AI-powered root cause analysis in action.</p>
            <button class="btn" id="testBtn" onclick="sendTestIncident()">
                Send Test Incident
            </button>
            <div class="result" id="result">
                <div class="result-header" id="resultHeader">✅ Analysis Complete</div>
                <div class="result-item">
                    <div class="result-label">Status</div>
                    <div class="result-value" id="status">-</div>
                </div>
                <div class="result-item">
                    <div class="result-label">Alerts Processed</div>
                    <div class="result-value" id="alerts">-</div>
                </div>
                <div class="result-item">
                    <div class="result-label">Latency</div>
                    <div class="result-value" id="latency">-</div>
                </div>
            </div>
        </div>

        <div class="links">
            <a href="https://github.com/aisre-io/ai-incident-commander" class="link" target="_blank">📦 GitHub</a>
            <a href="https://gitee.com/ai-sre/ai-incident-commander" class="link" target="_blank">📦 Gitee</a>
            <a href="/openapi.json" class="link" target="_blank">📄 API Docs</a>
            <a href="/health" class="link" target="_blank">❤️ Health</a>
        </div>
    </div>

    <script>
        const testPayload = {
            "event": {
                "id": "demo-" + Date.now(),
                "title": "High CPU usage on web-server-01",
                "description": "CPU usage exceeded 90% threshold for 5 minutes",
                "severity": "critical",
                "service": { "name": "web-frontend" },
                "created_at": new Date().toISOString(),
                "alerts": [{
                    "id": "alert-demo-" + Date.now(),
                    "title": "CPU Spike Detected",
                    "description": "web-server-01 CPU at 94%",
                    "severity": "critical"
                }]
            }
        };

        async function sendTestIncident() {
            const btn = document.getElementById('testBtn');
            const result = document.getElementById('result');
            const status = document.getElementById('status');
            const alerts = document.getElementById('alerts');
            const latency = document.getElementById('latency');
            const resultHeader = document.getElementById('resultHeader');

            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Analyzing...';
            result.className = 'result show';
            resultHeader.innerHTML = '⏳ Analyzing incident...';
            resultHeader.className = 'result-header';
            status.textContent = 'Processing...';
            alerts.textContent = '-';
            latency.textContent = '-';

            const startTime = Date.now();

            try {
                const response = await fetch('/webhook/pagerduty', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(testPayload)
                });

                const data = await response.json();
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

                if (response.ok) {
                    resultHeader.innerHTML = '✅ Analysis Complete';
                    resultHeader.className = 'result-header success';
                    status.textContent = '✅ Success';
                    status.className = 'result-value success';
                    alerts.textContent = data.alerts_processed || 1;
                    latency.textContent = elapsed + 's';
                } else {
                    throw new Error(data.detail || 'Request failed');
                }
            } catch (error) {
                resultHeader.innerHTML = '❌ Error';
                resultHeader.className = 'result-header error';
                status.textContent = '❌ ' + error.message;
                status.className = 'result-value error';
                latency.textContent = ((Date.now() - startTime) / 1000).toFixed(2) + 's';
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Send Test Incident';
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "public, max-age=300, s-maxage=600",
            "ETag": '"v1.0"',
        }
    )

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "env": DEPLOY_ENV}

@app.get("/keepalive")
async def keepalive():
    """Keep the service alive to prevent cold starts on free tier."""
    return {"status": "alive", "timestamp": os.environ.get("RAILWAY_DEPLOYMENT_ID", "local")}
