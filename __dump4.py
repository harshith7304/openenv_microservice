"""Dump the validation module."""
import inspect
from openenv.cli._validation import validate_running_environment
print(inspect.getsource(inspect.getmodule(validate_running_environment)))
