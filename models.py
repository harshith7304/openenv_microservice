from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Optional, Literal, Any

ServiceType = Literal["database", "auth", "payment"]
ActionType = Literal[
    "call_api",
    "inspect_logs",
    "restart_service",
    "update_config",
    "check_status",
    "rollback_deployment"
]

class Action(BaseModel):
    action_type: ActionType
    service: ServiceType
    endpoint: Optional[str] = Field(default=None, description="Endpoint to call for call_api")
    key: Optional[str] = Field(default=None, description="Config key to update")
    value: Optional[str] = Field(default=None, description="Config value to set")

class Observation(BaseModel):
    model_config = ConfigDict(extra="allow")

    api_response: Optional[str] = None
    logs: Optional[str] = None
    service_status: Dict[ServiceType, str] = {}
    reward: float = 0.01
    done: bool = False
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("reward", mode="after")
    @classmethod
    def clamp_reward(cls, v: float) -> float:
        """Ensure reward is STRICTLY in (0, 1) — never 0.0 or 1.0."""
        EPS = 0.01
        if v is None:
            return EPS
        return max(EPS, min(float(v), 0.99))

class ServiceState(BaseModel):
    status: str = "up"
    config: Dict[str, str] = {}
    metrics: Dict[str, float] = {"latency": 10.0, "error_rate": 0.0}

class State(BaseModel):
    system_health: float = 1.0
    services: Dict[ServiceType, ServiceState]
    task_name: str
