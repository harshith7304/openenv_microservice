"""Dump the OpenEnv framework source files we need to inspect."""
import os, inspect

# 1) http_server – how the FastAPI app is built, how step/reset endpoints work
from openenv.core.env_server.http_server import create_app
print("=" * 80)
print("FILE: http_server.py")
print("=" * 80)
print(inspect.getsource(inspect.getmodule(create_app)))

# 2) BaseEnvironment – what interface we must satisfy
from openenv.core.env_server.interfaces import Environment
print("\n" + "=" * 80)
print("FILE: interfaces.py (Environment base class)")
print("=" * 80)
print(inspect.getsource(inspect.getmodule(Environment)))

# 3) Rubric base class
try:
    from openenv.core.rubrics import Rubric
    print("\n" + "=" * 80)
    print("FILE: rubrics.py")
    print("=" * 80)
    print(inspect.getsource(inspect.getmodule(Rubric)))
except Exception as e:
    print(f"Could not get rubrics source: {e}")

# 4) evals / inspect_harness – how the evaluator runs
try:
    from openenv.core.evals import inspect_harness
    print("\n" + "=" * 80)
    print("FILE: inspect_harness.py")
    print("=" * 80)
    print(inspect.getsource(inspect_harness))
except Exception as e:
    print(f"Could not get inspect_harness source: {e}")

# 5) Check if there's a scoring / validation module
try:
    from openenv.core.evals import scoring
    print("\n" + "=" * 80)
    print("FILE: scoring.py")
    print("=" * 80) 
    print(inspect.getsource(scoring))
except Exception as e:
    print(f"No scoring module: {e}")

# 6) Check the openenv CLI validate command
try:
    from openenv import cli
    print("\n" + "=" * 80)
    print("FILE: cli.py (or main click group)")
    print("=" * 80)
    print(inspect.getsource(inspect.getmodule(cli)))
except Exception as e:
    print(f"Could not get cli source: {e}")
