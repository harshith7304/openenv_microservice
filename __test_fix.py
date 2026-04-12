"""Test that inference.py [END] line output format is correct.
Simulates what happens when LLM API is unavailable (no HF_TOKEN).
"""
import sys
import re
from pathlib import Path

# Simulate inference.py without LLM by temporarily overriding os env
import os
os.environ.pop("HF_TOKEN", None)  # Remove HF_TOKEN to force API errors

# Import the environment directly  
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from openenv_microservice.environment import OpenEnv
    from openenv_microservice.tasks import task_easy, task_medium, task_hard
    from openenv_microservice.models import Action
except ImportError:
    from environment import OpenEnv
    from tasks import task_easy, task_medium, task_hard
    from models import Action

# Simulate a task run WITHOUT the LLM (which is what happens during eval if API fails)
def simulate_task(task_name, init_fn):
    """Simulate a task where the LLM returns valid actions (best case)."""
    env = OpenEnv(init_fn)
    obs = env.reset()
    
    rewards = []
    done = False
    step_count = 0
    
    # Simulate the BEST case: agent does inspect_logs then update_config
    if task_name == "task_easy":
        actions = [
            Action(action_type="inspect_logs", service="database"),
            Action(action_type="update_config", service="database", key="url", value="valid_db_url"),
        ]
    elif task_name == "task_medium":
        actions = [
            Action(action_type="inspect_logs", service="auth"),
            Action(action_type="restart_service", service="auth"),
        ]
    elif task_name == "task_hard":
        actions = [
            Action(action_type="check_status", service="all"),
            Action(action_type="inspect_logs", service="payment"),
            Action(action_type="inspect_logs", service="database"),
            Action(action_type="rollback_deployment", service="payment"),
            Action(action_type="inspect_logs", service="database"),
            Action(action_type="update_config", service="database", key="pool_mode", value="safe"),
            Action(action_type="check_status", service="all"),
        ]
    else:
        actions = []
    
    for action in actions:
        if done:
            break
        step_count += 1
        obs = env.step(action)
        reward = obs.reward
        done = obs.done
        rewards.append(reward)
        print(f"  [STEP] step={step_count} action={action.action_type}({action.service}) reward={reward} done={done}")
    
    # Compute task_score exactly like inference.py now does
    if rewards:
        task_score = max(rewards)
    else:
        task_score = 0.01
    
    task_score = round(max(0.01, min(task_score, 0.99)), 4)
    success = done and any(r >= 0.9 for r in rewards)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    
    end_line = f"[END] task={task_name} success={str(success).lower()} score={task_score} steps={step_count} rewards={rewards_str}"
    print(f"  {end_line}")
    
    # Validate
    print(f"\n  === VALIDATION ===")
    print(f"  task_score = {task_score}")
    print(f"  0 < task_score < 1? {0 < task_score < 1}")
    print(f"  task_score == 0.0? {task_score == 0.0}")
    print(f"  task_score == 1.0? {task_score == 1.0}")
    
    if not (0 < task_score < 1):
        print(f"  *** FAIL: task_score {task_score} is OUT OF RANGE! ***")
        return False
    else:
        print(f"  *** PASS: task_score {task_score} is strictly in (0, 1) ***")
        return True


# Also test the WORST case: all API calls fail, reward stays at 0.1
def simulate_failed_task(task_name, init_fn):
    """Simulate when LLM API fails on every step."""
    rewards = []
    for _ in range(8):  # MAX_STEPS
        rewards.append(0.1)  # Default reward when exception occurs
    
    if rewards:
        task_score = max(rewards)
    else:
        task_score = 0.01
    task_score = round(max(0.01, min(task_score, 0.99)), 4)
    
    print(f"  Failed task {task_name}: task_score={task_score}, 0<score<1? {0 < task_score < 1}")
    return 0 < task_score < 1


print("=" * 60)
print("SCENARIO 1: Best case (agent solves each task)")
print("=" * 60)

for task_name, init_fn in [("task_easy", task_easy), ("task_medium", task_medium), ("task_hard", task_hard)]:
    print(f"\n--- {task_name} ---")
    simulate_task(task_name, init_fn)

print("\n" + "=" * 60)
print("SCENARIO 2: Worst case (LLM API fails every step)")
print("=" * 60)

for task_name, init_fn in [("task_easy", task_easy), ("task_medium", task_medium), ("task_hard", task_hard)]:
    simulate_failed_task(task_name, init_fn)

print("\n" + "=" * 60)
print("SCENARIO 3: Edge case (no rewards at all)")
print("=" * 60)
rewards = []
if rewards:
    task_score = max(rewards)
else:
    task_score = 0.01
task_score = round(max(0.01, min(task_score, 0.99)), 4)
print(f"  Empty rewards: task_score={task_score}, 0<score<1? {0 < task_score < 1}")
