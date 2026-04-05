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
    Reward always in [0.0, 1.0].

    Reward signal design:
    - Diagnostic actions get escalating rewards based on how many services diagnosed
    - Root cause identification gets a bonus
    - Incorrect/destructive actions get 0.0
    - Repeated actions get diminishing returns
    - Full system recovery gets 1.0
    """

    # --- Update system health based on current state ---
    if state.task_name == "task_easy":
        if state.services["database"].config.get("url") == "valid_db_url":
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.system_health = 1.0
        else:
            state.system_health = 0.0

    elif state.task_name == "task_medium":
        if state.services["auth"].status == "up":
            state.services["payment"].status = "up"
            state.system_health = 1.0
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
            state.system_health = 1.0
        elif db_url_ok:
            state.system_health = 0.5
        else:
            state.system_health = 0.1

    # --- Check episode done condition ---
    all_operational = all(s.status == "up" for s in state.services.values())
    done = state.system_health > 0.9 and all_operational

    # --- Compute reward strictly in [0.0, 1.0] ---
    if done:
        # Full recovery bonus — higher if root cause was identified first
        reward = 1.0 if root_cause_identified else 0.8
    elif action_is_incorrect:
        # Destructive or useless action
        reward = 0.0
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
            reward = round(min(base + rca_bonus, 0.7), 2)
    else:
        # Neutral action — minimal signal
        reward = round(state.system_health * 0.05, 2)

    return reward, done
