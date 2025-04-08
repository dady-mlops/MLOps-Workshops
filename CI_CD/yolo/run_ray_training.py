#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
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

def prepare_job_files(config_file="ray_training_config.yaml"):
    """Prepare files for Ray job submission"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="ray_training_")
    print(f"Created temporary directory for job files")
    
    # Essential files to copy
    required_files = [
        "train_yolo.py",
        "check_gpu.py",
        "ray_gpu_trainer.py",
        config_file,
        "requirements.txt"  # Always include requirements.txt
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

def run_ray_job(ray_address, work_dir, config_file):
    """Run training job on Ray cluster"""
    try:
        # Load config
        config = load_config(config_file)
        if not config:
            return "ERROR"
            
        show_logs = config.get("show_ray_logs", False)
        wandb_project = config.get("wandb_project")
        python_exec = config["ray_python_path"]
        
        # Connect to Ray
        client = JobSubmissionClient(ray_address)
        print(f"Connected to Ray cluster at {ray_address}")
        
        # Environment variables
        env_vars = {
            "PYTHONUNBUFFERED": "1",
        }
        
        # Add W&B credentials if available
        wandb_params = get_wandb_params()
        if wandb_params['api_key']:
            env_vars["WANDB_API_KEY"] = wandb_params['api_key']
        if wandb_params['entity']:
            env_vars["WANDB_ENTITY"] = wandb_params['entity']
        
        # Submit job (assuming cluster already has all required packages)
        print("Submitting job to Ray cluster...")
        job_id = client.submit_job(
            # Run script directly, without using Ray API
            entrypoint=f"{python_exec} ray_gpu_trainer.py",
            runtime_env={
                "working_dir": work_dir,
                "env_vars": env_vars,
                # Request GPU
                "resources": {"GPU": 1}
            }
        )
        
        print(f"Job submitted (ID: {job_id})")
        
        # Display W&B information if available
        if wandb_params['api_key'] and wandb_project:
            print(f"W&B tracking enabled. Check: https://wandb.ai/{wandb_params['entity'] or 'your-username'}/{wandb_project}")
        else:
            print("Warning: W&B API key or project not set. Tracking will be limited.")
        
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
                return "MONITORING_STOPPED"
        else:
            print(f"Job is running in the background (logs not shown).")
            print(f"You can view results in W&B when the job completes.")
            # Get current job status
            status = client.get_job_status(job_id)
            print(f"Current job status: {status}")
            print(f"Job ID: {job_id} - save this ID if you need to check status later")
            return "SUBMITTED"
        
        return status
        
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return "CANCELLED"
        
    except Exception as e:
        print(f"Error: {e}")
        return "ERROR"

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run YOLO training on Ray cluster')
    parser.add_argument('--ray-address', type=str, default="http://3.144.156.238:8265", 
                        help='Ray cluster address')
    parser.add_argument('--config', type=str, default="ray_training_config.yaml", 
                        help='Configuration file')
    parser.add_argument('--show-logs', action='store_true',
                        help='Show Ray job logs in real-time (overrides config setting)')
    parser.add_argument('--wait', action='store_true',
                        help='Wait for job completion even if show_ray_logs is false')
    
    args = parser.parse_args()
    
    # Verify config file
    config = load_config(args.config)
    if not config:
        return 1
    
    # If --show-logs parameter is specified, override the value from config
    if args.show_logs:
        config["show_ray_logs"] = True
        print("Note: Enabling real-time log display due to --show-logs flag")
    
    # Print execution settings
    print(f"========== YOLO Training using Ray Cluster ==========")
    print(f"Ray Address: {args.ray_address}")
    print(f"Model: {config['model_type']}")
    print(f"Data: {config['dataset']}")
    print(f"Epochs: {config['epochs']}")
    print(f"Batch size: {config['batch_size']}")
    print(f"Image size: {config['img_size']}")
    print(f"W&B Project: {config.get('wandb_project', 'Not set')}")
    print(f"Show logs: {'Yes' if config.get('show_ray_logs', False) else 'No'}")
    print(f"Wait for completion: {'Yes' if args.wait else 'No'}")
    print("====================================================")
    
    # Prepare job files
    work_dir = prepare_job_files(args.config)
    if not work_dir:
        return 1
    
    try:
        # Run the job
        status = run_ray_job(args.ray_address, work_dir, args.config)
        
        # If job is submitted but we don't wait for its completion
        if status == "SUBMITTED" and not args.wait:
            print("Job submitted successfully and running in the background.")
            print("You can view results in W&B when the job completes.")
            return 0
            
        # If monitoring was stopped, but we should wait for completion
        if status == "MONITORING_STOPPED" and args.wait:
            print("Waiting for job to complete without displaying logs...")
            client = JobSubmissionClient(args.ray_address)
            job_id = None
            
            # Get list of tasks and find ours by timestamp
            try:
                jobs = client.list_jobs()
                if jobs:
                    # Take the most recent task (assuming it's ours)
                    job_id = jobs[0]["job_id"]
                    
                # Wait for task completion
                while True:
                    status = client.get_job_status(job_id)
                    if status in ["SUCCEEDED", "FAILED", "STOPPED"]:
                        print(f"\nJob {status}")
                        break
                    time.sleep(10)
                    print(".", end="", flush=True)
            except Exception as e:
                print(f"Error waiting for job: {e}")
                return 1
        
        # Report final status
        if status in ["SUCCEEDED", "SUBMITTED", "MONITORING_STOPPED"]:
            print("✅ Job handled successfully")
            wandb_params = get_wandb_params()
            wandb_project = config.get("wandb_project")
            
            if wandb_params['api_key'] and wandb_project:
                print(f"Check Weights & Biases dashboard: https://wandb.ai/{wandb_params['entity'] or 'your-username'}/{wandb_project}")
            
            return 0
        else:
            print(f"❌ Job failed with status: {status}")
            return 1
                
    finally:
        # Clean up
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
            print(f"Cleaned up temporary directory: {work_dir}")

if __name__ == "__main__":
    sys.exit(main()) 