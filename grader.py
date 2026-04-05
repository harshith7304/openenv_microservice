try:
    from .models import State
except ImportError:
    from models import State


def grade_step(state: State, action_is_correct: bool, action_is_incorrect: bool) -> tuple[float, bool]:
    """
    Deterministic grader - reward always in [0.0, 1.0].
    Partial signals provided throughout episode.
    """
    # --- Update system health based on state ---
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
        if (state.services["database"].config.get("url") == "valid_db_url"
                and state.services["database"].metrics.get("latency", 9999) < 100):
            state.services["database"].metrics["latency"] = 10.0
            state.services["auth"].metrics["latency"] = 10.0
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.system_health = 1.0
        elif state.services["database"].config.get("url") == "valid_db_url":
            state.system_health = 0.5
        else:
            state.system_health = 0.1

    all_operational = all(s.status == "up" for s in state.services.values())
    done = state.system_health > 0.9 and all_operational

    # --- Compute reward strictly in [0.0, 1.0] ---
    if done:
        reward = 1.0
    elif action_is_correct:
        # Partial progress reward (diagnostic steps that advance understanding)
        reward = round(min(0.3 + state.system_health * 0.4, 0.8), 2)
    elif action_is_incorrect:
        # Penalty for destructive/useless actions
        reward = 0.0
    else:
        # Neutral exploratory action - small signal based on health
        reward = round(state.system_health * 0.1, 2)

    return reward, done
