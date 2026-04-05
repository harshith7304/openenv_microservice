# System Design

## Services

### Database

* stores user data
* config: db_url

### Auth

* depends on database
* handles login

### Payment

* depends on auth + database
* processes transactions

---

## Dependencies

database → auth → payment

---

## Failure Types

### Config Bug

* wrong DB URL

### Service Crash

* auth service down

### Cascading Failure

* DB latency → auth overload → payment fail

---

## Logs Design

Each service produces:

* error logs
* success logs
* warnings

Logs must clearly indicate root cause.

---

## System Health

Computed from:

* service uptime
* error rate
* API success rate

---

## Episode Flow

1. reset system with bug
2. agent explores
3. agent applies fixes
4. system updates
5. grader evaluates
