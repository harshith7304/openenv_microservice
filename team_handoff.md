# 🚀 Team Squirrel — OpenEnv Hackathon Handoff

## Quick Links
- **Live HF Space**: https://huggingface.co/spaces/harshith7304/openenv_microservice
- **GitHub Repo**: https://github.com/harshith7304/openenv_microservice
- **Deadline**: April 8, 2026, 11:59 PM IST
- **Submission**: Only team lead (Vamshidhar) can submit the HF Space URL on the dashboard

---

## What We Built

An **Autonomous SRE Incident Simulator** — an OpenEnv-compliant RL environment where AI agents must debug failing microservice systems. 

**The one-liner for judges:**
> "We built an OpenEnv environment where agents learn to perform root cause analysis and fix failures in simulated production systems."

### The System
3 microservices with real dependency chains:
```
database ← auth ← payment
```
- **auth** depends on **database**
- **payment** depends on **auth** AND **database**

When something breaks, errors cascade exactly like in real production systems.

### The 3 Tasks

| Task | Difficulty | Scenario | Correct Solution |
|------|-----------|----------|-----------------|
| **task_easy** | 🟢 Easy | Database URL is wrong (`invalid_url_123`) → all services down | `inspect_logs(database)` → `update_config(database, url, valid_db_url)` |
| **task_medium** | 🟡 Medium | Auth crashed (OOM). DB is fine. Payment blocked. | `inspect_logs(auth)` → `restart_service(auth)` |
| **task_hard** | 🔴 Hard | Bad DB URL → 5000ms latency → auth retry storm → payment cascade | `inspect_logs(payment)` → `inspect_logs(auth)` → `inspect_logs(database)` → `update_config(database, url, valid_db_url)` |

### Baseline Results (Already Passing ✅)
```
Easy:   0.30 → 1.00  (2 steps)
Medium: 0.30 → 1.00  (2 steps)
Hard:   0.15 → 0.25 → 0.50 → 1.00  (4 steps, escalating diagnostic rewards)
```

---

## Key Design Features (What Makes Us Competitive)

1. **Root Cause Gate**: Agent MUST `inspect_logs` before fixes get full reward. Blind `update_config` without diagnosis = penalty (`reward=0.0`)
2. **Dependency Enforcement**: Can't restart auth if DB config is broken. Can't restart payment unless auth+DB are up.
3. **Escalating Rewards**: Each NEW diagnostic action gets progressively higher reward. Repeated same action = `0.0`
4. **Rewards always in [0.0, 1.0]** — strictly compliant with hackathon rules

---

## Project Structure

```
meta_openenv/
├── openenv.yaml          # OpenEnv framework metadata
├── pyproject.toml         # Python package config (entry point: server)
├── Dockerfile             # Container config for HF Spaces
├── README.md              # HF Space frontmatter + documentation
├── requirements.txt       # Dependencies
├── __init__.py            # Root package init
├── models.py              # Pydantic models: Action, Observation, State, ServiceState
├── environment.py         # Core environment logic (step/reset/state)
├── tasks.py               # 3 task initializers (easy/medium/hard)
├── grader.py              # Deterministic reward function
├── inference.py           # Baseline agent using OpenAI client + Qwen
├── client.py              # OpenEnv client wrapper
├── server/
│   ├── __init__.py
│   └── app.py             # FastAPI server binding for OpenEnv framework
├── outputs/
│   └── baseline_results.txt  # Saved inference results
├── push.py                # Deployment helper (UTF-8 wrapper for Windows)
├── .gitignore
└── .huggingfaceignore     # Excludes venv from HF uploads
```

---

## How to Set Up Locally

### 1. Clone
```bash
git clone https://github.com/harshith7304/openenv_microservice.git
cd openenv_microservice
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install openenv-core openai pydantic
```

### 4. Set Environment Variables
```bash
# Windows PowerShell:
$env:HF_TOKEN = "your_huggingface_token"
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"

# Linux/Mac:
export HF_TOKEN="your_huggingface_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
```

### 5. Validate
```bash
openenv validate
```

### 6. Run Inference
```bash
python inference.py
```
Expected output: `[START]`, `[STEP]`, `[END]` logs for all 3 tasks.

### 7. Test Live Endpoints
```bash
# Reset
curl -X POST https://harshith7304-openenv-microservice.hf.space/reset -H "Content-Type: application/json" -d "{}"

# Step
curl -X POST https://harshith7304-openenv-microservice.hf.space/step -H "Content-Type: application/json" -d '{"action": {"action_type": "inspect_logs", "service": "database"}}'

# State
curl https://harshith7304-openenv-microservice.hf.space/state
```

---

## File-by-File Guide (What Each File Does)

### `models.py` — Data Contracts
- `Action`: What the agent can do (5 action types × 3 services)
- `Observation`: What the agent sees back (logs, status, reward, done)
- `State`: Internal system state (service statuses, configs, metrics)

### `environment.py` — The Brain
- Tracks action history, diagnosed services, root cause identification
- Enforces dependency chains (auth→db, payment→auth+db)
- Penalizes repeated actions and blind fixes

### `grader.py` — The Scorekeeper
- Escalating rewards: more diagnosed services = higher reward
- Root cause bonus: +0.15 when root cause identified
- Full recovery: 1.0 (with RCA) or 0.8 (without RCA)
- Repeated action: 0.05 (diminishing returns)

### `tasks.py` — The Scenarios
- `task_easy()`: Returns broken state with invalid DB URL
- `task_medium()`: Returns state with crashed auth, healthy DB
- `task_hard()`: Returns state with bad DB URL + high latency cascade

### `inference.py` — The Baseline Agent
- Uses Qwen/Qwen2.5-72B-Instruct via HF router
- Strictly follows `[START]` `[STEP]` `[END]` format
- Runs all 3 tasks sequentially

### `server/app.py` — The Web Server
- Binds our environment to OpenEnv's FastAPI framework
- Exposes /reset, /step, /state, /web endpoints automatically

---

## How to Deploy Changes

After making code changes:

### Push to HF Spaces (from Harshith's machine with auth):
```bash
python push.py
```

### Push to GitHub:
```bash
git add -A
git commit -m "description of changes"
git push
```

---

## Pre-Submission Checklist

- [x] HF Space deploys and shows "Running" ✅
- [x] `/reset` returns valid Observation ✅
- [x] `/step` returns valid Observation with reward ✅
- [x] `/state` returns episode metadata ✅
- [x] `openenv validate` passes ✅
- [x] `inference.py` runs < 20 min ✅
- [x] All rewards ∈ [0.0, 1.0] ✅
- [x] 3 tasks with graders ✅
- [x] Dockerfile builds ✅
- [x] `[START]` `[STEP]` `[END]` log format exact ✅

---

## What Could Still Be Improved (If Time Permits)

1. **Richer task_hard**: Add a 4th "expert" task with more services
2. **README baseline scores**: Fill in actual numbers instead of TBD
3. **More detailed dependency graph** in README for judges
4. **Edge case handling**: What if agent sends action with wrong service name
