import os
import sys
from click.testing import CliRunner

# Force UTF-8 on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import subprocess

env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
env['PYTHONUTF8'] = '1'

# Path to the executable inside the virtual environment
cli_path = r".\venv\Scripts\openenv.exe"

try:
    # Run the push command, outputting to native stdout dynamically
    print("Executing openenv push...", flush=True)
    result = subprocess.run(
        [cli_path, 'push', '--repo-id', 'harshith7304/openenv_microservice', '--exclude', '.huggingfaceignore'], 
        env=env
    )
    if result.returncode != 0:
        print(f"Failed with return code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
except Exception as e:
    print(f"Failed to execute: {e}")
    sys.exit(1)
