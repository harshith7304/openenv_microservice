import os
import json
from openai import OpenAI
from environment import OpenEnv
from tasks import task_easy, task_medium, task_hard
from models import Action

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or "fake-key"
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
BENCHMARK = "openenv_microservices"

def run_task(task_name, init_fn):
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = OpenEnv(init_fn)
    obs = env.reset()
    
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}")
    
    done = False
    step_count = 0
    rewards = []
    
    system_prompt = """You are an autonomous AI debugging agent fixing a microservice system.
Available actions:
- action_type: "check_status", "inspect_logs", "restart_service", "update_config", "call_api"
- service: "database", "auth", "payment"
For `update_config`, explicitly provide the `key` (e.g. "url") and `value` (e.g. "valid_db_url").
Return JSON matching the schema exactly:
{"action_type": "string", "service": "string", "endpoint": "string", "key": "string", "value": "string"}
Any missing property can be set to null.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Observation: {obs.model_dump_json()}"}
    ]

    while not done and step_count < 8:
        step_count += 1
        reward = 0.0
        error_msg = "null"
        action_str = "unknown"
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_action = response.choices[0].message.content
            action_dict = json.loads(raw_action)
            action = Action(**action_dict)
            action_str = f"{action.action_type}({action.service})"
            
            obs = env.step(action)
            reward = obs.reward
            done = obs.done
            
            messages.append({"role": "assistant", "content": raw_action})
            messages.append({"role": "user", "content": f"Observation: {obs.model_dump_json()}"})
            
        except Exception as e:
            error_msg = str(e).replace('\n', ' ')
            reward = -0.1
            done = True
            
        rewards.append(reward)
        print(f"[STEP] step={step_count} action={action_str} reward={reward:.2f} done={str(done).lower()} error={error_msg}")
        
    success = done
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={step_count} rewards={rewards_str}")

if __name__ == "__main__":
    run_task("task_easy", task_easy)
    run_task("task_medium", task_medium)
    run_task("task_hard", task_hard)
