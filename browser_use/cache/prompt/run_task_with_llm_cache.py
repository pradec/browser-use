#!/usr/bin/env python3
"""
Run task with LLM Cache enabled.

This wrapper sets the BROWSER_USE_LLM_CACHE environment variable and then
executes the regular run_task.py script with all the same arguments.
"""

import os
import subprocess
import sys
from pathlib import Path

# Enable LLM caching
os.environ["BROWSER_USE_LLM_CACHE"] = "true"

if __name__ == "__main__":
	print("🎯 Running task with LLM Cache enabled")
	print("=" * 50)
	
	# Show cache environment status
	print(f"📊 BROWSER_USE_LLM_CACHE = {os.environ.get('BROWSER_USE_LLM_CACHE')}")
	print()
	
	# Get the path to the regular run_task.py script
	current_dir = Path(__file__).parent
	run_task_script = current_dir / "run_task.py"
	
	if not run_task_script.exists():
		print(f"❌ Could not find run_task.py at {run_task_script}")
		sys.exit(1)
	
	# Find the .venv Python interpreter
	project_root = current_dir.parent.parent.parent  # Go up to BrowserUse root
	venv_python = project_root / ".venv" / "bin" / "python"
	
	if venv_python.exists():
		python_exec = str(venv_python)
		print(f"✓ Using virtual environment Python: {python_exec}")
	else:
		python_exec = sys.executable
		print(f"⚠️ Virtual environment not found, using system Python: {python_exec}")
	
	# Execute run_task.py with all the same arguments
	cmd = [python_exec, str(run_task_script)] + sys.argv[1:]
	print(f"🚀 Executing: {' '.join(cmd)}")
	print()
	
	try:
		# Set up environment with PYTHONPATH
		env = os.environ.copy()
		env["PYTHONPATH"] = str(project_root) + ":" + env.get("PYTHONPATH", "")
		
		# Run the command and wait for completion
		result = subprocess.run(cmd, env=env)
		sys.exit(result.returncode)
	except KeyboardInterrupt:
		print("\n⚠️ Task interrupted by user")
		sys.exit(130)
	except Exception as e:
		print(f"❌ Failed to execute task: {e}")
		sys.exit(1)