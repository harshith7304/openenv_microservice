# Grading System

## Metrics

* system_health (0–1)
* error_rate
* success_rate

---

## Reward Logic

### Step Reward

* correct action → +0.2
* incorrect action → -0.1

### Final Reward

* system fully fixed → +1.0
* partially fixed → +0.5
* not fixed → 0

---

## Penalties

* redundant actions → -0.05
* wrong root cause → -0.2

---

## Success Criteria

done = True if:

* system_health > 0.9
* all services operational

---

## Determinism

* no randomness
* same input → same output
