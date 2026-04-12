try:
    from .models import State
except ImportError:
    from models import State


def grade_step(
    state: State,
    action_is_correct: bool,
    action_is_incorrect: bool,
    root_cause_identified: bool = False,
    num_diagnosed: int = 0,
    is_repeated: bool = False,
) -> tuple[float, bool]:
    """
    Deterministic grader with escalating partial rewards.
    Reward STRICTLY in (0.0, 1.0) — never exactly 0.0 or 1.0.

    Reward signal design:
    - Diagnostic actions get escalating rewards based on how many services diagnosed
    - Root cause identification gets a bonus
    - Incorrect/destructive actions get 0.01 (minimum nonzero)
    - Repeated actions get diminishing returns
    - Full system recovery gets 0.99 (maximum below 1.0)
    """

    # --- Update system health based on current state ---
    if state.task_name == "task_easy":
        if state.services["database"].config.get("url") == "valid_db_url":
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.system_health = 0.99
        else:
            state.system_health = 0.1

    elif state.task_name == "task_medium":
        if state.services["auth"].status == "up":
            state.services["payment"].status = "up"
            state.system_health = 0.99
        else:
            state.system_health = 0.3

    elif state.task_name == "task_hard":
        payment_stable = state.services["payment"].config.get("deployment") == "stable"
        pool_ok = state.services["database"].config.get("pool_mode") == "safe"
        verified = float(state.services["payment"].metrics.get("verified", 0.0)) >= 1.0

        if payment_stable and pool_ok and verified:
            # Full recovery after explicit verification
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.services["database"].metrics.update({"latency": 30.0, "error_rate": 0.01})
            state.services["auth"].metrics.update({"latency": 35.0, "error_rate": 0.01})
            state.services["payment"].metrics.update({"latency": 40.0, "error_rate": 0.01})
            state.system_health = 0.99
        elif payment_stable and pool_ok:
            # Fixes applied but not yet verified (verification is REQUIRED for done)
            state.system_health = 0.85
        elif payment_stable:
            # Rollback helped, but drift remains
            state.system_health = 0.50
        else:
            # Bad deployment still running
            state.system_health = 0.10

    # --- Check episode done condition ---
    all_operational = all(s.status == "up" for s in state.services.values())
    done = state.system_health > 0.9 and all_operational

    # --- Compute reward STRICTLY in (0.0, 1.0) ---
    if done:
        # Full recovery — higher if root cause was identified first
        reward = 0.99 if root_cause_identified else 0.80
    elif action_is_incorrect:
        # Destructive or useless action — minimum nonzero penalty
        reward = 0.01
    elif action_is_correct:
        if is_repeated:
            # Repeated correct action — diminishing returns
            reward = 0.05
        else:
            # Escalating reward based on diagnostic progress
            # First diagnosis: 0.15, second: 0.25, third: 0.35
            base = 0.05 + (num_diagnosed * 0.10)
            # Root cause bonus
            rca_bonus = 0.15 if root_cause_identified else 0.0
            reward = min(base + rca_bonus, 0.70)
    else:
        # Neutral action — minimal signal
        reward = max(state.system_health * 0.05, 0.01)

    # --- FINAL SAFETY CLAMP: ensure strictly (0, 1) ---
    EPS = 0.01
    reward = round(max(EPS, min(reward, 0.99)), 2)

    return reward, done
