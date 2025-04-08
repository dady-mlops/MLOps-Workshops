terraform {
  required_providers {
    aws = {
      source  = "opentofu/aws"
      version = "5.93.0"
    }
  }
  required_version = ">= 1.9.0"
  backend "remote" {
    hostname = "spodarets.scalr.io"
    organization = "env-v0o06dgi6sivpq3v2"
    workspaces = {
      name = "DataPhoenix-AI-Agents"
    }
  }
}

provider "aws" {
  region = var.aws_region
}