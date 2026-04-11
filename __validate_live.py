"""Run the actual openenv validate against the live HF space."""
from openenv.cli._validation import validate_running_environment
import json

result = validate_running_environment("https://harshith7304-openenv-microservice.hf.space", timeout_s=15.0)
print(json.dumps(result, indent=2))
