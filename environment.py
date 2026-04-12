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

# --- Deterministic noise lines (NO random module!) ---
# These are interleaved with core logs to test agent's ability to filter signal from noise.
NOISE_LINES = {
    "database": [
        "INFO: [pg_stat_statements] Background worker auto-vacuum complete.",
        "WARN: [ConnectionPool] 12% of connections are currently idle.",
        "INFO: [Backup] Daily snapshot synced to S3 successfully.",
    ],
    "auth": [
        "WARN: [auth] Token cache miss rate 12% over last 5 minutes.",
        "INFO: [OAuth2] Refreshed signing keys from JWKS endpoint.",
        "INFO: [SessionManager] Cleaned up 439 orphan sessions.",
    ],
    "payment": [
        "INFO: [StripeWebhook] Received 'charge.succeeded' for evt_x8f9.",
        "WARN: [FraudDetector] Heuristic rules match rate increased by 2%.",
        "INFO: [Payouts] Batch settlement completed.",
    ],
}


def _deterministic_noisy_logs(svc: str, core_log: str) -> str:
    """Injects plausible noise deterministically (no randomness)."""
    noise = NOISE_LINES.get(svc, ["INFO: System health check executed."])
    # Always: first noise line, then core log, then second noise line
    lines = []
    if len(noise) > 0:
        lines.append(noise[0])
    lines.append(core_log)
    if len(noise) > 1:
        lines.append(noise[1])
    return "\n".join(lines)


from openenv.core.rubrics import Rubric

class HackathonGrader(Rubric):
    def forward(self, action: Action, observation: Observation) -> float:
        return observation.reward

class OpenEnv(BaseEnvironment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, init_state_fn=None):
        super().__init__()
        if init_state_fn is None:
            init_state_fn = task_easy
        self.init_state_fn = init_state_fn
        self.rubric = HackathonGrader()
        self.state_obj = None
        self._internal_state = OpenEnvStateType(episode_id=str(uuid4()), step_count=0)
        # --- Session tracking for intelligent grading ---
        self.action_history: list[str] = []
        self.diagnosed_services: set[str] = set()
        self.root_cause_identified: bool = False

        # --- Hard-task phase tracking (deterministic, session-scoped) ---
        self._hard_saw_all_status: bool = False
        self._hard_saw_payment_deploy_evidence: bool = False
        self._hard_saw_db_drift_isolated: bool = False

    def reset(self) -> Observation:
        self.state_obj = self.init_state_fn()
        self._internal_state = OpenEnvStateType(episode_id=str(uuid4()), step_count=0)
        self.action_history = []
        self.diagnosed_services = set()
        self.root_cause_identified = False

        self._hard_saw_all_status = False
        self._hard_saw_payment_deploy_evidence = False
        self._hard_saw_db_drift_isolated = False
        return self._get_obs("Environment reset successfully.", "System initialized.", 0.01, False)

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
        # HARD TASK: deterministic degradation tick while bad deploy runs
        # ============================================================
        if self.state_obj.task_name == "task_hard":
            payment_deploy = self.state_obj.services["payment"].config.get("deployment")
            if payment_deploy == "bad":
                # Simulate memory pressure / latency creep across the stack
                for svc_name in ("payment", "auth", "database"):
                    m = self.state_obj.services[svc_name].metrics
                    m["memory_mb"] = float(m.get("memory_mb", 0.0)) + 75.0
                    m["latency"] = float(m.get("latency", 0.0)) + 150.0
                    m["error_rate"] = min(0.99, float(m.get("error_rate", 0.0)) + 0.02)

        # ============================================================
        # ACTION: update_config
        # ============================================================
        if action.action_type == "update_config":
            if action.service == "database":
                # --- Hard task has a DISTINCT config drift key to fix ---
                if self.state_obj.task_name == "task_hard":
                    if action.key == "pool_mode" and action.value == "safe":
                        if not self.root_cause_identified:
                            action_is_incorrect = True
                            api_res = "Config update rejected: blind fix without diagnosis."
                            logs = "WARNING: Attempted DB drift fix without diagnosing the incident first."
                            self.state_obj.services["database"].config["pool_mode"] = "corrupt"
                        elif self.state_obj.services["payment"].config.get("deployment") == "bad":
                            # Sequencing enforcement: bad payment binary will overwrite DB config on restart loop
                            action_is_incorrect = True
                            api_res = "Config update failed: value keeps getting overwritten."
                            logs = (
                                "ERROR: database.pool_mode was updated, but the payment service (bad deployment) "
                                "overwrote it again during its crash/restart loop. Stop the upstream churn, then retry the drift correction."
                            )
                            self.state_obj.services["database"].config["pool_mode"] = "corrupt"
                        elif not self._hard_saw_db_drift_isolated:
                            action_is_incorrect = True
                            api_res = "Config update rejected: missing phase-2 evidence."
                            logs = "WARNING: Confirm the drift is isolated (inspect database logs after stabilizing payment) before applying the config correction."
                            self.state_obj.services["database"].config["pool_mode"] = "corrupt"
                        else:
                            self.state_obj.services["database"].config["pool_mode"] = "safe"
                            # Stabilize DB + downstream after drift fix
                            self.state_obj.services["database"].metrics.update({"latency": 80.0, "error_rate": 0.10, "memory_mb": 500.0})
                            self.state_obj.services["auth"].metrics.update({"latency": 120.0, "error_rate": 0.10, "memory_mb": 600.0})
                            self.state_obj.services["payment"].metrics.update({"latency": 180.0, "error_rate": 0.10, "memory_mb": 650.0})
                            action_is_correct = True
                            api_res = "Config updated: database.pool_mode = safe"
                            logs = "DB drift corrected. System appears stable; run check_status(all) to verify recovery."
                    elif action.key == "url" and action.value == "valid_db_url":
                        action_is_incorrect = True
                        api_res = "Config update not applicable."
                        logs = "INFO: database.url appears healthy for this incident. Look for effects of a recent release and a secondary DB config drift (pool_mode)."
                    else:
                        action_is_incorrect = True
                        api_res = f"Config update rejected: invalid key/value for {action.service}."
                        logs = f"Expected: database.pool_mode=safe (hard) or database.url=valid_db_url (easy), got: {action.service}.{action.key}={action.value}"

                # --- Easy task: classic DB URL fix ---
                elif action.key == "url" and action.value == "valid_db_url":
                    if not self.root_cause_identified:
                        action_is_incorrect = True
                        api_res = "Config update applied, but without prior diagnosis this is a blind fix."
                        logs = "WARNING: You updated config without inspecting logs first. SRE protocol violation."
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
            else:
                action_is_incorrect = True
                api_res = f"Config update rejected: invalid key/value for {action.service}."
                logs = f"Expected: database.url=valid_db_url or database.pool_mode=safe, got: {action.service}.{action.key}={action.value}"

        # ============================================================
        # ACTION: rollback_deployment
        # ============================================================
        elif action.action_type == "rollback_deployment":
            svc = action.service
            if svc == "payment" and self.state_obj.task_name == "task_hard":
                if not self.root_cause_identified:
                    action_is_incorrect = True
                    api_res = "Rollback rejected."
                    logs = "WARNING: Blind rollback attempted without correlating status sweep + deployment evidence."
                else:
                    self.state_obj.services["payment"].config["deployment"] = "stable"
                    # Partial recovery: memory pressure drops, but DB drift still breaks stability
                    self.state_obj.services["payment"].metrics.update({"latency": 900.0, "error_rate": 0.30, "memory_mb": 700.0})
                    self.state_obj.services["auth"].metrics.update({"latency": 1400.0, "error_rate": 0.35, "memory_mb": 850.0})
                    self.state_obj.services["database"].metrics.update({"latency": 1700.0, "error_rate": 0.40, "memory_mb": 900.0})
                    action_is_correct = True
                    api_res = "Deployment rolled back to previous stable version."
                    logs = "Rollback successful for payment. Memory pressure reduced; database drift remains to be fixed."

            elif svc == "database":
                if not self.root_cause_identified:
                    action_is_incorrect = True
                    api_res = "Rollback rejected."
                    logs = "WARNING: Blind rollback attempted without diagnosing root cause first. SRE protocol violation."
                else:
                    self.state_obj.services["database"].config["url"] = "valid_db_url"
                    self.state_obj.services["database"].metrics["latency"] = 10.0
                    action_is_correct = True
                    api_res = "Deployment rolled back to previous stable version."
                    logs = "Rollback successful. DB config restored to valid_db_url. Latency normalized."
            else:
                action_is_incorrect = True
                api_res = f"Rollback failed for {svc}."
                logs = f"No previous stable deployment found for {svc}."

        # ============================================================
        # ACTION: restart_service
        # ============================================================
        elif action.action_type == "restart_service":
            svc = action.service

            # Penalty for restarting a healthy service
            if svc in self.state_obj.services:
                svc_state = self.state_obj.services[svc]
                svc_metrics = svc_state.metrics or {}
                lat_ok = svc_metrics.get("latency", 0) < 1000
                err_ok = svc_metrics.get("error_rate", 0) < 0.5
                url_ok = svc_state.config.get("url", "valid_db_url") == "valid_db_url"

                if svc_state.status == "up" and lat_ok and err_ok and url_ok:
                    action_is_incorrect = True
                    api_res = f"400 Bad Request — {svc} is already healthy."
                    logs = f"WARNING: Restarted healthy service ({svc}). 500 active user sessions dropped!"
                    reward, done = grade_step(
                        state=self.state_obj,
                        action_is_correct=False,
                        action_is_incorrect=True,
                        root_cause_identified=self.root_cause_identified,
                        num_diagnosed=len(self.diagnosed_services),
                        is_repeated=is_repeated,
                    )
                    return self._get_obs(api_res, logs, reward, done)

            # Dependency enforcement
            if svc == "payment":
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

            if svc == "all":
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = "inspect_logs does not support service='all'. Use check_status(all) for a broad sweep, then inspect_logs on a specific service."
                reward, done = grade_step(
                    state=self.state_obj,
                    action_is_correct=False,
                    action_is_incorrect=True,
                    root_cause_identified=self.root_cause_identified,
                    num_diagnosed=len(self.diagnosed_services),
                    is_repeated=is_repeated,
                )
                return self._get_obs(api_res, logs, reward, done)

            if self.state_obj.task_name == "task_easy":
                if svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    self.root_cause_identified = True
                    core_log = "FATAL: Invalid database URL 'invalid_url_123'. Expected: valid_db_url. All downstream services (auth, payment) are unreachable."
                elif svc in ("auth", "payment"):
                    action_is_correct = True
                    self.diagnosed_services.add(svc)
                    core_log = f"ERROR: {svc} cannot connect to database. Connection refused at 'invalid_url_123'. Root cause: database misconfiguration."
                    if "database" not in self.diagnosed_services:
                        core_log += " Hint: inspect database logs first."
                else:
                    core_log = f"INFO: {svc} logs nominal."

            elif self.state_obj.task_name == "task_medium":
                if svc == "auth":
                    action_is_correct = True
                    self.diagnosed_services.add("auth")
                    self.root_cause_identified = True
                    core_log = "CRITICAL: Auth service crashed — OOM exception. Status=DOWN. Requires restart. Payment is blocked pending auth recovery."
                elif svc == "payment":
                    action_is_correct = True
                    self.diagnosed_services.add("payment")
                    core_log = "ERROR: Payment gateway cannot process — auth dependency is DOWN. Fix auth first."
                elif svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    core_log = "INFO: Database running normally. No errors in last 24h."
                else:
                    core_log = f"INFO: {svc} logs nominal."

            elif self.state_obj.task_name == "task_hard":
                if svc == "payment":
                    action_is_correct = True
                    self.diagnosed_services.add("payment")
                    # Phase 1 evidence: deployment artifact signature
                    self._hard_saw_payment_deploy_evidence = True
                    deployed_at = "2026-04-12T09:14:27Z"
                    build_id = "pay-2.7.13-bad"
                    core_log = (
                        f"CRITICAL: Release marker observed for payment: build={build_id} deployed_at={deployed_at}. "
                        "Heap usage is trending upward with frequent GC cycles and growing request queue depth. "
                        "Symptoms began within minutes of this release and correlate with system-wide latency/error spikes."
                    )
                    # Root cause gate: requires BOTH broad status sweep and deploy evidence
                    if self._hard_saw_all_status:
                        self.root_cause_identified = True

                elif svc == "database":
                    action_is_correct = True
                    self.diagnosed_services.add("database")
                    lat = self.state_obj.services["database"].metrics.get("latency", 0)
                    pool_mode = self.state_obj.services["database"].config.get("pool_mode")
                    payment_deploy = self.state_obj.services["payment"].config.get("deployment")
                    if payment_deploy == "bad":
                        core_log = (
                            f"WARN: DB latency={lat}ms. Observed drift in a runtime config value: pool_mode='{pool_mode}'. "
                            "There are repeated write attempts during the payment crash/restart loop, and the value flips back intermittently. "
                            "If you try to correct this while upstream churn continues, the change may not persist."
                        )
                    else:
                        self._hard_saw_db_drift_isolated = True
                        core_log = (
                            f"WARN: DB latency={lat}ms. pool_mode is still '{pool_mode}', but upstream churn has stopped and the value is now stable. "
                            "This looks like an isolated drift that should be safe to correct."
                        )

                elif svc == "auth":
                    action_is_correct = True
                    self.diagnosed_services.add("auth")
                    mem = self.state_obj.services["auth"].metrics.get("memory_mb", 0)
                    core_log = (
                        f"ERROR: Auth degraded. memory_mb={mem}. Elevated error rate due to upstream instability. "
                        "Symptoms consistent with cascading pressure from another service (not an auth config issue)."
                    )
                else:
                    core_log = f"INFO: {svc} logs nominal."

            logs = _deterministic_noisy_logs(svc, core_log)
            api_res = "Logs retrieved successfully."

        # ============================================================
        # ACTION: check_status
        # ============================================================
        elif action.action_type == "check_status":
            svc = action.service
            if svc == "all":
                parts: list[str] = []
                any_bad = False
                for name, svc_state in self.state_obj.services.items():
                    st = svc_state.status
                    lat = svc_state.metrics.get("latency", 0)
                    err = svc_state.metrics.get("error_rate", 0)
                    mem = svc_state.metrics.get("memory_mb", 0)
                    parts.append(f"{name}: status={st}, latency={lat}ms, error_rate={err}, memory_mb={mem}")
                    if st == "down" or lat > 1000 or err > 0.5:
                        any_bad = True
                api_res = "\n".join(parts)
                logs = "Health sweep complete for all services."
                if any_bad:
                    action_is_correct = True

                if self.state_obj.task_name == "task_hard":
                    # Phase 1 gate evidence
                    self._hard_saw_all_status = True
                    # Order-independent RCA gate (requires BOTH observations)
                    if self._hard_saw_payment_deploy_evidence:
                        self.root_cause_identified = True
                    # Phase 3 verification latch
                    payment_stable = self.state_obj.services["payment"].config.get("deployment") == "stable"
                    pool_ok = self.state_obj.services["database"].config.get("pool_mode") == "safe"
                    verified = float(self.state_obj.services["payment"].metrics.get("verified", 0.0)) >= 1.0
                    if payment_stable and pool_ok and not verified:
                        self.state_obj.services["payment"].metrics["verified"] = 1.0
                        logs += " Verification recorded: system observed stable post-fix."
                        action_is_correct = True

            elif svc in self.state_obj.services:
                st = self.state_obj.services[svc].status
                lat = self.state_obj.services[svc].metrics.get("latency", 0)
                err = self.state_obj.services[svc].metrics.get("error_rate", 0)
                mem = self.state_obj.services[svc].metrics.get("memory_mb", 0)
                api_res = f"{svc}: status={st}, latency={lat}ms, error_rate={err}, memory_mb={mem}"
                logs = f"Health check complete for {svc}."
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
            if action.service == "all":
                action_is_incorrect = True
                api_res = "Unknown service."
                logs = "call_api does not support service='all'."
            else:
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
