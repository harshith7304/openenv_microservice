# Tasks Definition

## Task 1: Config Bug

Initial State:

* DB URL incorrect
* all services failing

Expected Solution:

* update_config(database, "url", correct_url)

---

## Task 2: Auth Failure

Initial State:

* auth service down
* payment failing

Expected Solution:

* restart_service(auth)

---

## Task 3: Cascading Failure

Initial State:

* All services are UP but degraded (high latency + error rates)
* Payment has a bad deployment artifact causing cascading memory pressure
* Database has a secondary config drift (pool_mode) that must be fixed after rollback

Expected Solution:

* check_status(all) to observe degraded pattern
* inspect_logs(payment) to identify bad deployment
* rollback_deployment(payment) first (strict ordering)
* inspect_logs(database) to find drift key
* update_config(database, pool_mode, safe)
* check_status(all) to verify recovery

---

## Task Requirements

* Each task must have:

  * fixed initial state
  * known correct solution
  * deterministic outcome
