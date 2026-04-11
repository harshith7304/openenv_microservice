# Grading System

## Metrics

* system_health (0-1)
* error_rate
* success_rate

---

## Reward Logic

### Step Reward

* correct action -> positive reward in `(0, 1)`
* incorrect action -> minimum nonzero reward `0.01`

### Final Reward

* system fully fixed -> `0.99`
* partially fixed -> `0.50`
* not fixed -> `0.01`

---

## Penalties

* redundant actions -> low nonzero reward
* wrong root cause -> minimum nonzero reward

---

## Success Criteria

done = True if:

* system_health > 0.9
* all services operational

---

## Determinism

* no randomness
* same input -> same output
