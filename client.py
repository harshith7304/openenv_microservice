from typing import Dict
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State as OpenEnvState

try:
    from .models import Action, Observation
except ImportError:
    from models import Action, Observation

class MicroserviceEnv(EnvClient[Action, Observation, OpenEnvState]):
    """
    Client for the Microservice Debugging Environment.
    """

    def _step_payload(self, action: Action) -> Dict:
        return action.model_dump()

    def _parse_result(self, payload: Dict) -> StepResult[Observation]:
        obs_data = payload.get("observation", {})
        # Clamp reward to strict (0, 1) range
        raw_reward = payload.get("reward", 0.01)
        if raw_reward is None:
            raw_reward = 0.01
        clamped_reward = max(0.01, min(float(raw_reward), 0.99))

        observation = Observation(
            api_response=obs_data.get("api_response"),
            logs=obs_data.get("logs"),
            service_status=obs_data.get("service_status", {}),
            reward=clamped_reward,
            done=payload.get("done", False),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=clamped_reward,
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> OpenEnvState:
        return OpenEnvState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
