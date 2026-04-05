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

* DB slow response
* auth retry loop
* payment timeout

Expected Solution:

* fix DB config
* stabilize system

---

## Task Requirements

* Each task must have:

  * fixed initial state
  * known correct solution
  * deterministic outcome
