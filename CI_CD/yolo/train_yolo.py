#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import shutil
from ultralytics import YOLO
from datetime import datetime
from dotenv import load_dotenv
import wandb
import yaml

# Load environment variables from .env file
load_dotenv()

# Functions for getting parameters
def get_wandb_params():
    """Gets W&B parameters from environment."""
    return {
        'api_key': os.environ.get("WANDB_API_KEY", ""),
        'entity': os.environ.get("WANDB_ENTITY", "")
    }

def get_training_datetime():
    """Returns current date and time in formatted form."""
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H%M%S')
    }

def get_model_dataset_names(model_type, data):
    """Extracts model and dataset names from paths."""
    # Get model name without extension
    model_name = model_type.split('.')[0] if '.' in model_type else model_type
    model_name = model_name.split('/')[-1] if '/' in model_name else model_name
    
    # Define dataset name
    dataset_name = data.split('.')[0] if '.' in data else data
    dataset_name = dataset_name.split('/')[-1] if '/' in dataset_name else dataset_name
    
    return {
        'model': model_name,
        'dataset': dataset_name
    }

def load_config(config_path="ray_training_config.yaml"):
    """Loads and returns configuration from file."""
    if not os.path.exists(config_path):
        print(f"Warning: Configuration file {config_path} not found")
        return None
        
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Warning: Error loading configuration: {e}")
        return None

def train_yolo_model(
    model_type="yolov8n.pt",
    data="coco8.yaml",
    epochs=5,
    batch_size=16,
    imgsz=640,
    device="",
    project=None,
    name=None,
    resume=False
):
    """
    Train a YOLO model using Ultralytics framework and log results to Weights & Biases.
    
    Args:
        model_type (str): Path to model file, i.e. yolov8n.pt, yolov8s.pt, etc.
        data (str): Path to data YAML file, i.e. data.yaml
        epochs (int): Number of training epochs
        batch_size (int): Batch size for training
        imgsz (int): Image size for training
        device (str): Device to train on, i.e. cuda device=0 or device=0,1,2,3 or device=cpu
        project (str): Project name for W&B logging
        name (str): Experiment name for W&B logging
        resume (bool): Resume training from last checkpoint
        
    Returns:
        YOLO model: Trained model
    """
    # Get W&B parameters
    wandb_params = get_wandb_params()
    
    if not wandb_params['api_key']:
        print("Warning: WANDB_API_KEY not found in environment variables or .env file")
    else:
        print(f"Using W&B API key from environment")
        os.environ["WANDB_API_KEY"] = wandb_params['api_key']
    
    # Get date and time
    dt = get_training_datetime()
    date_str = dt['date']
    time_str = dt['time']
    
    # Get model and dataset names
    names = get_model_dataset_names(model_type, data)
    model_name = names['model']
    dataset_name = names['dataset']
    
    # If project is not specified, try to load from configuration
    if project is None:
        config = load_config()
        if config and "wandb_project" in config:
            project = config["wandb_project"]
            print(f"Using project name from config: {project}")
        else:
            print("Error: project name not provided and not found in config")
            return None
    
    entity = wandb_params['entity']
    
    # Generate experiment name with timestamp if not provided
    if name is None:
        # Create structured name: dataset_model_date_time
        name = f"{dataset_name}_{model_name}_{date_str}_{time_str}"
    
    # Enable W&B integration with Ultralytics
    os.system("yolo settings wandb=True")
    
    print(f"Starting YOLO training:")
    print(f"  - Model: {model_type}")
    print(f"  - Data: {data}")
    print(f"  - Epochs: {epochs}")
    print(f"  - Batch size: {batch_size}")
    print(f"  - Image size: {imgsz}")
    print(f"  - Device: {device}")
    print(f"  - Project: {project}")
    print(f"  - Run name: {name}")
    print(f"  - Resume: {resume}")
    
    try:
        # Load the model
        if resume:
            # Resume from last checkpoint
            model = YOLO(model_type)
            print(f"Resuming training from {model_type}")
        else:
            # Start fresh training
            if model_type.endswith('.yaml'):
                # Build a new model from YAML
                model = YOLO(model_type)
                print(f"Building new model from {model_type}")
            elif model_type.endswith('.pt'):
                # Load a pretrained model
                model = YOLO(model_type)
                print(f"Loading pretrained model {model_type}")
            else:
                raise ValueError(f"Unsupported model format: {model_type}. Use .pt or .yaml files.")
        
        # Train the model
        results = model.train(
            data=data,
            epochs=epochs,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            project=project,
            name=name,
            exist_ok=True,
            pretrained=True,
            optimizer="Adam",  # Optimizer (Adam, SGD, etc.)
            lr0=1e-3,          # Initial learning rate
            lrf=1e-4,          # Final learning rate
            momentum=0.937,    # SGD momentum/Adam beta1
            weight_decay=5e-4, # Optimizer weight decay
            warmup_epochs=1.0, # Warmup epochs
            warmup_momentum=0.8, # Warmup initial momentum
            warmup_bias_lr=0.1,  # Warmup initial bias lr
            save=True,         # Save checkpoints
            save_period=1,     # Save checkpoint every x epochs
            workers=8,         # Number of worker threads for data loading
            verbose=True,      # Verbose output
            seed=42            # Random seed for reproducibility
        )
        
        print(f"Training completed successfully")
        
        # Validate the model
        print(f"Running validation...")
        val_results = model.val(
            data=data,
            project=project,
            name=name
        )
        
        print(f"Validation completed:")
        for k, v in val_results.results_dict.items():
            print(f"  - {k}: {v}")
        
        # Log additional information to W&B (if needed)
        if wandb.run is not None:
            # Save the W&B run URL to a file for GitHub Actions
            run_url = wandb.run.get_url()
            print(f"W&B run URL: {run_url}")
            with open("wandb_run_url.txt", "w") as f:
                f.write(run_url)
                
            # Log the best model as an artifact to W&B
            best_model_path = os.path.join(project, name, "weights", "best.pt")
            if os.path.exists(best_model_path):
                # Create artifact name in format: yolo_model_dataset_date
                artifact_name = f"yolo_{model_name}_{dataset_name}_{date_str}"
                
                # Explicitly specify artifact version to avoid automatic renaming
                run_id = wandb.run.id
                artifact_version = f"v{time_str}"
                
                # Create a local copy of the model with a descriptive name
                named_model_path = os.path.join(project, f"{artifact_name}.pt")
                try:
                    import shutil
                    shutil.copy2(best_model_path, named_model_path)
                    print(f"Model saved locally as: {named_model_path}")
                except Exception as e:
                    print(f"Warning: Could not save named model copy: {e}")
                
                artifact = wandb.Artifact(
                    name=artifact_name, 
                    type="model",
                    description=f"YOLOv8 model trained on {dataset_name} dataset"
                )
                
                # Add model file with explicit file name
                artifact.add_file(best_model_path, name=f"{artifact_name}.pt")
                
                # Add metadata to artifact
                artifact.metadata = {
                    "model_type": model_type,
                    "dataset": data,
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "image_size": imgsz,
                    "training_date": date_str,
                    "training_time": time_str,
                    "run_name": name,
                    "run_id": run_id,
                    "artifact_version": artifact_version
                }
                
                # Save artifact
                artifact_id = wandb.log_artifact(artifact, aliases=["latest", f"epoch_{epochs}", artifact_version])
                print(f"Best model saved to W&B as artifact: {artifact_name} ({artifact_version})")
                
                # Additionally save model information in wandb
                wandb.config.update({
                    "model_artifact": artifact_name,
                    "model_artifact_version": artifact_version,
                    "model_artifact_id": artifact_id.id if hasattr(artifact_id, 'id') else None
                })
        
        return model
    
    except Exception as e:
        print(f"Error during model training: {e}")
        return None
    
    finally:
        # Make sure to finish the W&B run
        if wandb.run is not None:
            # Save the W&B run URL before finishing
            if not os.path.exists("wandb_run_url.txt"):
                try:
                    run_url = wandb.run.get_url()
                    with open("wandb_run_url.txt", "w") as f:
                        f.write(run_url)
                    print(f"Saved W&B run URL to wandb_run_url.txt: {run_url}")
                except Exception as e:
                    print(f"Error saving W&B run URL: {e}")
            
            wandb.finish()
            print("W&B logging completed")

if __name__ == "__main__":
    # Try to load configuration for default values
    config = load_config()
    default_project = None
    
    if config and "wandb_project" in config:
        default_project = config["wandb_project"]
    
    parser = argparse.ArgumentParser(description="Train YOLO model with W&B integration")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Model file (.pt) or configuration (.yaml)")
    parser.add_argument("--data", type=str, default="data.yaml", help="Dataset configuration file")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--img-size", type=int, default=640, help="Image size")
    parser.add_argument("--device", type=str, default="", help="Device to use (e.g., cpu, 0, 0,1, mps)")
    parser.add_argument("--project", type=str, default=default_project, help="Project name for W&B (default from config)")
    parser.add_argument("--name", type=str, default=None, help="Run name for W&B")
    parser.add_argument("--resume", action="store_true", help="Resume training from last checkpoint")
    
    args = parser.parse_args()
    
    # Train model
    model = train_yolo_model(
        model_type=args.model,
        data=args.data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        imgsz=args.img_size,
        device=args.device,
        project=args.project,
        name=args.name,
        resume=args.resume
    )
