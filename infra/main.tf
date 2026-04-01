# infra/main.tf
# Terraform provider configuration and shared variables

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # Uncomment for remote state storage
  # backend "s3" {
  #   bucket  = "your-tf-state-bucket"
  #   key     = "iot-health-monitor/terraform.tfstate"
  #   region  = "ap-south-1"
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "iot-health-monitor"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ---------- Variables ----------
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project name prefix for resource naming"
  type        = string
  default     = "iot-health-monitor"
}

variable "alert_email" {
  description = "Email address to receive SNS anomaly alerts"
  type        = string
  sensitive   = true
}

variable "model_bucket" {
  description = "S3 bucket name that holds the ML model artifact"
  type        = string
}

# ---------- SNS Topic for alerts ----------
resource "aws_sns_topic" "health_alerts" {
  name = "${var.project}-health-alerts-${var.environment}"
}

resource "aws_sns_topic_subscription" "email_alert" {
  topic_arn = aws_sns_topic.health_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------- Outputs ----------
output "sns_topic_arn" {
  value = aws_sns_topic.health_alerts.arn
}
