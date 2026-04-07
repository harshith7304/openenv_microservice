try:
    from .models import State, ServiceState
except ImportError:
    from models import State, ServiceState

def task_easy() -> State:
    return State(
        system_health=0.01,
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
        system_health=0.1,
        task_name="task_hard",
        services={
            "database": ServiceState(status="up", config={"url": "invalid_url_123"}, metrics={"latency": 5000.0, "error_rate": 0.8}),
            "auth": ServiceState(status="up", config={"db_url": "valid_db_url"}, metrics={"latency": 5000.0, "error_rate": 0.9}),
            "payment": ServiceState(status="down", config={}, metrics={"latency": 0.0, "error_rate": 1.0})
        }
    )
