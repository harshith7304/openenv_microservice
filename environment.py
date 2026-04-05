from uuid import uuid4
from openenv.core.env_server.interfaces import Environment as BaseEnvironment
from openenv.core.env_server.types import State as OpenEnvStateType

try:
    from .models import Action, Observation, State
    from .tasks import task_easy, task_medium, task_hard
    from .grader import grade_step
except ImportError:
    from models import Action, Observation, State
    from tasks import task_easy, task_medium, task_hard
    from grader import grade_step

TASK_MAP = {
    "task_easy": task_easy,
    "task_medium": task_medium,
    "task_hard": task_hard,
}

class OpenEnv(BaseEnvironment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, init_state_fn=None):
        if init_state_fn is None:
            init_state_fn = task_easy
        self.init_state_fn = init_state_fn
        self.state_obj = None
        self._internal_state = OpenEnvStateType(episode_id=str(uuid4()), step_count=0)

    def reset(self) -> Observation:
        self.state_obj = self.init_state_fn()
        self._internal_state = OpenEnvStateType(episode_id=str(uuid4()), step_count=0)
        return self._get_obs("Environment reset successfully.", "System initialized.", 0.0, False)

    def _get_obs(self, api_res: str, logs: str, reward: float, done: bool) -> Observation:
        if self.state_obj:
            svc_status = {k: v.status for k, v in self.state_obj.services.items()}
        else:
            svc_status = {}
        return Observation(
            api_response=api_res,
            logs=logs,
            service_status=svc_status,
            reward=reward,
            done=done,
            metadata={
                "task": getattr(self.state_obj, "task_name", "unknown"),
                "system_health": getattr(self.state_obj, "system_health", 0.0),
                "step": self._internal_state.step_count,
            }
        )

    def step(self, action: Action) -> Observation:  # type: ignore[override]
        # Auto-initialize if reset() hasn't been called yet
        if self.state_obj is None:
            self.reset()

        self._internal_state.step_count += 1

        action_is_correct = False
        action_is_incorrect = False
        api_res = ""
        logs = ""

        if action.action_type == "update_config":
            if action.service == "database" and action.key == "url" and action.value == "valid_db_url":
                self.state_obj.services["database"].config["url"] = "valid_db_url"
                self.state_obj.services["database"].metrics["latency"] = 10.0
                action_is_correct = True
                api_res = "Config updated: database.url = valid_db_url"
                logs = "DB config accepted. Service attempting restart."
            else:
                action_is_incorrect = True
                api_res = f"Config update rejected: invalid key/value for {action.service}."
                logs = f"Expected: database.url=valid_db_url, got: {action.service}.{action.key}={action.value}"

        elif action.action_type == "restart_service":
            svc = action.service
            if svc == "auth" and self.state_obj.task_name == "task_medium":
                self.state_obj.services["auth"].status = "up"
                action_is_correct = True
                api_res = "auth restarted successfully."
                logs = "Auth service is back online. Payment dependencies restored."
            elif svc in self.state_obj.services:
                if self.state_obj.services[svc].config.get("url", "valid") != "valid_db_url" and svc == "database":
                    action_is_incorrect = True
                    api_res = f"{svc} restart failed: config is still invalid."
                    logs = f"Cannot restart {svc} — misconfiguration still present."
                else:
                    self.state_obj.services[svc].status = "up"
                    api_res = f"{svc} restarted."
                    logs = f"Service {svc} is now running."
            else:
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = f"No service named '{svc}'."

        elif action.action_type == "inspect_logs":
            svc = action.service
            if self.state_obj.task_name == "task_easy" and svc == "database":
                action_is_correct = True
                logs = "FATAL: Invalid database URL 'invalid_url_123'. Expected format: valid_db_url. All downstream services (auth, payment) are unreachable."
            elif self.state_obj.task_name == "task_easy" and svc in ("auth", "payment"):
                action_is_correct = True
                logs = f"ERROR: {svc} cannot connect to database. Connection refused at 'invalid_url_123'."
            elif self.state_obj.task_name == "task_medium" and svc == "auth":
                action_is_correct = True
                logs = "CRITICAL: Auth service crashed due to OOM exception. Status=DOWN. Payment service is blocked pending auth recovery."
            elif self.state_obj.task_name == "task_medium" and svc == "payment":
                action_is_correct = True
                logs = "ERROR: Payment gateway cannot process — auth dependency is DOWN."
            elif self.state_obj.task_name == "task_hard" and svc == "database":
                action_is_correct = True
                lat = self.state_obj.services["database"].metrics.get("latency", 0)
                logs = f"WARN: DB query latency={lat}ms (threshold=100ms). URL='{self.state_obj.services['database'].config.get('url')}'. Auth service retry storm detected."
            elif self.state_obj.task_name == "task_hard" and svc == "auth":
                action_is_correct = True
                logs = "ERROR: Auth retry loop — 5000 retries/sec against slow DB. Payment gateway timeout cascade."
            else:
                logs = f"INFO: {svc} logs nominal. No immediate errors detected."
            api_res = "Logs retrieved successfully."

        elif action.action_type == "check_status":
            svc = action.service
            if svc in self.state_obj.services:
                st = self.state_obj.services[svc].status
                health = self.state_obj.services[svc].metrics.get("latency", 0)
                api_res = f"{svc}: status={st}, latency={health}ms"
                logs = f"Health check complete for {svc}."
                # Correct if checking a broken service (useful diagnostic)
                if st == "down" or health > 1000:
                    action_is_correct = True
            else:
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = "No such service exists."

        elif action.action_type == "call_api":
            health = self.state_obj.system_health
            if health < 0.5:
                api_res = "500 Internal Server Error — system health critical."
                logs = f"API call to {action.service}{('/' + action.endpoint) if action.endpoint else ''} failed."
            else:
                api_res = "200 OK"
                logs = f"API call to {action.service}{('/' + action.endpoint) if action.endpoint else ''} succeeded."

        else:
            action_is_incorrect = True
            api_res = "Unknown action type."
            logs = f"Action '{action.action_type}' is not supported."

        reward, done = grade_step(self.state_obj, action_is_correct, action_is_incorrect)
        return self._get_obs(api_res, logs, reward, done)

    @property
    def state(self) -> OpenEnvStateType:
        return self._internal_state

    def internal_state(self) -> State:
        return self.state_obj
