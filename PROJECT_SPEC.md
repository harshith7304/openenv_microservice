# API Debugging Environment — OpenEnv Spec

## Objective

Build an OpenEnv environment that simulates a failing microservice system.
An agent must perform root cause analysis and fix system failures.

---

## Core Concept

The environment represents a backend system with:

* auth service
* payment service
* database

The agent interacts via structured actions to:

1. inspect logs
2. diagnose issues
3. fix system
4. verify recovery

---

## Key Constraints

* Deterministic behavior (no randomness)
* One correct solution path per task
* Fully reproducible episodes
* No free-text actions (strict tool interface)

---

## Environment API

### reset()

Returns initial observation:

* system status
* initial logs

### step(action)

Applies action:

* updates system state
* returns observation, reward, done

### state()

Returns internal state (for debugging only)

---

## Actions

* call_api(service, endpoint)
* inspect_logs(service)
* restart_service(service)
* update_config(service, key, value)
* check_status(service)

---

## Observations

Structured JSON:

* API response
* logs
* service status

---

## Tasks

### Task 1 (Easy)

Bug: wrong DB config
Goal: fix config → system works

### Task 2 (Medium)

Bug: auth service down
Goal: restore dependency chain

### Task 3 (Hard)

Bug: cascading failure
Goal: identify root cause and stabilize system

---

## Reward Design

* correct fix → +1.0
* partial fix → +0.5
* wrong action → -0.2
* unnecessary steps → small penalty

---

## Success Condition

System health > threshold AND all services operational
