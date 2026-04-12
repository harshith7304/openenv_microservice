import os
import json
from openai import OpenAI

try:
    from .environment import OpenEnv
    from .tasks import task_easy, task_medium, task_hard
    from .models import Action
except ImportError:
    from environment import OpenEnv
    from tasks import task_easy, task_medium, task_hard
    from models import Action

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
BENCHMARK = "openenv_microservices"
MAX_STEPS = 8

SYSTEM_PROMPT = """You are an autonomous AI SRE agent tasked with debugging a failing microservice system.

The system has 3 services: database, auth, payment.
- auth depends on database
- payment depends on auth and database

Available actions (respond ONLY with valid JSON, no explanation):
- {"action_type": "check_status", "service": "<database|auth|payment|all>"}
- {"action_type": "inspect_logs", "service": "<database|auth|payment>"}
- {"action_type": "restart_service", "service": "<database|auth|payment>"}
- {"action_type": "update_config", "service": "database", "key": "url", "value": "valid_db_url"}
- {"action_type": "update_config", "service": "database", "key": "pool_mode", "value": "safe"}
- {"action_type": "rollback_deployment", "service": "<database|payment>"}
- {"action_type": "call_api", "service": "<database|auth|payment>", "endpoint": "<optional>"}

Strategy:
1. Start with check_status(all) to get a broad sweep if the incident is unclear
2. Use inspect_logs on the most suspicious service(s) to identify root cause
3. Apply the correct fix (update_config, rollback_deployment, OR restart_service)
4. Verify by checking status again (often check_status(all))
5. Done when all services are up and system_health > 0.9

Always respond with a single JSON object and nothing else."""


def run_task(task_name: str, init_fn):
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    env = OpenEnv(init_fn)
    obs = env.reset()

    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    done = False
    step_count = 0
    rewards = []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Initial observation: {obs.model_dump_json()}\n\nWhat is your first action?"}
    ]

    while not done and step_count < MAX_STEPS:
        step_count += 1
        reward = 0.1
        error_msg = "null"
        action_str = "unknown"

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=150,
            )
            raw_action = response.choices[0].message.content
            action_dict = json.loads(raw_action)
            # Remove None values so Pydantic doesn't choke
            action_dict = {k: v for k, v in action_dict.items() if v is not None}
            action = Action(**action_dict)
            action_str = f"{action.action_type}({action.service})"

            obs = env.step(action)
            reward = obs.reward
            done = obs.done

            messages.append({"role": "assistant", "content": raw_action})
            messages.append({
                "role": "user",
                "content": f"Observation: {obs.model_dump_json()}\n\nContinue debugging. What is your next action?"
            })

        except Exception as e:
            error_msg = str(e).replace('\n', ' ')[:200]
            done = False

        rewards.append(reward)
        print(f"[STEP] step={step_count} action={action_str} reward={reward} done={str(done).lower()} error={error_msg}", flush=True)

    # Compute a continuous task score strictly in (0, 1)
    # The evaluator checks that task scores are strictly between 0 and 1
    # (not 0.0 and not 1.0), so we must never emit exactly 0.0 or 1.0.
    if rewards:
        task_score = max(rewards)  # Use the best reward achieved
    else:
        task_score = 0.01  # Fallback: minimum nonzero

    # STRICT CLAMP: ensure task_score is in open interval (0, 1)
    task_score = round(max(0.01, min(task_score, 0.99)), 4)

    success = done and any(r >= 0.9 for r in rewards)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] task={task_name} success={str(success).lower()} score={task_score} steps={step_count} rewards={rewards_str}", flush=True)


if __name__ == "__main__":
    run_task("task_easy", task_easy)
    run_task("task_medium", task_medium)
    run_task("task_hard", task_hard)
