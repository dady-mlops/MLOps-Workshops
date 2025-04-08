#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ray
import json
import subprocess
import yaml
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable unnecessary output from Ray
os.environ["RAY_DISABLE_JUPYTER_PROGRESS"] = "1"
logging.getLogger("ray").setLevel(logging.ERROR)

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

# Ray is automatically initialized when running a job on a cluster
# DO NOT need to call ray.init() here

# Define Ray actor with GPU requirement
@ray.remote(num_gpus=1)
class GPUTrainer:
    def __init__(self):
        # Get GitHub context from environment if running as GitHub Action
        self.is_github_action = os.environ.get("IS_GITHUB_ACTION", "").lower() in ("1", "true", "yes")
        
        if self.is_github_action:
            self.github_run_id = os.getenv("GITHUB_RUN_ID", "")
            self.github_sha = os.getenv("GITHUB_SHA", "")
            self.github_repo = os.getenv("GITHUB_REPOSITORY", "")
            print(f"Running as GitHub Action: Run ID: {self.github_run_id}, SHA: {self.github_sha}")
        
        # Check if we need to install dependencies
        self.config_file = self._find_config_file(["ray_training_config.yaml"])
        self.config = None
        
        if self.config_file:
            self.config = load_config(self.config_file)
            if self.config and self.config["auto_install_deps"]:
                self._install_dependencies()
            else:
                print(f"Skipping dependencies installation (disabled in config)")
        else:
            # No config file found, install dependencies by default
            self._install_dependencies()
        
        # Run GPU check
        self.gpu_info = self._check_gpu()
        print(f"GPU status: {self.gpu_info.get('cuda_available', False)}")

    def _find_config_file(self, config_files):
        """Find the first existing config file from the list"""
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"Using configuration file: {config_file}")
                return config_file
        print("Warning: No configuration file found")
        return None
    
    def _install_dependencies(self):
        """Install required dependencies from requirements.txt file"""
        try:
            print("Installing dependencies from requirements.txt...")
            # Use custom Python path if specified
            python_exec = os.environ.get("RAY_PYTHON_PATH", sys.executable)
            
            # Check if requirements.txt exists
            if not os.path.exists("requirements.txt"):
                print("Warning: requirements.txt not found, skipping dependencies installation")
                return
            
            # Install dependencies from requirements.txt
            try:
                print("Running pip install -r requirements.txt...")
                subprocess.check_call([
                    python_exec, "-m", "pip", "install", "-r", "requirements.txt"
                ])
                print("Dependencies installation completed successfully")
            except Exception as e:
                print(f"Error installing dependencies: {e}")
                
        except Exception as e:
            print(f"Error in dependencies installation: {e}")
    
    def _check_gpu(self):
        """Check GPU availability"""
        try:
            # Use custom Python path if specified
            python_exec = os.environ.get("RAY_PYTHON_PATH", sys.executable)
            subprocess.run([python_exec, "check_gpu.py"], check=False)
            
            if os.path.exists("gpu_check_result.json"):
                with open("gpu_check_result.json", "r") as f:
                    return json.load(f)
            return {"cuda_available": False}
        except Exception as e:
            print(f"Error checking GPU: {e}")
            return {"cuda_available": False}
    
    def run_training(self, config_file=None):
        """Run YOLO training with config parameters"""
        try:
            # Use provided config_file or the one found during initialization
            if config_file:
                config = load_config(config_file)
            else:
                config = self.config
            
            # Check if we have a valid configuration
            if not config:
                return {"status": "error", "error": f"Config file not found or invalid"}
            
            # Setup W&B integration if API key exists
            wandb_api_key = os.environ.get("WANDB_API_KEY", "")
            if wandb_api_key:
                os.system("yolo settings wandb=True")
                
                # Set W&B project from config
                wandb_project = config["wandb_project"]
                os.environ["WANDB_PROJECT"] = wandb_project
                print(f"Using W&B project: {wandb_project}")
            
            # Select device (GPU or CPU)
            device = "0" if self.gpu_info.get("cuda_available", False) else "cpu"
            
            # Get training parameters from config
            epochs = config["epochs"]
            batch_size = config["batch_size"] 
            img_size = config["img_size"]
            model = config["model_type"]
            data = config["dataset"]
            project = config["wandb_project"]
            
            # Define run name
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            base_name = config["run_name"] if "run_name" in config else "yolo-training"
            
            if self.is_github_action:
                # For GitHub Actions add information about commit and run
                if self.github_run_id:
                    github_sha_short = self.github_sha[:7] if self.github_sha else ""
                    name = f"{base_name}-{timestamp}-gh{self.github_run_id}-{github_sha_short}"
                else:
                    name = f"{base_name}-{timestamp}-github"
            else:
                # For regular runs use same format with date and time
                name = f"{base_name}-{timestamp}"
            
            # Use custom Python path if specified
            python_exec = os.environ.get("RAY_PYTHON_PATH", sys.executable)
            
            cmd = [
                python_exec, "train_yolo.py",
                "--model", model,
                "--data", data,
                "--epochs", str(epochs),
                "--batch-size", str(batch_size),
                "--img-size", str(img_size),
                "--device", device,
                "--project", project,
                "--name", name
            ]
            
            print(f"Starting training: {model} on {device}")
            print(f"Command: {' '.join(cmd)}")
            
            # Run training process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=dict(os.environ, PYTHONUNBUFFERED='1')
            )
            
            # Capture process output
            wandb_url = None
            
            # Process output stream
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    print(line.rstrip())
                    
                    # Capture W&B URL if present
                    if "View run at" in line and "wandb.ai" in line:
                        try:
                            wandb_url = line.split("View run at")[1].strip()
                            with open('wandb_run_url.txt', 'w') as f:
                                f.write(wandb_url)
                        except:
                            pass
            
            # Get process result
            returncode = process.poll()
            success = returncode == 0
            
            # Create result object
            result = {
                "status": "success" if success else "error",
                "returncode": returncode,
                "device_used": device,
                "wandb_url": wandb_url,
                "completed_at": datetime.now().isoformat()
            }
            
            # Add GitHub information if available
            if self.is_github_action:
                result.update({
                    "github_run_id": self.github_run_id,
                    "github_sha": self.github_sha,
                    "github_repository": self.github_repo,
                    "run_name": name,
                    "gpu_available": self.gpu_info.get("cuda_available", False)
                })
            
            # Save result
            with open("training_result.json", "w") as f:
                json.dump(result, f, indent=2)
            
            # Print result JSON for GitHub Actions to parse
            if self.is_github_action:
                print(json.dumps(result))
                
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error_message": str(e),
                "device_used": "unknown",
                "completed_at": datetime.now().isoformat()
            }
            
            # Add GitHub information if available
            if self.is_github_action:
                error_result.update({
                    "github_run_id": self.github_run_id if hasattr(self, 'github_run_id') else "",
                    "github_sha": self.github_sha if hasattr(self, 'github_sha') else "",
                    "github_repository": self.github_repo if hasattr(self, 'github_repo') else ""
                })
            
            # Save error result
            with open("training_result.json", "w") as f:
                json.dump(error_result, f, indent=2)
            
            # Print error result JSON for GitHub Actions to parse
            if hasattr(self, 'is_github_action') and self.is_github_action:
                print(json.dumps(error_result))
                
            return error_result

def main():
    """
    Main function for starting training.
    Determines whether it's run as part of a Ray task or directly.
    """
    # Check if the script is running as part of a Ray job
    is_ray_job = "RAY_JOB_ID" in os.environ
    
    if is_ray_job:
        # Running inside a Ray job, start directly without Actor
        print("Running as part of Ray job")
        trainer = GPUTrainer.__new__(GPUTrainer)
        trainer.__init__()
        result = trainer.run_training()
    else:
        # Running directly, use Ray API
        print("Running as standalone script, initializing Ray")
        ray.init(ignore_reinit_error=True)
        trainer = GPUTrainer.remote()
        result = ray.get(trainer.run_training.remote())
    
    print(f"Training completed: {result['status']}")
    return result

if __name__ == "__main__":
    main() 