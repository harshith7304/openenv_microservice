"""Test the live HF space to see EXACTLY what the evaluator sees."""
import requests
import json

BASE = "https://harshith7304-openenv-microservice.hf.space"

print("=" * 60)
print("1. RESET (task_easy default)")
print("=" * 60)
r = requests.post(f"{BASE}/reset", json={})
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))
reset_data = r.json()

print("\n" + "=" * 60)
print("2. STEP: inspect_logs(database)")
print("=" * 60)
r = requests.post(f"{BASE}/step", json={"action": {"action_type": "inspect_logs", "service": "database"}})
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

print("\n" + "=" * 60)
print("3. STEP: update_config(database, url, valid_db_url)")
print("=" * 60)
r = requests.post(f"{BASE}/step", json={"action": {"action_type": "update_config", "service": "database", "key": "url", "value": "valid_db_url"}})
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

print("\n" + "=" * 60)
print("4. STEP: restart_service(database)")
print("=" * 60)
r = requests.post(f"{BASE}/step", json={"action": {"action_type": "restart_service", "service": "database"}})
print(f"Status: {r.status_code}")
step_data = r.json()
print(json.dumps(step_data, indent=2))

print("\n" + "=" * 60)
print("5. STATE")
print("=" * 60)
r = requests.get(f"{BASE}/state")
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

print("\n" + "=" * 60)
print("6. CRITICAL: Check reward values")
print("=" * 60)
print(f"Reset reward: {reset_data.get('reward')} (type: {type(reset_data.get('reward')).__name__})")
print(f"Last step reward: {step_data.get('reward')} (type: {type(step_data.get('reward')).__name__})")
print(f"Last step done: {step_data.get('done')}")

reward = step_data.get('reward')
if reward is not None:
    if reward == 0.0:
        print("WARNING: reward is exactly 0.0!")
    elif reward == 1.0:
        print("WARNING: reward is exactly 1.0!")
    elif 0.0 < reward < 1.0:
        print(f"OK: reward {reward} is strictly in (0, 1)")
    else:
        print(f"ERROR: reward {reward} is out of [0, 1] range!")

# Now test the SAME BUT check if there's a NEW environment per
# request or if state carries over
print("\n" + "=" * 60)
print("7. CRITICAL: State isolation test")
print("=" * 60)
print("Sending step WITHOUT prior reset to see if env resets per-request:")
r2 = requests.post(f"{BASE}/step", json={"action": {"action_type": "check_status", "service": "database"}})
print(f"Status: {r2.status_code}")
step2 = r2.json()
print(json.dumps(step2, indent=2))
print(f"Step reward: {step2.get('reward')}")
