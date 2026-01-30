"""
Airflow Pipeline Wrappers
-------------------------
This module provides entry points for the Airflow DAG to execute
the CLI commands defined in src.main.
"""
import sys
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

# Ensure we are running from the project root in context
# (Assumes this file is in src/pipeline_wrappers.py)

def _run_command(command_parts):
    """
    Helper to run a subprocess command in the project root.
    """
    cmd = [sys.executable, "-m"] + command_parts
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    # Assuming the CWD for Airflow is acceptable, or we might need to set it.
    # For now, we rely on python path being set correctly in Airflow.
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        raise Exception(f"Command failed with code {result.returncode}: {result.stderr}")
    
    logger.info(f"Command output: {result.stdout}")
    return result.stdout

def run_crawl_json():
    """Executes: python -m src.main crawl-to-json"""
    _run_command(["src.main", "crawl-to-json"])

def run_update_embeddings():
    """Executes: python -m src.main update-embeddings"""
    _run_command(["src.main", "update-embeddings"])

def run_build_static():
    """Executes: python -m src.main build-static"""
    _run_command(["src.main", "build-static"])

def run_match_profiles(all_profiles=False):
    """Executes: python -m src.main match-profiles --all"""
    args = ["src.main", "match-profiles"]
    if all_profiles:
        args.append("--all")
    _run_command(args)
