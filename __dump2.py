"""Dump just serialize_observation."""
import inspect
from openenv.core.env_server.serialization import serialize_observation
print(inspect.getsource(inspect.getmodule(serialize_observation)))
