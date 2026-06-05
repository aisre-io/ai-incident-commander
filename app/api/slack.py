from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi import SlackRequestHandler
from app.integrations.slack_bot import get_slack_app
from app.utils.logger import logger

router = APIRouter(prefix="/slack", tags=["slack"])


@router.post("/events")
async def slack_events(request: Request):
    app = get_slack_app()
    if not app:
        return {"error": "Slack not configured"}, 500
    handler = SlackRequestHandler(app)
    return await handler.handle(request)


@router.get("/install")
async def install():
    return {"message": "Slack app installation endpoint"}


@router.get("/oauth_redirect")
async def oauth_redirect():
    return {"message": "OAuth redirect endpoint"}
