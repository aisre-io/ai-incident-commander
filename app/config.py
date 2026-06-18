from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal

NotifierType = Literal["lark", "slack", "console"]


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    lark_webhook_url: str = ""
    lark_region: Literal["cn", "intl"] = "cn"
    notifier_type: NotifierType = "lark"
    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = ""
    tdengine_host: str = "localhost"
    tdengine_port: int = 6041
    tdengine_user: str = "root"
    tdengine_password: str = "taosdata"
    tdengine_database: str = "incident_commander"
    github_token: str = ""
    pagerduty_api_key: str = ""
    opsgenie_api_key: str = ""
    app_env: str = "development"
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "extra": "ignore"}


TASK = Literal["rca", "clustering", "extraction", "synthesis", "quick"]

_ROUTING: dict[TASK, str] = {
    "rca": "deepseek-v4-flash",
    "rca_pro": "deepseek-v4-pro",
    "clustering": "deepseek-v4-flash",
    "extraction": "deepseek-v4-flash",
    "synthesis": "deepseek-v4-flash",
    "quick": "deepseek-v4-flash",
}

_QUALITY_GATE: dict[TASK, float] = {
    "rca": 0.7,
}


def get_model_for(task: TASK) -> str:
    return _ROUTING.get(task, "deepseek-v4-flash")


def should_escalate_to_pro(confidence: float, task: TASK = "rca") -> bool:
    return confidence < _QUALITY_GATE.get(task, 0.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
