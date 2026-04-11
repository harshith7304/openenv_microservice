"""Dump the openenv CLI validate command source."""
import inspect

# Find the validate command
try:
    from openenv.cli.commands.validate import validate
    print("=" * 80)
    print("FILE: commands/validate.py")
    print("=" * 80)
    print(inspect.getsource(inspect.getmodule(validate)))
except Exception as e:
    print(f"Could not import validate command: {e}")

# Also try the push command to see what it validates
try:
    from openenv.cli.commands.push import push
    print("\n" + "=" * 80)
    print("FILE: commands/push.py")
    print("=" * 80)
    print(inspect.getsource(inspect.getmodule(push)))
except Exception as e:
    print(f"Could not import push command: {e}")
