#!/usr/bin/env python3
"""
Generate 60+ simulated incidents with known ground truth for RCA benchmark.

Fault types (10): cpu_spike, memory_leak, slow_query, null_pointer,
                  dep_timeout, disk_full, network_partition, cert_expiry,
                  config_error, deploy_regression
"""

import json
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta

SERVICES = ["api-gateway", "user-service", "payment-service", "order-service", "notification-service", "search-service"]
LANGUAGES = ["Java", "Go", "Python", "Node.js", "Rust"]
REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

random.seed(42)

FAULT_TEMPLATES = {
    "cpu_spike": {
        "alerts": [
            lambda svc: {"title": f"High CPU on {svc}", "description": f"CPU > 95% for 10 minutes on {svc}", "severity": "critical"},
            lambda svc: {"title": f"CPU threshold breach on {svc}", "description": f"CPU utilization sustained above 90%", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": f"fix: add rate limiting to {svc} endpoint", "author": "dev1", "files_changed": 3},
            {"message": f"feat: add new data processing pipeline", "author": "dev2", "files_changed": 12},
        ],
        "logs": [
            "ERROR - Request processing time exceeded 30s",
            "WARN - Thread pool exhausted, rejecting request",
            "ERROR - connection reset by peer",
        ],
        "ground_truth": lambda svc: f"Inefficient data processing pipeline in {svc} causing CPU saturation. New pipeline feature added excessive computation per request without rate limiting.",
    },
    "memory_leak": {
        "alerts": [
            lambda svc: {"title": f"OOM on {svc}", "description": f"Memory usage > 95% on {svc} instances", "severity": "critical"},
            lambda svc: {"title": f"Heap memory warning on {svc}", "description": f"Heap usage growing monotonically", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": f"fix: close database connections properly", "author": "dev3", "files_changed": 1},
            {"message": f"feat: add in-memory result cache", "author": "dev1", "files_changed": 5},
            {"message": "refactor: update session management", "author": "dev2", "files_changed": 8},
        ],
        "logs": [
            "ERROR - java.lang.OutOfMemoryError: Java heap space",
            "WARN - GC overhead limit exceeded",
            "ERROR - Unable to create new native thread",
        ],
        "ground_truth": lambda svc: f"Memory leak in {svc} caused by unbounded in-memory result cache. Cache entries are never evicted, causing heap to grow until OOM.",
    },
    "slow_query": {
        "alerts": [
            lambda svc: {"title": f"DB query timeout on {svc}", "description": f"P95 query latency > 5s on primary database", "severity": "critical"},
            lambda svc: {"title": f"Connection pool exhaustion", "description": f"Database connections maxed out", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": f"feat: add user analytics dashboard", "author": "dev4", "files_changed": 6},
            {"message": "perf: add index to orders table", "author": "dev3", "files_changed": 1},
        ],
        "logs": [
            "WARN - Slow query detected: SELECT * FROM orders WHERE user_id NOT IN (SELECT id FROM active_users) — 8.3s",
            "ERROR - PostgreSQL: canceling statement due to statement timeout",
            "WARN - connection pool at 95% capacity",
        ],
        "ground_truth": lambda svc: f"Unoptimized query in {svc} analytics dashboard: full table scan on orders with NOT IN subquery. Missing index and lack of pagination causes database CPU spike.",
    },
    "null_pointer": {
        "alerts": [
            lambda svc: {"title": f"High error rate on {svc}", "description": f"500 errors > 5% of requests on {svc}", "severity": "critical"},
            lambda svc: {"title": f"Service degradation on {svc}", "description": f"Error rate spike to 12%", "severity": "critical"},
        ],
        "commits": lambda svc: [
            {"message": "fix: handle null user profile in response", "author": "dev1", "files_changed": 2},
        ],
        "logs": [
            "ERROR - NullPointerException: Cannot invoke 'User.getName()' because 'user' is null",
            "ERROR - at com.{svc}.UserController.getProfile(UserController.java:82)",
            "WARN - request failed: GET /api/users/profile",
        ],
        "ground_truth": lambda svc: f"NullPointerException in {svc} UserController.getProfile() at line 82. A recent fix attempted to handle null user profile but missed the case where user object itself is null, not just the profile.",
    },
    "dep_timeout": {
        "alerts": [
            lambda svc: {"title": f"Upstream timeout on {svc}", "description": f"{svc} failing to reach payment-gateway", "severity": "critical"},
            lambda svc: {"title": f"External dependency degraded", "description": f"Payment gateway P99 latency > 10s", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": "chore: bump payment SDK version to 3.2.1", "author": "dev5", "files_changed": 1},
            {"message": "feat: add retry logic for payment calls", "author": "dev4", "files_changed": 3},
        ],
        "logs": [
            "ERROR - HTTP timeout calling payment-gateway/charge after 30s",
            "WARN - Retry attempt 2/3 for payment-gateway/charge",
            "ERROR - circuit-breaker opened for payment-gateway",
        ],
        "ground_truth": lambda svc: f"Payment gateway SDK upgrade to v3.2.1 changed the default timeout from 60s to 10s. Combined with new retry logic, rapid retries overwhelm the downstream causing cascade failure.",
    },
    "disk_full": {
        "alerts": [
            lambda svc: {"title": f"Disk full on {svc} host", "description": f"/data partition 100% full on {svc} nodes", "severity": "critical"},
            lambda svc: {"title": f"Write failures on {svc}", "description": f"Application unable to write logs and data files", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": "feat: add verbose debug logging to data pipeline", "author": "dev2", "files_changed": 4},
            {"message": "feat: enable request/response payload logging", "author": "dev1", "files_changed": 2},
        ],
        "logs": [
            "ERROR - Disk quota exceeded: No space left on device",
            "WARN - Log rotation failed: unable to archive /var/log/app/access.log",
            "ERROR - write /data/db/journal: no space left on device",
        ],
        "ground_truth": lambda svc: f"Verbose debug logging and request payload logging enabled in {svc} data pipeline. Log volume increased 50x, log rotation settings not updated, causing disk to fill within hours.",
    },
    "network_partition": {
        "alerts": [
            lambda svc: {"title": f"Service unreachable", "description": f"{svc} cannot reach database cluster", "severity": "critical"},
            lambda svc: {"title": f"Replica lag spike", "description": f"DB replication lag > 300s across AZs", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": "ops: update security group rules for database access", "author": "devops", "files_changed": 2},
        ],
        "logs": [
            "ERROR - dial tcp 10.0.3.12:5432: i/o timeout",
            "WARN - connection to database primary lost, attempting failover",
            "ERROR - all database replicas unreachable from current AZ",
        ],
        "ground_truth": lambda svc: f"Network partition between {svc} AZ and database cluster. Recent security group update inadvertently removed the ingress rule for the application subnet on port 5432.",
    },
    "cert_expiry": {
        "alerts": [
            lambda svc: {"title": f"TLS handshake failures on {svc}", "description": f"Clients reporting SSL errors connecting to {svc}", "severity": "critical"},
            lambda svc: {"title": f"Certificate warning", "description": f"TLS certificate for api.example.com expires in 3 days", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": "ops: update load balancer TLS settings", "author": "devops", "files_changed": 1},
        ],
        "logs": [
            "ERROR - SSL_ERROR_EXPIRED_CERT: certificate expired",
            "ERROR - tls: first record does not look like a TLS handshake",
            "WARN - acme renewal failed: Let's Encrypt endpoint unreachable",
        ],
        "ground_truth": lambda svc: f"TLS certificate for {svc} has expired. Auto-renewal failed because Let's Encrypt ACME endpoint was blocked by updated firewall rules. Load balancer TLS settings update did not include cert rotation.",
    },
    "config_error": {
        "alerts": [
            lambda svc: {"title": f"Deployment failure on {svc}", "description": f"New version of {svc} failing health checks", "severity": "critical"},
            lambda svc: {"title": f"Config validation error", "description": f"Invalid configuration in latest release", "severity": "warning"},
        ],
        "commits": lambda svc: [
            {"message": "feat: add feature flags system", "author": "dev1", "files_changed": 10},
            {"message": "fix: correct database URL in config template", "author": "dev2", "files_changed": 1},
        ],
        "logs": [
            f"ERROR - Failed to parse config.yaml: unknown field 'feature_toggles'",
            "ERROR - Application startup aborted due to configuration error",
            "WARN - Config validation: environment 'production' not found in allowed values",
        ],
        "ground_truth": lambda svc: f"Configuration parsing error in {svc}: feature flags config schema mismatch. New 'feature_toggles' field was added to config but the JSON schema validation was not updated to include it, causing startup rejection.",
    },
    "deploy_regression": {
        "alerts": [
            lambda svc: {"title": f"Error rate spike after deployment", "description": f"{svc} error rate increased 10x after latest deploy", "severity": "critical"},
            lambda svc: {"title": f"Latency regression on {svc}", "description": f"P99 latency increased from 200ms to 5s", "severity": "critical"},
        ],
        "commits": lambda svc: [
            {"message": "refactor: migrate authentication to OAuth 2.0", "author": "dev1", "files_changed": 15},
            {"message": "fix: update auth token validation logic", "author": "dev1", "files_changed": 3},
            {"message": "chore: bump golang version to 1.22", "author": "dev5", "files_changed": 2},
        ],
        "logs": [
            "ERROR - token validation failed: unexpected signature algorithm",
            "WARN - JWT decode error: crypto/rsa: verification error",
            "ERROR - authentication middleware rejection rate: 45%",
        ],
        "ground_truth": lambda svc: f"Deploy regression in {svc}: OAuth 2.0 migration changed token signing algorithm from RS256 to RS384 but validation logic still expects RS256. Combined with Go 1.22 crypto behavior change, all tokens are rejected.",
    },
}


def generate_incident(fault_type: str, templates: dict, idx: int) -> dict:
    svc = random.choice(SERVICES)
    lang = random.choice(LANGUAGES)
    region = random.choice(REGIONS)
    now = datetime.utcnow() - timedelta(hours=random.randint(1, 72))

    alert_templates = templates["alerts"]
    alerts = []
    for i, at in enumerate(alert_templates):
        a = at(svc)
        a = at(svc)
        alerts.append({
            "source": random.choice(["pagerduty", "opsgenie"]),
            "alert_id": f"sim-{fault_type}-{idx}-{i}",
            "title": a["title"],
            "description": a["description"],
            "severity": a["severity"],
            "service": svc,
            "timestamp": (now + timedelta(minutes=i * 3)).isoformat(),
        })

    commit_fn = templates["commits"]
    commit_list = commit_fn(svc) if callable(commit_fn) else commit_fn
    commits = []
    for ct in commit_list:
        c = ct
        commits.append({
            "sha": f"sim-{uuid.uuid4().hex[:12]}",
            "message": c["message"],
            "author": c["author"],
            "files_changed": c["files_changed"],
            "timestamp": (now - timedelta(hours=random.randint(1, 48))).isoformat(),
        })

    logs = [l if "{svc}" not in l else l.format(svc=svc) for l in templates["logs"]]

    ground_truth = templates["ground_truth"](svc)

    return {
        "id": f"sim-{fault_type}-{idx:03d}",
        "fault_type": fault_type,
        "service": svc,
        "language": lang,
        "region": region,
        "severity": random.choice(["critical", "critical", "warning"]),
        "timestamp": now.isoformat(),
        "title": alerts[0]["title"] if alerts else f"Incident on {svc}",
        "alerts": alerts,
        "commits": commits,
        "logs": logs,
        "incident_count": len(alerts),
        "ground_truth": ground_truth,
        "expected_confidence": 0.95 if fault_type != "network_partition" else 0.7,
    }


def generate_dataset(count_per_type: int = 6) -> list[dict]:
    incidents = []
    for fault_type, templates in FAULT_TEMPLATES.items():
        for i in range(count_per_type):
            incident = generate_incident(fault_type, templates, i)
            incidents.append(incident)
    return incidents


def main():
    incidents = generate_dataset(count_per_type=6)
    output_path = Path(__file__).parent / "dataset.json"

    stats = {}
    for inc in incidents:
        stats.setdefault(inc["fault_type"], 0)
        stats[inc["fault_type"]] += 1

    output = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat(),
            "total": len(incidents),
            "fault_types": len(stats),
            "stats": stats,
        },
        "incidents": incidents,
    }

    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(incidents)} incidents ({len(stats)} fault types)")
    for ft, c in sorted(stats.items()):
        print(f"  {ft}: {c}")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
