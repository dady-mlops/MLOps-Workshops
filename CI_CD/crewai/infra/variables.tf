variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "name_ai_write_agent_service" {
  description = "Name of the App Runner application"
  type        = string
  default     = "ai-agents-app"
}

variable "app_port_ai_write_agent_service" {
  description = "Port on which the container listens"
  type        = number
  default     = 5000
}

variable "ai_write_agent_service_cpu" {
  description = "CPU units for the App Runner service"
  type        = string
  default     = "1 vCPU"
}

variable "ai_write_agent_service_memory" {
  description = "Memory for the App Runner service"
  type        = string
  default     = "2 GB"
}

variable "DB_PASSWORD" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

variable "SECRET_KEY" {
  description = "Secret key for the application"
  type        = string
  sensitive   = true
}

variable "DEFAULT_ADMIN_PASSWORD" {
  description = "Default admin password"
  type        = string
  sensitive   = true
}

variable "OPENAI_API_KEY" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "WANDB_API_KEY" {
  description = "Weights & Biases API key"
  type        = string
  sensitive   = true
}

variable "FIRECRAWL_API_KEY" {
  description = "FireCrawl API key"
  type        = string
  sensitive   = true
}
