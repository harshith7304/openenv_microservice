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
        # --- Session tracking for intelligent grading ---
        self.action_history: list[str] = []
        self.diagnosed_services: set[str] = set()  # services whose logs have been inspected
        self.root_cause_identified: bool = False

    def reset(self) -> Observation:
        self.state_obj = self.init_state_fn()
        self._internal_state = OpenEnvStateType(episode_id=str(uuid4()), step_count=0)
        self.action_history = []
        self.diagnosed_services = set()
        self.root_cause_identified = False
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
                "root_cause_identified": self.root_cause_identified,
                "diagnosed_services": list(self.diagnosed_services),
            }
        )

    def step(self, action: Action) -> Observation:  # type: ignore[override]
        # Auto-initialize if reset() hasn't been called yet
        if self.state_obj is None:
            self.reset()

        self._internal_state.step_count += 1

        action_key = f"{action.action_type}:{action.service}"
        is_repeated = action_key in self.action_history
        self.action_history.append(action_key)

        action_is_correct = False
        action_is_incorrect = False
        api_res = ""
        logs = ""

        # ============================================================
        # ACTION: update_config
        # ============================================================
        if action.action_type == "update_config":
            if action.service == "database" and action.key == "url" and action.value == "valid_db_url":
                # --- Dependency gate: must have diagnosed root cause first ---
                if not self.root_cause_identified:
                    action_is_incorrect = True
                    api_res = "Config update applied, but without prior diagnosis this is a blind fix."
                    logs = "WARNING: You updated config without inspecting logs first. SRE protocol violation."
                    # Still apply the fix, but penalize score
                    self.state_obj.services["database"].config["url"] = "valid_db_url"
                    self.state_obj.services["database"].metrics["latency"] = 10.0
                else:
                    self.state_obj.services["database"].config["url"] = "valid_db_url"
                    self.state_obj.services["database"].metrics["latency"] = 10.0
                    action_is_correct = True
                    api_res = "Config updated: database.url = valid_db_url"
                    logs = "DB config accepted. Latency normalized. Service attempting restart."
            else:
                action_is_incorrect = True
                api_res = f"Config update rejected: invalid key/value for {action.service}."
                logs = f"Expected: database.url=valid_db_url, got: {action.service}.{action.key}={action.value}"

        # ============================================================
        # ACTION: restart_service
        # ============================================================
        elif action.action_type == "restart_service":
            svc = action.service

            # --- Dependency enforcement ---
            if svc == "payment":
                # Payment depends on auth + database
                auth_up = self.state_obj.services["auth"].status == "up"
                db_up = self.state_obj.services["database"].status == "up"
                if not (auth_up and db_up):
                    action_is_incorrect = True
                    deps = []
                    if not db_up: deps.append("database")
                    if not auth_up: deps.append("auth")
                    api_res = f"payment restart failed: dependencies not met."
                    logs = f"Cannot restart payment — {', '.join(deps)} must be up first. Fix upstream services."
                else:
                    self.state_obj.services[svc].status = "up"
                    action_is_correct = True
                    api_res = "payment restarted successfully."
                    logs = "Payment gateway is processing transactions normally."

            elif svc == "auth":
                # Auth depends on database
                db_url_valid = self.state_obj.services["database"].config.get("url") == "valid_db_url"
                db_up = self.state_obj.services["database"].status == "up"
                if not db_url_valid:
                    action_is_incorrect = True
                    api_res = "auth restart failed: database config is invalid."
                    logs = "Auth service crashed on startup — cannot connect to DB at 'invalid_url_123'."
                elif self.state_obj.task_name == "task_medium" or db_up:
                    self.state_obj.services["auth"].status = "up"
                    action_is_correct = True
                    api_res = "auth restarted successfully."
                    logs = "Auth service is back online. Payment dependencies restored."
                else:
                    action_is_incorrect = True
                    api_res = "auth restart failed: database is still down."
                    logs = "Auth cannot initialize — database service must be running."

            elif svc == "database":
                db_url_valid = self.state_obj.services["database"].config.get("url") == "valid_db_url"
                if not db_url_valid:
                    action_is_incorrect = True
                    api_res = "database restart failed: config is still invalid."
                    logs = "Cannot restart database — misconfiguration still present. Fix url first."
                else:
                    self.state_obj.services["database"].status = "up"
                    action_is_correct = True
                    api_res = "database restarted successfully."
                    logs = "Database accepting connections. Latency nominal."
            else:
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = f"No service named '{svc}'."

        # ============================================================
        # ACTION: inspect_logs (THE KEY DIAGNOSTIC ACTION)
        # ============================================================
        elif action.action_type == "inspect_logs":
            svc = action.service

            if self.state_obj.task_name == "task_easy":
                if svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    self.root_cause_identified = True
                    logs = "FATAL: Invalid database URL 'invalid_url_123'. Expected: valid_db_url. All downstream services (auth, payment) are unreachable."
                elif svc in ("auth", "payment"):
                    action_is_correct = True
                    self.diagnosed_services.add(svc)
                    logs = f"ERROR: {svc} cannot connect to database. Connection refused at 'invalid_url_123'. Root cause: database misconfiguration."
                    if "database" not in self.diagnosed_services:
                        logs += " Hint: inspect database logs first."
                else:
                    logs = f"INFO: {svc} logs nominal."

            elif self.state_obj.task_name == "task_medium":
                if svc == "auth":
                    action_is_correct = True
                    self.diagnosed_services.add("auth")
                    self.root_cause_identified = True
                    logs = "CRITICAL: Auth service crashed — OOM exception. Status=DOWN. Requires restart. Payment is blocked pending auth recovery."
                elif svc == "payment":
                    action_is_correct = True
                    self.diagnosed_services.add("payment")
                    logs = "ERROR: Payment gateway cannot process — auth dependency is DOWN. Fix auth first."
                elif svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    logs = "INFO: Database running normally. No errors in last 24h."
                else:
                    logs = f"INFO: {svc} logs nominal."

            elif self.state_obj.task_name == "task_hard":
                if svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    lat = self.state_obj.services["database"].metrics.get("latency", 0)
                    url = self.state_obj.services["database"].config.get("url")
                    logs = f"WARN: DB query latency={lat}ms (threshold=100ms). Config URL='{url}'. Auth service retry storm detected. ROOT CAUSE: invalid DB URL causing connection pool exhaustion."
                    if "auth" in self.diagnosed_services:
                        self.root_cause_identified = True
                elif svc == "auth":
                    action_is_correct = True
                    self.diagnosed_services.add("auth")
                    logs = "ERROR: Auth retry loop — 5000 retries/sec against slow DB. Memory pressure building. Payment gateway timeout cascade imminent."
                    if "database" in self.diagnosed_services:
                        self.root_cause_identified = True
                elif svc == "payment":
                    action_is_correct = True
                    self.diagnosed_services.add("payment")
                    logs = "ERROR: Payment service timeout. All transactions failing. Upstream auth dependency unresponsive."
                else:
                    logs = f"INFO: {svc} logs nominal."

            api_res = "Logs retrieved successfully."

        # ============================================================
        # ACTION: check_status
        # ============================================================
        elif action.action_type == "check_status":
            svc = action.service
            if svc in self.state_obj.services:
                st = self.state_obj.services[svc].status
                lat = self.state_obj.services[svc].metrics.get("latency", 0)
                err = self.state_obj.services[svc].metrics.get("error_rate", 0)
                api_res = f"{svc}: status={st}, latency={lat}ms, error_rate={err}"
                logs = f"Health check complete for {svc}."
                # Correct if checking a broken service
                if st == "down" or lat > 1000 or err > 0.5:
                    action_is_correct = True
            else:
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = "No such service exists."

        # ============================================================
        # ACTION: call_api
        # ============================================================
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

        # --- Penalize repeated identical actions ---
        if is_repeated and not action_is_correct:
            action_is_incorrect = True
            logs += " [REPEATED ACTION — no new information gained]"

        reward, done = grade_step(
            state=self.state_obj,
            action_is_correct=action_is_correct,
            action_is_incorrect=action_is_incorrect,
            root_cause_identified=self.root_cause_identified,
            num_diagnosed=len(self.diagnosed_services),
            is_repeated=is_repeated,
        )
        return self._get_obs(api_res, logs, reward, done)

    @property
    def state(self) -> OpenEnvStateType:
        return self._internal_state

    def internal_state(self) -> State:
        return self.state_obj
