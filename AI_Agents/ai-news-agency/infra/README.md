# OpenTofu Infrastructure for AWS App Runner

This project contains OpenTofu configuration for deploying a container to AWS App Runner.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. OpenTofu installed
3. Docker image published to ECR

## Configuration

1. Create `terraform.tfvars` based on `terraform.tfvars.example`
2. Set the following variables:
   - `app_runner_image_identifier` - URI of your Docker image in ECR
   - Other variables as needed

## Deployment

1. Initialize OpenTofu:
   ```bash
   tofu init
   ```

2. Plan changes:
   ```bash
   tofu plan
   ```

3. Apply changes:
   ```bash
   tofu apply
   ```

## Cleanup

To remove all created resources:
```bash
tofu destroy
```

## Structure of the project

```
infra/
├── main.tf                # Основной файл конфигурации
├── variables.tf           # Определение переменных
├── outputs.tf             # Выходные значения
├── terraform.tfvars.example # Пример файла с переменными
└── modules/
    └── app_runner/       # Модуль для AWS App Runner
        ├── main.tf       # Ресурсы App Runner
        ├── variables.tf  # Переменные модуля
        └── outputs.tf    # Выходные значения модуля
```

## Variables

| Name | Description | Type | Default |
|-----|----------|-----|-------------|
| aws_region | AWS region for deployment | string | "us-east-1" |
| app_name | App Runner application name | string | "ai-agents-app" |
| image_uri | Container image URI | string | - |
| container_port | Container port | number | 8080 |
| cpu | CPU for App Runner service | string | "1 vCPU" |
| memory | Memory for App Runner service | string | "2 GB" |
| environment_variables | Environment variables | map(string) | {} |

## Outputs

- `app_runner_service_url` - App Runner service URL
- `app_runner_service_arn` - App Runner service ARN

## Note

This project uses the OpenTofu AWS provider (`opentofu/aws`) version 5.93.0.
