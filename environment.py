from uuid import uuid4
from openenv.core.env_server.interfaces import Environment as BaseEnvironment
from openenv.core.env_server.types import State as OpenEnvStateType

try:
    from ..models import Action, Observation, State
    from ..tasks import task_easy
    from ..grader import grade_step
except ImportError:
    from models import Action, Observation, State
    from tasks import task_easy
    from grader import grade_step

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
            metadata={"task": getattr(self.state_obj, "task_name", "unknown")}
        )

    def step(self, action: Action) -> Observation:  # type: ignore[override]
        self._internal_state.step_count += 1
        action_is_correct = False
        action_is_incorrect = False
        api_res = ""
        logs = ""

        if action.action_type == "update_config":
            if action.service == "database" and action.key == "url" and action.value == "valid_db_url":
                self.state_obj.services["database"].config["url"] = "valid_db_url"
                action_is_correct = True
                api_res = "Config updated successfully."
                logs = "Database url updated. Restart might be required."
            else:
                action_is_incorrect = True
                api_res = "Config update failed."
                logs = f"Invalid config key/value for {action.service}."

        elif action.action_type == "restart_service":
            if action.service == "auth" and self.state_obj.task_name == "task_medium":
                self.state_obj.services["auth"].status = "up"
                action_is_correct = True
                api_res = "Service restarted successfully."
                logs = "Auth service came up cleanly."
            else:
                self.state_obj.services[action.service].status = "up"
                api_res = f"Service {action.service} restarted."
                logs = f"Restarted {action.service}."

        elif action.action_type == "inspect_logs":
            if self.state_obj.task_name == "task_easy" and action.service == "database":
                logs = "FATAL: Incorrect Database URL format (invalid_url_123)."
            elif self.state_obj.task_name == "task_medium" and action.service == "auth":
                logs = "ERROR: Auth service is down gracefully."
            elif self.state_obj.task_name == "task_hard" and action.service == "database":
                logs = "WARN: DB query timeout due to slow response (cascading failure)."
            else:
                logs = f"Standard logs for {action.service}: No immediate errors found."
            api_res = "Logs retrieved."
            
        elif action.action_type == "check_status":
            st = self.state_obj.services[action.service].status
            api_res = f"Status: {st}"
            logs = f"Health check executed for {action.service}."
            
        elif action.action_type == "call_api":
            api_res = "Endpoint response: 500 Internal Server Error" if self.state_obj.system_health < 0.9 else "Endpoint response: 200 OK"
            logs = f"API call made to {action.service} {action.endpoint}."

        else:
            action_is_incorrect = True
            api_res = "Unknown action."
            logs = "Action not supported."

        reward, done = grade_step(self.state_obj, action_is_correct, action_is_incorrect)
        
        return self._get_obs(api_res, logs, reward, done)

    @property
    def state(self) -> OpenEnvStateType:
        return self._internal_state

    def internal_state(self) -> State:
        return self.state_obj
