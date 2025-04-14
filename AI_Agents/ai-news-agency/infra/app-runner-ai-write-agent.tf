resource "aws_apprunner_service" "ai_write_agent_service" {
  service_name = var.name_ai_write_agent_service

  source_configuration {
    auto_deployments_enabled = false

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_role.arn
    }

    image_repository {
      image_identifier      = "493395458839.dkr.ecr.us-east-1.amazonaws.com/dataphoenix-writer-agent:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = var.app_port_ai_write_agent_service
        runtime_environment_variables = {
            DB_TYPE            = "postgres"
            DB_USER            = "spodarets"
            DB_HOST            = "strapi-rds.c6pnm6c9jp1s.us-east-1.rds.amazonaws.com"
            DB_PORT            = "5432"
            DB_NAME            = "ai-news-agency-db"
            DB_SSL             = "true"
            DB_SSL_REJECT_UNAUTHORIZED = "false"
            WANDB_PROJECT      = "ai-news-agency"
            WANDB_ENTITY       = "dmytro-spodarets"
            DEFAULT_ADMIN_USERNAME = "admin"
            # Add variable for debugging
            DEBUG_MODE         = "true"
        }
        
        # Use runtime_environment_secrets for SSM parameters
        runtime_environment_secrets = {
            DB_PASSWORD        = aws_ssm_parameter.db_password.arn
            SECRET_KEY         = aws_ssm_parameter.secret_key.arn
            DEFAULT_ADMIN_PASSWORD = aws_ssm_parameter.admin_password.arn
            OPENAI_API_KEY     = aws_ssm_parameter.openai_api_key.arn
            WANDB_API_KEY      = aws_ssm_parameter.wandb_api_key.arn
            FIRECRAWL_API_KEY  = aws_ssm_parameter.firecrawl_api_key.arn
        }
      }
    }
  }

  instance_configuration {
    cpu                = var.ai_write_agent_service_cpu
    memory             = var.ai_write_agent_service_memory
    instance_role_arn  = aws_iam_role.apprunner_service_role.arn
  }

  tags = {
    Name = "ai-agents-app"
  }
}

# Create parameters in SSM Parameter Store
resource "aws_ssm_parameter" "db_password" {
  name  = "/ai-agents-app/DB_PASSWORD"
  type  = "SecureString"
  value = var.DB_PASSWORD
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/ai-agents-app/SECRET_KEY"
  type  = "SecureString"
  value = var.SECRET_KEY
}

resource "aws_ssm_parameter" "admin_password" {
  name  = "/ai-agents-app/DEFAULT_ADMIN_PASSWORD"
  type  = "SecureString"
  value = var.DEFAULT_ADMIN_PASSWORD
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/ai-agents-app/OPENAI_API_KEY"
  type  = "SecureString"
  value = var.OPENAI_API_KEY
}

resource "aws_ssm_parameter" "wandb_api_key" {
  name  = "/ai-agents-app/WANDB_API_KEY"
  type  = "SecureString"
  value = var.WANDB_API_KEY
}

resource "aws_ssm_parameter" "firecrawl_api_key" {
  name  = "/ai-agents-app/FIRECRAWL_API_KEY"
  type  = "SecureString"
  value = var.FIRECRAWL_API_KEY
}