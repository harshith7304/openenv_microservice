"""Check all endpoints on the live HF space."""
import requests
BASE = "https://harshith7304-openenv-microservice.hf.space"

# Check what OpenAPI exposes
r = requests.get(f"{BASE}/openapi.json")
openapi = r.json()
paths = list(openapi.get("paths", {}).keys())
print("Available endpoints:", paths)

# Check for /tasks endpoint  
for path in ["/tasks", "/task", "/graders", "/score", "/scores"]:
    try:
        r = requests.get(f"{BASE}{path}", timeout=5)
        print(f"GET {path}: {r.status_code} -> {r.text[:200]}")
    except Exception as e:
        print(f"GET {path}: ERROR {e}")
    try:
        r = requests.post(f"{BASE}{path}", json={}, timeout=5)
        print(f"POST {path}: {r.status_code} -> {r.text[:200]}")
    except Exception as e:
        print(f"POST {path}: ERROR {e}")

# Check metadata
r = requests.get(f"{BASE}/metadata")
print(f"\nMetadata: {r.json()}")

# Check schema
r = requests.get(f"{BASE}/schema")
import json
schema = r.json()
print(f"\nObservation schema keys: {list(schema.get('observation', {}).get('properties', {}).keys())}")
