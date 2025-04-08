# SageMaker Deployment Project

This directory contains scripts and configurations for deploying ML models to AWS SageMaker.

## Main Components

- `build_and_test_locally.py` - Script to build and test the model container locally
- `push_container_to_ecr.py` - Script to push the container to AWS ECR
- `deploy_serverless.py` - Script to deploy the model as a serverless endpoint
- `test_model.py` - Script to test the deployed model
- `run_local_server.py` - Script to run the model locally for testing
- `delete_sagemaker_resources.py` - Script to clean up AWS resources

## Configuration Files

- `config.yaml` - Main configuration file
- `.env` - Environment variables (copy from `.env.example`)
- `requirements.txt` - Python dependencies

## Directories

- `inference_container/` - Docker container configuration


## AWS IAM

- `iam_setup_instructions.md` - Instructions for setting up IAM roles
- `sagemaker-s3-policy.json` - S3 access policy
- `sagemaker-cloudwatch-policy.json` - CloudWatch access policy
- `trust-policy.json` - Trust relationship policy 

## SageMaker Deployment Commands

```
# Run local inference server
python run_local_server.py

# Test model locally
python test_model.py --url http://localhost:8000/invocations --image car.jpg --save my_result.jpg

# Build container and test locally
python build_and_test_locally.py

# Push container to Amazon ECR
python build_and_push_to_ecr.py

# Deploy serverless endpoint on SageMaker
python deploy_serverless.py --custom-container

# Test deployed endpoint
python test_model.py --endpoint https://runtime.sagemaker.us-east-2.amazonaws.com/endpoints/yolov8-serverless-endpoint/invocations --image car.jpg --save my_result.jpg
```