try:
    from .models import State, ServiceState
except ImportError:
    from models import State, ServiceState

def task_easy() -> State:
    return State(
        system_health=0.1,
        task_name="task_easy",
        services={
            "database": ServiceState(status="down", config={"url": "invalid_url_123"}),
            "auth": ServiceState(status="down", config={"db_url": "invalid_url_123"}),
            "payment": ServiceState(status="down", config={})
        }
    )

def task_medium() -> State:
    return State(
        system_health=0.3,
        task_name="task_medium",
        services={
            "database": ServiceState(status="up", config={"url": "valid_db_url"}),
            "auth": ServiceState(status="down", config={"db_url": "valid_db_url"}),
            "payment": ServiceState(status="down", config={})
        }
    )

def task_hard() -> State:
    return State(
        system_health=0.2,
        task_name="task_hard",
        services={
            "database": ServiceState(
                status="up",
                config={"url": "valid_db_url", "pool_mode": "corrupt"},
                metrics={"latency": 4200.0, "error_rate": 0.6, "memory_mb": 1200.0},
            ),
            "auth": ServiceState(
                status="up",
                config={"db_url": "valid_db_url"},
                metrics={"latency": 3600.0, "error_rate": 0.7, "memory_mb": 1500.0},
            ),
            "payment": ServiceState(
                status="up",
                config={"deployment": "bad"},
                metrics={"latency": 2800.0, "error_rate": 0.8, "memory_mb": 2000.0, "verified": 0.0},
            ),
        }
    )
