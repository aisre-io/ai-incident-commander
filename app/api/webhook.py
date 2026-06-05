from fastapi import APIRouter, Request
from app.models.schemas import AlertPayload
from app.services.incident_service import IncidentService
from app.agents.supervisor import SupervisorAgent
from app.integrations.notifier_factory import get_notifier
from app.utils.logger import logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
incident_service = IncidentService()
supervisor = SupervisorAgent()


@router.post("/pagerduty")
async def pagerduty_webhook(request: Request):
    body = await request.json()
    logger.debug(f"PagerDuty webhook received: {body.get('event', {}).get('id', 'unknown')}")

    messages = body.get("messages", [])
    for msg in messages:
        payload = msg.get("payload", {})
        alert = AlertPayload(
            source="pagerduty",
            alert_id=payload.get("id", ""),
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            severity=payload.get("severity", "warning"),
            service=payload.get("service", {}).get("name", "unknown"),
            timestamp=msg.get("occurred_at", ""),
            raw=payload,
        )
        event = await incident_service.process_alert(alert)
        result = await supervisor.run(event)
        await _notify(result)
        incident_service.save_report(result)

    return {"status": "ok"}


@router.post("/opsgenie")
async def opsgenie_webhook(request: Request):
    body = await request.json()
    logger.debug(f"Opsgenie webhook received: {body.get('alert', {}).get('alertId', 'unknown')}")

    alert_data = body.get("alert", {})
    alert = AlertPayload(
        source="opsgenie",
        alert_id=alert_data.get("alertId", ""),
        title=alert_data.get("message", ""),
        description=alert_data.get("description", ""),
        severity=alert_data.get("priority", "P3"),
        service=alert_data.get("source", "unknown"),
        timestamp=alert_data.get("createdAt", ""),
        raw=alert_data,
    )
    event = await incident_service.process_alert(alert)
    result = await supervisor.run(event)
    await _notify(result)
    incident_service.save_report(result)

    return {"status": "ok"}


async def _notify(report):
    notifier = get_notifier()
    try:
        await notifier.send_report(report)
    except Exception as e:
        logger.error(f"Notifier {notifier.name} failed: {e}")
