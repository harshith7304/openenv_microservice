from openenv.core.env_server.http_server import create_app
from ..models import Action, Observation
from ..environment import OpenEnv

app = create_app(
    OpenEnv,
    Action,
    Observation,
    env_name="openenv_microservice",
    max_concurrent_envs=1
)

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)  # main() check workaround
