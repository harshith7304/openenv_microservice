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
            state.system_health = 0.01

    elif state.task_name == "task_medium":
        if state.services["auth"].status == "up":
            state.services["payment"].status = "up"
            state.system_health = 0.99
        else:
            state.system_health = 0.3

    elif state.task_name == "task_hard":
        db_url_ok = state.services["database"].config.get("url") == "valid_db_url"
        db_lat_ok = state.services["database"].metrics.get("latency", 9999) < 100
        if db_url_ok and db_lat_ok:
            state.services["database"].metrics["latency"] = 10.0
            state.services["auth"].metrics["latency"] = 10.0
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.system_health = 0.99
        elif db_url_ok:
            state.system_health = 0.5
        else:
            state.system_health = 0.1

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
            reward = round(min(base + rca_bonus, 0.70), 2)
    else:
        # Neutral action — minimal signal
        reward = max(round(state.system_health * 0.05, 2), 0.01)

    # --- FINAL SAFETY CLAMP: ensure strictly (0, 1) ---
    reward = max(0.01, min(reward, 0.99))

    return reward, done
