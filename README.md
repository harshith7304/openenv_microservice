---
title: Openenv Microservice
emoji: ⚙️
sdk: docker
app_port: 8000
---
# OpenEnv: Microservice Debugging Environment

## Environment Description & Motivation
This environment simulates a real-world backend microservice system containing a Database, an Authentication service, and a Payment service. The motivation is to test an autonomous AI DevOps/SRE agent's ability to perform root cause analysis and correctly recover system failures without human intervention. This directly models the real-world task of incident response and site reliability engineering (SRE).

## Action and Observation Space Definitions
The environment relies on structured JSON (Pydantic objects), eliminating free-form text hallucinations.

### Action Space:
- **`action_type`**: Must be one of `call_api`, `inspect_logs`, `restart_service`, `update_config`, `check_status`, `rollback_deployment`.
- **`service`**: The target service to act upon (`database`, `auth`, `payment`). For `check_status`, `service` may also be `all`.
- **`endpoint`, `key`, `value`**: Optional string parameters used contextually when calling endpoints or updating configurations.

### Observation Space:
- **`api_response`**: Standard output or result from an executed action.
- **`logs`**: Tail of the remote logs retrieved based on contextual actions.
- **`service_status`**: A dictionary indicating whether each dependency in the chain is strictly `up` or `down`.

## Task Descriptions (Difficulty Range)
1. **Task 1: Config Bug (Easy)**
   - **Scenario**: Database URL has been mistakenly replaced with an invalid string.
   - **Goal**: Identify the wrong URL, apply `update_config` with the correct URL string.
2. **Task 2: Auth Failure (Medium)**
   - **Scenario**: The Auth service has crashed abruptly due to a memory exception.
   - **Goal**: Restart the auth service while not accidentally disrupting the database or payment stability.
3. **Task 3: Cascading Failure (Hard)**
   - **Scenario**: A recent bad deployment of the Payment service causes cascading memory pressure and high latency across Auth + Database. During the crash/restart loop it also corrupts a secondary database configuration value.
   - **Goal**: Perform a broad sweep with `check_status(all)`, identify the bad deployment via `inspect_logs(payment)`, rollback the Payment deployment, then fix the isolated DB config drift (`update_config(database, pool_mode, safe)`), and finally verify recovery with `check_status(all)`.

## Setup and Usage Instructions
1. Clone the repository natively.
2. Install dependencies: `pip install -r requirements.txt`.
3. To validate against the standard OpenEnv protocols: `openenv validate`.
4. Optionally, start up the environment server natively using: `uv run server`.
5. Execute an agent evaluating all three tasks:
   - From the repo root (the folder that contains `openenv_microservice/`): `python -m openenv_microservice.inference`
   - Or from inside `openenv_microservice/`: `python inference.py`
   - Ensure you export your API key and define your preferred `MODEL_NAME`.

### Local sanity checks
- From the repo root: `python -m openenv_microservice.__test_fix`
- Or from inside `openenv_microservice/`: `python __test_fix.py`

## Baseline Scores
*Baseline scores are generated automatically upon successful inference run and remain strictly inside `(0, 1)`.*
- **Easy**: `TBD` / `0.99`
- **Medium**: `TBD` / `0.99`
- **Hard**: `TBD` / `0.99`

<!-- build trigger 6.0.1 -->
