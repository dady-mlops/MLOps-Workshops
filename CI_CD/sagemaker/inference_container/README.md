# SageMaker Inference Container

This directory contains all the necessary files for creating a container for YOLO model inference in Amazon SageMaker. The container supports both CPU and GPU inference.

## Contents

- `Dockerfile` - Multi-stage Dockerfile for creating an optimized container with GPU support
- `app.py` - FastAPI application implementing the `/ping` and `/invocations` endpoints for SageMaker
- `serve` - Script for launching the FastAPI application in the SageMaker container
- `requirements.txt` - Python dependencies required for the application

## SageMaker Requirements Compliance

The container is developed in accordance with AWS SageMaker requirements for custom containers:

1. Web server on port 8080
2. Implementation of `/ping` (HTTP GET) and `/invocations` (HTTP POST) endpoints
3. Request processing within 60 seconds

## Directory Structure

```
/opt/program/            # Working directory with application code
  app.py                 # FastAPI application
  serve                  # Launch script
  
/opt/ml/                 # Standard SageMaker structure
  /model/                # Directory with model files
    model.pt             # YOLO model file
  /input/data/           # Input data (optional)
  /output/data/          # Output data and logs
```

## Usage

To build and push the container to ECR, use:

```bash
python push_container_to_ecr.py
```

To deploy a model using this container, run:

```bash
python deploy_serverless.py --custom-container
```

## Logging

The container is configured to write logs to `/opt/ml/output/data/` with various levels of detail.
Main log files:
- `app.log` - FastAPI application logs
- `startup.log` - Container startup logs
- `access.log` - API access logs 