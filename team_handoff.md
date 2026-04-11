# Team Squirrel - OpenEnv Hackathon Handoff

## Quick Links
- **Live HF Space**: https://huggingface.co/spaces/harshith7304/openenv_microservice
- **GitHub Repo**: https://github.com/harshith7304/openenv_microservice
- **Deadline**: April 8, 2026, 11:59 PM IST
- **Submission**: Only team lead (Vamshidhar) can submit the HF Space URL on the dashboard

---

## What We Built

An **Autonomous SRE Incident Simulator** - an OpenEnv-compliant RL environment where AI agents must debug failing microservice systems.

**The one-liner for judges:**
> "We built an OpenEnv environment where agents learn to perform root cause analysis and fix failures in simulated production systems."

### The System
3 microservices with real dependency chains:
```
database <- auth <- payment
```
- **auth** depends on **database**
- **payment** depends on **auth** AND **database**

When something breaks, errors cascade exactly like in real production systems.

### The 3 Tasks

| Task | Difficulty | Scenario | Correct Solution |
|------|-----------|----------|-----------------|
| **task_easy** | Easy | Database URL is wrong (`invalid_url_123`) -> all services down | `inspect_logs(database)` -> `update_config(database, url, valid_db_url)` |
| **task_medium** | Medium | Auth crashed (OOM). DB is fine. Payment blocked. | `inspect_logs(auth)` -> `restart_service(auth)` |
| **task_hard** | Hard | Bad DB URL -> 5000ms latency -> auth retry storm -> payment cascade | `inspect_logs(payment)` -> `inspect_logs(auth)` -> `inspect_logs(database)` -> `update_config(database, url, valid_db_url)` |

### Baseline Results
```
Easy:   0.30 -> 0.99  (2 steps)
Medium: 0.30 -> 0.99  (2 steps)
Hard:   0.15 -> 0.25 -> 0.50 -> 0.99  (4 steps, escalating diagnostic rewards)
```

---

## Key Design Features

1. **Root Cause Gate**: Agent must `inspect_logs` before fixes get full reward. Blind `update_config` without diagnosis gets `0.01`.
2. **Dependency Enforcement**: Can't restart auth if DB config is broken. Can't restart payment unless auth and DB are up.
3. **Escalating Rewards**: Each new diagnostic action gets progressively higher reward. Repeated same action gets a low nonzero reward.
4. **Rewards always in `(0.0, 1.0)`** - strictly compliant with hackathon rules.

---

## Project Structure

```
meta_openenv/
|-- openenv.yaml
|-- pyproject.toml
|-- Dockerfile
|-- README.md
|-- requirements.txt
|-- __init__.py
|-- models.py
|-- environment.py
|-- tasks.py
|-- grader.py
|-- inference.py
|-- client.py
|-- server/
|   |-- __init__.py
|   `-- app.py
|-- outputs/
|   `-- baseline_results.txt
|-- push.py
|-- .gitignore
`-- .huggingfaceignore
```

---

## Pre-Submission Checklist

- [x] HF Space deploys and shows "Running"
- [x] `/reset` returns valid Observation
- [x] `/step` returns valid Observation with reward
- [x] `/state` returns episode metadata
- [x] `openenv validate` passes
- [x] `inference.py` runs in expected time
- [x] All rewards are strictly in `(0.0, 1.0)`
- [x] 3 tasks with graders
- [x] Dockerfile builds
- [x] `[START]` `[STEP]` `[END]` log format exact
