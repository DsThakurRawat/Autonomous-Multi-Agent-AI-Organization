variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "ai-org"
}

variable "backend_image" {
  description = "Backend Docker image URI"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image URI"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.micro"
}

variable "ecs_backend_cpu" {
  description = "ECS task CPU units for backend"
  type        = number
  default     = 512
}

variable "ecs_backend_memory" {
  description = "ECS task memory (MiB) for backend"
  type        = number
  default     = 1024
}

variable "ecs_frontend_cpu" {
  default = 256
  type    = number
}

variable "ecs_frontend_memory" {
  default = 512
  type    = number
}

variable "min_capacity" {
  default = 1
  type    = number
}

variable "max_capacity" {
  default = 10
  type    = number
}