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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}
