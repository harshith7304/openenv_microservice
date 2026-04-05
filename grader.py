try:
    from .models import State
except ImportError:
    from models import State

def grade_step(state: State, action_is_correct: bool, action_is_incorrect: bool) -> tuple[float, bool]:
    # Evaluate health deterministically based on states
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
        if state.services["database"].config.get("url") == "valid_db_url":
            state.services["database"].metrics["latency"] = 10.0
            state.services["auth"].metrics["latency"] = 10.0
            state.services["database"].status = "up"
            state.services["auth"].status = "up"
            state.services["payment"].status = "up"
            state.system_health = 1.0
        else:
            state.system_health = 0.1

    all_operational = all(s.status == "up" for s in state.services.values())
    done = state.system_health > 0.9 and all_operational

    # Calculate rewards
    step_reward = 0.0
    if action_is_correct:
        step_reward += 0.2
    if action_is_incorrect:
        step_reward -= 0.1

    final_reward = 0.0
    if done:
        final_reward = 1.0
    elif state.system_health >= 0.5:
        final_reward = 0.5

    total_reward = step_reward + final_reward
    return total_reward, done
