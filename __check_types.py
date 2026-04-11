"""Check StepResponse and ResetResponse types."""
import inspect
from openenv.core.env_server.types import StepResponse, ResetResponse

print("StepResponse fields:")
print(StepResponse.model_json_schema())

print("\nResetResponse fields:")
print(ResetResponse.model_json_schema())

# Also check what Observation type is expected
from openenv.core.env_server.types import Observation as BaseObservation
print("\nBase Observation fields:")
print(BaseObservation.model_json_schema())

# Check the ResetRequest
from openenv.core.env_server.types import ResetRequest
print("\nResetRequest fields:")
print(ResetRequest.model_json_schema())
