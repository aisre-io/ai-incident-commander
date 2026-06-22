import os
from fastapi import FastAPI
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

@app.get("/")
async def root():
    return {
        "name": "AI Incident Commander",
        "status": "🟢 Live",
        "version": "0.1.0",
        "description": "AI-powered incident root cause analysis and remediation",
        "accuracy": "87.31% on 26 simulations",
        "endpoints": {
            "health": "/health",
            "docs": "/openapi.json",
            "pagerduty_webhook": "/webhook/pagerduty",
            "opsgenie_webhook": "/webhook/opsgenie"
        },
        "links": {
            "github": "https://github.com/aisre-io/ai-incident-commander",
            "gitee": "https://gitee.com/ai-sre/ai-incident-commander"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "env": DEPLOY_ENV}
