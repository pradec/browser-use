#!/usr/bin/env python3
"""
Comprehensive logging utility for Browser Use cache system.

This utility provides centralized logging that outputs to both terminal and log files,
with each script getting its own log file in a shared run directory.
"""

import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import sys


class TaskLogger:
    """Centralized logger for task execution with file and console output."""
    
    _instances: Dict[str, 'TaskLogger'] = {}
    _run_directory: Optional[Path] = None
    
    def __init__(self, script_name: str, run_directory: Optional[Path] = None):
        """Initialize logger for a specific script."""
        self.script_name = script_name
        
        # Use shared run directory or create new one
        if run_directory:
            self._run_directory = run_directory
        elif not self._run_directory:
            self._run_directory = self._create_run_directory()
        
        self.run_directory = self._run_directory
        self.log_file = self.run_directory / f"{script_name}.log"
        
        # Set up Python logger
        self.logger = logging.getLogger(f"browser_use_cache.{script_name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file, mode='a')
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter('%(message)s')
        
        # Set formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Store instance for reuse
        self._instances[script_name] = self
        
        # Log initialization
        self.info(f"🚀 {script_name} logger initialized")
        self.info(f"📁 Run directory: {self.run_directory}")
        self.info(f"📄 Log file: {self.log_file}")
    
    @classmethod
    def get_logger(cls, script_name: str, run_directory: Optional[Path] = None) -> 'TaskLogger':
        """Get or create a logger instance for a script."""
        if script_name in cls._instances and run_directory is None:
            return cls._instances[script_name]
        return cls(script_name, run_directory)
    
    @classmethod
    def set_run_directory(cls, run_directory: Path):
        """Set the shared run directory for all loggers."""
        cls._run_directory = run_directory
    
    @classmethod
    def get_run_directory(cls) -> Optional[Path]:
        """Get the current run directory."""
        return cls._run_directory
    
    @staticmethod
    def _create_run_directory() -> Path:
        """Create a unique run directory for this execution."""
        timestamp = int(datetime.now().timestamp())
        run_id = str(uuid.uuid4())[:8]
        
        base_tmp = Path(tempfile.gettempdir())
        run_directory = base_tmp / f'browseruse_task_runner_{run_id}_{timestamp}'
        run_directory.mkdir(parents=True, exist_ok=True)
        
        return run_directory
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(f"⚠️  {message}")
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(f"❌ {message}")
    
    def success(self, message: str):
        """Log success message."""
        self.logger.info(f"✅ {message}")
    
    def step(self, step_num: int, message: str):
        """Log step message."""
        self.logger.info(f"\n🔧 Step {step_num}: {message}")
    
    def command(self, cmd: str, description: str = ""):
        """Log command execution."""
        if description:
            self.logger.info(f"🔧 {description}")
        self.logger.info(f"   Command: {cmd}")
    
    def command_result(self, success: bool, output: str = "", error: str = ""):
        """Log command result."""
        if success:
            self.logger.info("   ✅ Success")
            if output.strip():
                # Log each line of output with proper indentation
                for line in output.strip().split('\n'):
                    self.logger.info(f"   Output: {line}")
        else:
            self.logger.error(f"   ❌ Failed")
            if error.strip():
                for line in error.strip().split('\n'):
                    self.logger.error(f"   Error: {line}")
            if output.strip():
                for line in output.strip().split('\n'):
                    self.logger.info(f"   Output: {line}")
    
    def action_start(self, action_index: int, action_name: str, details: str = ""):
        """Log action start."""
        self.logger.info(f"\n🎬 Starting Action {action_index}: {action_name}")
        if details:
            self.logger.info(f"   Details: {details}")
    
    def action_result(self, action_index: int, success: bool, message: str = ""):
        """Log action result."""
        if success:
            self.logger.info(f"✅ Action {action_index} completed successfully")
        else:
            self.logger.error(f"❌ Action {action_index} failed")
        if message:
            self.logger.info(f"   {message}")
    
    def json_data(self, label: str, data: Any):
        """Log JSON data."""
        self.logger.info(f"📊 {label}:")
        json_str = json.dumps(data, indent=2)
        for line in json_str.split('\n'):
            self.logger.info(f"   {line}")
    
    def file_operation(self, operation: str, file_path: Path, success: bool = True):
        """Log file operation."""
        if success:
            self.logger.info(f"📄 {operation}: {file_path}")
        else:
            self.logger.error(f"📄 Failed to {operation.lower()}: {file_path}")
    
    def statistics(self, stats: Dict[str, Any]):
        """Log statistics."""
        self.logger.info("📊 Statistics:")
        for key, value in stats.items():
            self.logger.info(f"   {key}: {value}")
    
    def save_execution_summary(self, summary_data: Dict[str, Any]):
        """Save execution summary to a JSON file."""
        summary_file = self.run_directory / f"{self.script_name}_summary.json"
        
        # Add timestamp and run info
        summary_data.update({
            "script_name": self.script_name,
            "run_directory": str(self.run_directory),
            "log_file": str(self.log_file),
            "execution_timestamp": datetime.now().isoformat(),
        })
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        self.success(f"Execution summary saved: {summary_file}")
        return summary_file
    
    def create_run_summary(self):
        """Create overall run summary with all script logs."""
        run_summary_file = self.run_directory / "run_summary.json"
        
        # Collect all log files in run directory
        log_files = list(self.run_directory.glob("*.log"))
        summary_files = list(self.run_directory.glob("*_summary.json"))
        
        run_summary = {
            "run_id": self.run_directory.name,
            "run_directory": str(self.run_directory),
            "start_time": datetime.now().isoformat(),
            "log_files": [str(f) for f in log_files],
            "summary_files": [str(f) for f in summary_files],
            "scripts_executed": [f.stem for f in log_files],
        }
        
        with open(run_summary_file, 'w') as f:
            json.dump(run_summary, f, indent=2)
        
        self.success(f"Run summary created: {run_summary_file}")
        return run_summary_file


def get_logger(script_name: str, run_directory: Optional[Path] = None) -> TaskLogger:
    """Convenience function to get a logger instance."""
    return TaskLogger.get_logger(script_name, run_directory)


def set_run_directory(run_directory: Path):
    """Set the shared run directory for all loggers."""
    TaskLogger.set_run_directory(run_directory)


def get_run_directory() -> Optional[Path]:
    """Get the current run directory."""
    return TaskLogger.get_run_directory()
