#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import argparse
import tempfile
import shutil
import yaml
from datetime import datetime
from dotenv import load_dotenv
from ray.job_submission import JobSubmissionClient

# Load environment variables
load_dotenv()

# Function for loading configuration
def load_config(config_path="ray_training_config.yaml"):
    """Loads and returns configuration from file."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file {config_path} not found")
        return None
        
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

# Getting Weights & Biases parameters from environment
def get_wandb_params():
    """Gets W&B parameters from environment."""
    return {
        'api_key': os.environ.get("WANDB_API_KEY", ""),
        'entity': os.environ.get("WANDB_ENTITY", "")
    }

# Getting GitHub Actions parameters from environment
def get_github_params():
    """Gets GitHub Actions parameters from environment."""
    return {
        'run_id': os.environ.get("GITHUB_RUN_ID", ""),
        'sha': os.environ.get("GITHUB_SHA", ""),
        'repository': os.environ.get("GITHUB_REPOSITORY", ""),
        'is_action': os.environ.get("GITHUB_ACTIONS", "false").lower() in ("true", "1", "yes")
    }

def prepare_job_files(config_file="ray_training_config.yaml"):
    """Prepare files for Ray job submission"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="ray_github_action_")
    print(f"Created temporary directory for job files")
    
    # Essential files to copy
    required_files = [
        "train_yolo.py",
        "check_gpu.py",
        "ray_gpu_trainer.py",
        config_file,
        "requirements.txt"
    ]
    
    # Include optional files if they exist
    if os.path.exists(".env"):
        required_files.append(".env")
    
    if os.path.exists("data.yaml"):
        required_files.append("data.yaml")
    
    # Copy files to temp directory
    missing_essentials = []
    for file in required_files:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(temp_dir, file))
            print(f"  - Copied {file}")
        else:
            print(f"Warning: Required file '{file}' not found")
            if file in ["train_yolo.py", "check_gpu.py", "ray_gpu_trainer.py"]:
                missing_essentials.append(file)
    
    if missing_essentials:
        print(f"Error: Essential files missing: {', '.join(missing_essentials)}")
        shutil.rmtree(temp_dir)
        return None
    
    return temp_dir

def run_ray_job(ray_address, work_dir, show_logs=False):
    """Run training job on Ray cluster"""
    try:
        # Load config
        config_file = os.path.join(work_dir, "ray_training_config.yaml")
        config = load_config(config_file)
        if not config:
            return "ERROR"
            
        wandb_project = config["wandb_project"]
        python_exec = config["ray_python_path"]
        
        print(f"Loaded config: W&B project={wandb_project}, Show logs={show_logs}")
        
        # Connect to Ray
        client = JobSubmissionClient(ray_address)
        print(f"Connected to Ray cluster at {ray_address}")
        
        # Environment variables
        env_vars = {
            "PYTHONUNBUFFERED": "1",
        }
        
        # Get and add W&B parameters
        wandb_params = get_wandb_params()
        if wandb_params['api_key']:
            env_vars["WANDB_API_KEY"] = wandb_params['api_key']
        if wandb_params['entity']:
            env_vars["WANDB_ENTITY"] = wandb_params['entity']
        
        # Add GitHub parameters
        github_params = get_github_params()
        if github_params['run_id']:
            env_vars["GITHUB_RUN_ID"] = github_params['run_id']
        if github_params['sha']:
            env_vars["GITHUB_SHA"] = github_params['sha']
        if github_params['repository']:
            env_vars["GITHUB_REPOSITORY"] = github_params['repository']
            
        # Set IS_GITHUB_ACTION environment variable for ray_gpu_trainer.py to detect
        env_vars["IS_GITHUB_ACTION"] = "true"
        
        # Submit job
        print("Submitting job to Ray cluster...")
        job_id = client.submit_job(
            entrypoint=f"{python_exec} ray_gpu_trainer.py",
            runtime_env={
                "working_dir": work_dir,
                "env_vars": env_vars,
                # Request GPU resources
                "resources": {"GPU": 1}
            }
        )
        
        print(f"Job submitted (ID: {job_id})")
        print(f"NOTE: This job will trigger worker node autoscaling to get resources")
        
        # Display W&B information if available
        if wandb_params['api_key']:
            print(f"W&B tracking enabled. Check: https://wandb.ai/{wandb_params['entity'] or 'your-username'}/{wandb_project}")
        else:
            print("Warning: W&B API key not set. Tracking will be limited.")
        
        # If show_logs=True, show logs in real-time
        if show_logs:
            print("Monitoring job logs in real-time. Press Ctrl+C to stop monitoring (job will continue)...")
            previous_logs = ""
            
            try:
                while True:
                    status = client.get_job_status(job_id)
                    logs = client.get_job_logs(job_id)
                    
                    # Print only new log lines
                    if logs and logs != previous_logs:
                        new_logs = logs[len(previous_logs):]
                        if new_logs:
                            print(new_logs, end="")
                        previous_logs = logs
                    
                    # Check if job completed
                    if status in ["SUCCEEDED", "FAILED", "STOPPED"]:
                        print(f"\nJob {status}")
                        break
                        
                    # Short pause between log requests
                    time.sleep(2)
            except KeyboardInterrupt:
                print("\nStopped monitoring logs. The job will continue running.")
                print(f"You can check the job status later or view results in W&B.")
                # We only stop monitoring, but don't stop the task
            
            # Save basic information about the running task
            # Create result for GitHub Actions
            training_info = {
                "status": "MONITORING_COMPLETED",
                "github_run_id": github_params['run_id'],
                "github_sha": github_params['sha'],
                "github_repository": github_params['repository'],
                "job_id": job_id,
                "completed_at": datetime.now().isoformat(),
            }
            
            # Save information to file
            with open("training_info.json", "w") as f:
                json.dump(training_info, f, indent=2)
            
            # Write output parameters for GitHub Actions
            if os.getenv("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write(f"status=MONITORING_COMPLETED\n")
                    f.write(f"job_id={job_id}\n")
                    f.write(f"message=Training job is running, monitoring logs has completed\n")
        else:
            print(f"Job is running in the background (logs not shown).")
            print(f"You can view results in W&B when the job completes.")
            # Get current job status
            status = client.get_job_status(job_id)
            print(f"Current job status: {status}")
            print(f"Job ID: {job_id} - save this ID if you need to check status later")
            
            # Save basic information about the running task
            # Create result for GitHub Actions
            training_info = {
                "status": "SUBMITTED",
                "github_run_id": github_params['run_id'],
                "github_sha": github_params['sha'],
                "github_repository": github_params['repository'],
                "job_id": job_id,
                "submitted_at": datetime.now().isoformat(),
            }
            
            # Save information to file
            with open("training_info.json", "w") as f:
                json.dump(training_info, f, indent=2)
            
            # Write output parameters for GitHub Actions
            if os.getenv("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write(f"status=SUBMITTED\n")
                    f.write(f"job_id={job_id}\n")
                    f.write(f"message=Training job has been submitted to Ray cluster\n")
        
        return job_id
        
    except Exception as e:
        print(f"Error: {e}")
        return "ERROR"

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run YOLO training on Ray cluster from GitHub Actions')
    parser.add_argument('--ray-address', type=str, 
                        default=os.getenv("RAY_ADDRESS", "http://3.144.156.238:8265"),
                        help='Ray cluster address')
    parser.add_argument('--show-logs', action='store_true',
                        help='Show Ray job logs in real-time')
    
    args = parser.parse_args()
    
    # Make sure the config file exists
    config = load_config("ray_training_config.yaml")
    if not config:
        return 1
    
    # Show logs only if the --show-logs flag is explicitly specified
    show_logs = args.show_logs
    
    # If log display is enabled, show a message
    if show_logs:
        print("Note: Real-time log display is enabled")
    
    # Get GitHub parameters for information
    github_params = get_github_params()
    
    # Display execution settings
    print("========== YOLO Training on Ray Cluster (GitHub Actions) ==========")
    print(f"Ray Address: {args.ray_address}")
    print(f"Model: {config['model_type']}")
    print(f"Data: {config['dataset']}")
    print(f"Epochs: {config['epochs']}")
    print(f"Batch size: {config['batch_size']}")
    print(f"Image size: {config['img_size']}")
    print(f"Show logs: {'Yes' if show_logs else 'No'}")
    print(f"GitHub Run ID: {github_params['run_id']}")
    print(f"GitHub SHA: {github_params['sha']}")
    print("===================================================================")
    
    # Prepare job files
    work_dir = prepare_job_files()
    if not work_dir:
        print("Failed to prepare job files")
        return 1
    
    try:
        # Run the job - pass the show_logs argument from the command line
        result = run_ray_job(args.ray_address, work_dir, show_logs=show_logs)
        
        # Result processing
        if isinstance(result, str) and result == "ERROR":
            # Error when launching the task
            print("========================================")
            print(f"❌ Failed to submit training job")
            print("========================================")
            return 1
        
        # Task successfully launched
        print("========================================")
        print(f"🚀 Training job has been submitted to Ray cluster")
        print(f"Check W&B dashboard for results")
        print("========================================")
        return 0
                
    finally:
        # Clean up
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
            print(f"Cleaned up temporary directory: {work_dir}")

if __name__ == "__main__":
    sys.exit(main()) 