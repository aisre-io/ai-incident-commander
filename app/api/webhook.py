from fastapi import APIRouter, Request, BackgroundTasks
from app.models.schemas import AlertPayload
from app.services.incident_service import IncidentService
from app.agents.supervisor import SupervisorAgent
from app.integrations.notifier_factory import get_notifier
from app.utils.logger import logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
incident_service = IncidentService()
supervisor = SupervisorAgent()


async def _process_alert_async(alert: AlertPayload):
    """Process a single alert asynchronously (AI analysis + notification)."""
    try:
        logger.info(f"Processing alert {alert.alert_id} asynchronously...")
        event = await incident_service.process_alert(alert)
        result = await supervisor.run(event)
        await _notify(result)
        incident_service.save_report(result)
        logger.info(f"Alert {alert.alert_id} processed successfully")
    except Exception as e:
        logger.error(f"Async processing failed for alert {alert.alert_id}: {e}")


@router.post("/pagerduty")
async def pagerduty_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    logger.debug(f"PagerDuty webhook received: {body.get('event', {}).get('id', 'unknown')}")

    alerts = _parse_pagerduty_payload(body)
    for alert in alerts:
        background_tasks.add_task(_process_alert_async, alert)

    return {"status": "ok", "alerts_processed": len(alerts), "processing": "async"}


@router.post("/opsgenie")
async def opsgenie_webhook(request: Request, background_tasks: BackgroundTasks):
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
    background_tasks.add_task(_process_alert_async, alert)

    return {"status": "ok", "processing": "async"}


def _parse_pagerduty_payload(body: dict) -> list[AlertPayload]:
    fmt = "pd_v3" if body.get("messages") else "simplified"
    logger.info(f"PagerDuty payload format: {fmt}")

    if fmt == "pd_v3":
        alerts = []
        for msg in body.get("messages", []):
            p = msg.get("payload", {})
            alerts.append(AlertPayload(
                source="pagerduty",
                alert_id=p.get("id", ""),
                title=p.get("title", ""),
                description=p.get("description", ""),
                severity=p.get("severity", "warning"),
                service=p.get("service", {}).get("name", "unknown"),
                timestamp=msg.get("occurred_at", ""),
                raw=p,
            ))
        return alerts

    ev = body.get("event", {})
    svc = ev.get("service", {}).get("name", "unknown")
    alerts = []
    for a in ev.get("alerts", [ev]):
        alerts.append(AlertPayload(
            source="pagerduty",
            alert_id=a.get("id", ev.get("id", "")),
            title=a.get("title", ev.get("title", "")),
            description=a.get("description", ev.get("description", "")),
            severity=a.get("severity", "critical"),
            service=a.get("service", {}).get("name", svc),
            timestamp=ev.get("created_at", ""),
            raw=a,
        ))
    return alerts


async def _notify(report):
    notifier = get_notifier()
    try:
        await notifier.send_report(report)
    except Exception as e:
        logger.error(f"Notifier {notifier.name} failed: {e}")
