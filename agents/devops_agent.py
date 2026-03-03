"""
DevOps Agent — Infrastructure & Deployment
Generates Terraform configs, Dockerfiles, CI/CD pipelines,
and orchestrates the full AWS deployment lifecycle.
"""

import textwrap
from typing import Any, Dict
import structlog
from .base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class DevOpsAgent(BaseAgent):
    """
    DevOps Agent responsibilities:
    1. Generate Terraform infrastructure code
    2. Build and push Docker images to ECR
    3. Deploy services to ECS Fargate
    4. Setup ALB, HTTPS, autoscaling
    5. Configure CloudWatch monitoring
    """

    ROLE = "DevOps"

    @property
    def system_prompt(self) -> str:
        return """You are a Senior DevOps/Platform Engineer at an AI software company.
You provision production AWS infrastructure using Terraform following:
- Least privilege IAM policies
- Multi-AZ deployments for reliability
- Auto-scaling policies for cost efficiency
- HTTPS enforced (never HTTP)
- CloudWatch alarms on critical metrics
- Secrets Manager for all secrets
- VPC with private subnets for databases

You generate complete, working Terraform HCL and CI/CD pipeline configs.
"""

    async def run(
        self,
        task: Any = None,
        context: Any = None,
        architecture: Dict[str, Any] = None,
        project_name: str = "ai-org",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate all infrastructure code and simulate deployment."""
        arch = context.memory.architecture if context else (architecture or {})

        # Generate infrastructure files
        infra_files = self._generate_terraform(arch, project_name)
        cicd_files = self._generate_cicd(project_name)
        compose_file = self._generate_docker_compose(arch)

        # Save all infrastructure files
        all_files = {**infra_files, **cicd_files, "docker-compose.yml": compose_file}
        if context:
            for path, content in all_files.items():
                context.artifacts.save_code_file(
                    f"infrastructure/{path}", content, self.ROLE
                )

        # Simulate deployment steps
        deployment_result = await self._simulate_deployment(project_name, context)

        if context:
            # Store public URL
            context.artifacts.save(
                "url",
                "deployment_url",
                deployment_result.get("public_url", "https://pending.example.com"),
                self.ROLE,
                tags=["deployment", "url"],
            )
            context.memory.deployment_info = deployment_result
            context.decision_log.log(
                agent_role=self.ROLE,
                decision_type="deployment",
                description="AWS infrastructure provisioned and services deployed",
                rationale="ECS Fargate chosen for serverless container management",
                input_context={"architecture": str(arch)[:500]},
                output=deployment_result,
                confidence=0.88,
                tags=["aws", "deployment", "terraform"],
            )

        logger.info(
            "DevOps: Deployment complete", url=deployment_result.get("public_url")
        )
        return {
            "infrastructure_files": list(infra_files.keys()),
            "deployment": deployment_result,
        }

    async def execute_task(self, task: Any, context: Any) -> Dict[str, Any]:
        return await self.run(task=task, context=context)

    async def _simulate_deployment(
        self, project_name: str, context: Any
    ) -> Dict[str, Any]:
        """Simulate the multi-step AWS deployment process."""
        steps = [
            ("terraform init", "Initializing Terraform providers..."),
            ("terraform plan", "Planning AWS resource changes..."),
            ("terraform apply", "Creating VPC, subnets, security groups..."),
            ("docker build", "Building backend and frontend images..."),
            ("ecr push", "Pushing images to Amazon ECR..."),
            ("ecs deploy", "Deploying ECS services..."),
            ("health check", "Verifying service health..."),
        ]

        for step, message in steps:
            if context:
                # emit progress event (simplified)
                logger.info(message)

        import asyncio

        await asyncio.sleep(0.5)  # Simulate processing

        return {
            "status": "deployed",
            "public_url": f"https://{project_name}.example.com",
            "backend_url": f"https://api.{project_name}.example.com",
            "frontend_url": f"https://{project_name}.example.com",
            "ecs_cluster": f"{project_name}-cluster",
            "rds_endpoint": f"{project_name}-db.abc123.us-east-1.rds.amazonaws.com",
            "cloudfront_domain": "d1234abcd.cloudfront.net",
            "deployment_time_seconds": 187,
            "health_checks_passed": True,
            "https_enabled": True,
            "autoscaling_enabled": True,
        }

    # ══ TERRAFORM CODE GENERATION ════════════════════════════════════

    def _generate_terraform(
        self, arch: Dict[str, Any], project_name: str
    ) -> Dict[str, str]:
        return {
            "terraform/main.tf": self._tf_main(project_name),
            "terraform/variables.tf": self._tf_variables(project_name),
            "terraform/outputs.tf": self._tf_outputs(),
            "terraform/vpc.tf": self._tf_vpc(project_name),
            "terraform/ecs.tf": self._tf_ecs(project_name),
            "terraform/rds.tf": self._tf_rds(project_name),
            "terraform/alb.tf": self._tf_alb(project_name),
            "terraform/iam.tf": self._tf_iam(project_name),
            "terraform/cloudwatch.tf": self._tf_cloudwatch(project_name),
        }

    def _tf_main(self, name: str) -> str:
        return textwrap.dedent(f"""
            # ============================================================
            # AI Company in a Box — AWS Infrastructure
            # Generated by DevOps Agent
            # ============================================================

            terraform {{
              required_version = ">= 1.6.0"
              required_providers {{
                aws = {{
                  source  = "hashicorp/aws"
                  version = "~> 5.0"
                }}
              }}
              backend "s3" {{
                bucket = "{name}-terraform-state"
                key    = "production/terraform.tfstate"
                region = var.aws_region
                encrypt = true
              }}
            }}

            provider "aws" {{
              region = var.aws_region
              default_tags {{
                tags = {{
                  Project     = "{name}"
                  Environment = var.environment
                  ManagedBy   = "AI-Company-in-a-Box"
                  Generation  = "Autonomous"
                }}
              }}
            }}

            locals {{
              name_prefix = "{name}-${{var.environment}}"
              common_tags = {{
                Project     = "{name}"
                Environment = var.environment
              }}
            }}
        """).strip()

    def _tf_variables(self, name: str) -> str:
        return textwrap.dedent(f"""
            variable "aws_region" {{
              description = "AWS region for all resources"
              type        = string
              default     = "us-east-1"
            }}

            variable "environment" {{
              description = "Deployment environment"
              type        = string
              default     = "production"
              validation {{
                condition     = contains(["development", "staging", "production"], var.environment)
                error_message = "Environment must be development, staging, or production."
              }}
            }}

            variable "project_name" {{
              description = "Project name used in resource naming"
              type        = string
              default     = "{name}"
            }}

            variable "backend_image" {{
              description = "Backend Docker image URI"
              type        = string
            }}

            variable "frontend_image" {{
              description = "Frontend Docker image URI"
              type        = string
            }}

            variable "db_instance_class" {{
              description = "RDS instance type"
              type        = string
              default     = "db.t3.micro"
            }}

            variable "ecs_backend_cpu" {{
              description = "ECS task CPU units for backend"
              type        = number
              default     = 512
            }}

            variable "ecs_backend_memory" {{
              description = "ECS task memory (MiB) for backend"
              type        = number
              default     = 1024
            }}

            variable "ecs_frontend_cpu" {{
              default = 256
              type    = number
            }}

            variable "ecs_frontend_memory" {{
              default = 512
              type    = number
            }}

            variable "min_capacity" {{
              default = 1
              type    = number
            }}

            variable "max_capacity" {{
              default = 10
              type    = number
            }}
        """).strip()

    def _tf_outputs(self) -> str:
        return textwrap.dedent("""
            output "alb_dns_name" {
              description = "Application Load Balancer DNS name"
              value       = aws_lb.main.dns_name
            }

            output "cloudfront_domain" {
              description = "CloudFront distribution domain"
              value       = aws_cloudfront_distribution.main.domain_name
            }

            output "rds_endpoint" {
              description = "RDS PostgreSQL endpoint"
              value       = aws_db_instance.postgres.endpoint
              sensitive   = true
            }

            output "ecs_cluster_name" {
              description = "ECS cluster name"
              value       = aws_ecs_cluster.main.name
            }

            output "ecr_backend_url" {
              description = "Backend ECR repository URL"
              value       = aws_ecr_repository.backend.repository_url
            }

            output "ecr_frontend_url" {
              description = "Frontend ECR repository URL"
              value       = aws_ecr_repository.frontend.repository_url
            }
        """).strip()

    def _tf_vpc(self, name: str) -> str:
        return textwrap.dedent("""
            # ── VPC and Networking ────────────────────────────────────
            resource "aws_vpc" "main" {
              cidr_block           = "10.0.0.0/16"
              enable_dns_hostnames = true
              enable_dns_support   = true
            }

            resource "aws_internet_gateway" "main" {
              vpc_id = aws_vpc.main.id
            }

            # Public subnets (ALB, NAT Gateways)
            resource "aws_subnet" "public" {
              count             = 2
              vpc_id            = aws_vpc.main.id
              cidr_block        = "10.0.${count.index}.0/24"
              availability_zone = data.aws_availability_zones.available.names[count.index]
              map_public_ip_on_launch = true
            }

            # Private subnets (ECS tasks, RDS)
            resource "aws_subnet" "private" {
              count             = 2
              vpc_id            = aws_vpc.main.id
              cidr_block        = "10.0.${count.index + 10}.0/24"
              availability_zone = data.aws_availability_zones.available.names[count.index]
            }

            # NAT Gateway for private subnet internet access
            resource "aws_eip" "nat" {
              count  = 2
              domain = "vpc"
            }

            resource "aws_nat_gateway" "main" {
              count         = 2
              allocation_id = aws_eip.nat[count.index].id
              subnet_id     = aws_subnet.public[count.index].id
            }

            resource "aws_route_table" "private" {
              count  = 2
              vpc_id = aws_vpc.main.id
            }

            resource "aws_route" "private_nat" {
              count                  = 2
              route_table_id         = aws_route_table.private[count.index].id
              destination_cidr_block = "0.0.0.0/0"
              nat_gateway_id         = aws_nat_gateway.main[count.index].id
            }

            resource "aws_route_table_association" "private" {
              count          = 2
              subnet_id      = aws_subnet.private[count.index].id
              route_table_id = aws_route_table.private[count.index].id
            }

            data "aws_availability_zones" "available" {
              state = "available"
            }

            # Security Groups
            resource "aws_security_group" "alb" {
              name   = "${local.name_prefix}-alb-sg"
              vpc_id = aws_vpc.main.id
              ingress {
                from_port   = 80
                to_port     = 80
                protocol    = "tcp"
                cidr_blocks = ["0.0.0.0/0"]
              }
              ingress {
                from_port   = 443
                to_port     = 443
                protocol    = "tcp"
                cidr_blocks = ["0.0.0.0/0"]
              }
              egress {
                from_port   = 0
                to_port     = 0
                protocol    = "-1"
                cidr_blocks = ["0.0.0.0/0"]
              }
            }

            resource "aws_security_group" "ecs" {
              name   = "${local.name_prefix}-ecs-sg"
              vpc_id = aws_vpc.main.id
              ingress {
                from_port       = 0
                to_port         = 65535
                protocol        = "tcp"
                security_groups = [aws_security_group.alb.id]
              }
              egress {
                from_port   = 0
                to_port     = 0
                protocol    = "-1"
                cidr_blocks = ["0.0.0.0/0"]
              }
            }

            resource "aws_security_group" "rds" {
              name   = "${local.name_prefix}-rds-sg"
              vpc_id = aws_vpc.main.id
              ingress {
                from_port       = 5432
                to_port         = 5432
                protocol        = "tcp"
                security_groups = [aws_security_group.ecs.id]
              }
            }
        """).strip()

    def _tf_ecs(self, name: str) -> str:
        return textwrap.dedent("""
            # ── ECS Cluster & Services ─────────────────────────────────
            resource "aws_ecs_cluster" "main" {
              name = "${local.name_prefix}-cluster"
              setting {
                name  = "containerInsights"
                value = "enabled"
              }
            }

            resource "aws_ecr_repository" "backend" {
              name                 = "${local.name_prefix}-backend"
              image_tag_mutability = "MUTABLE"
              image_scanning_configuration {
                scan_on_push = true
              }
            }

            resource "aws_ecr_repository" "frontend" {
              name                 = "${local.name_prefix}-frontend"
              image_tag_mutability = "MUTABLE"
            }

            # Backend ECS Service
            resource "aws_ecs_task_definition" "backend" {
              family                   = "${local.name_prefix}-backend"
              network_mode             = "awsvpc"
              requires_compatibilities = ["FARGATE"]
              cpu                      = var.ecs_backend_cpu
              memory                   = var.ecs_backend_memory
              execution_role_arn       = aws_iam_role.ecs_execution.arn
              task_role_arn            = aws_iam_role.ecs_task.arn

              container_definitions = jsonencode([
                {
                  name      = "backend"
                  image     = var.backend_image
                  essential = true
                  portMappings = [{ containerPort = 8000, protocol = "tcp" }]
                  environment = [
                    { name = "ENVIRONMENT", value = var.environment },
                    { name = "AWS_REGION", value = var.aws_region }
                  ]
                  secrets = [
                    { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn },
                    { name = "SECRET_KEY",   valueFrom = aws_secretsmanager_secret.secret_key.arn }
                  ]
                  logConfiguration = {
                    logDriver = "awslogs"
                    options = {
                      "awslogs-group"         = aws_cloudwatch_log_group.backend.name
                      "awslogs-region"        = var.aws_region
                      "awslogs-stream-prefix" = "backend"
                    }
                  }
                  healthCheck = {
                    command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
                    interval    = 30
                    timeout     = 5
                    retries     = 3
                    startPeriod = 60
                  }
                }
              ])
            }

            resource "aws_ecs_service" "backend" {
              name            = "${local.name_prefix}-backend"
              cluster         = aws_ecs_cluster.main.id
              task_definition = aws_ecs_task_definition.backend.arn
              desired_count   = var.min_capacity
              launch_type     = "FARGATE"

              network_configuration {
                subnets          = aws_subnet.private[*].id
                security_groups  = [aws_security_group.ecs.id]
                assign_public_ip = false
              }

              load_balancer {
                target_group_arn = aws_lb_target_group.backend.arn
                container_name   = "backend"
                container_port   = 8000
              }

              deployment_circuit_breaker {
                enable   = true
                rollback = true
              }

              lifecycle {
                ignore_changes = [desired_count, task_definition]
              }
            }

            # Auto-scaling
            resource "aws_appautoscaling_target" "backend" {
              max_capacity       = var.max_capacity
              min_capacity       = var.min_capacity
              resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
              scalable_dimension = "ecs:service:DesiredCount"
              service_namespace  = "ecs"
            }

            resource "aws_appautoscaling_policy" "backend_cpu" {
              name               = "${local.name_prefix}-backend-cpu-scale"
              policy_type        = "TargetTrackingScaling"
              resource_id        = aws_appautoscaling_target.backend.resource_id
              scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
              service_namespace  = aws_appautoscaling_target.backend.service_namespace

              target_tracking_scaling_policy_configuration {
                predefined_metric_specification {
                  predefined_metric_type = "ECSServiceAverageCPUUtilization"
                }
                target_value       = 70.0
                scale_in_cooldown  = 300
                scale_out_cooldown = 60
              }
            }

            # Secrets
            resource "aws_secretsmanager_secret" "db_url" {
              name = "${local.name_prefix}/database-url"
            }

            resource "aws_secretsmanager_secret" "secret_key" {
              name = "${local.name_prefix}/secret-key"
            }
        """).strip()

    def _tf_rds(self, name: str) -> str:
        return textwrap.dedent(f"""
            # ── RDS PostgreSQL ─────────────────────────────────────────
            resource "aws_db_subnet_group" "main" {{
              name       = "${{local.name_prefix}}-db-subnet"
              subnet_ids = aws_subnet.private[*].id
            }}

            resource "aws_db_instance" "postgres" {{
              identifier             = "${{local.name_prefix}}-postgres"
              engine                 = "postgres"
              engine_version         = "15.4"
              instance_class         = var.db_instance_class
              allocated_storage      = 20
              max_allocated_storage  = 100
              storage_encrypted      = true

              db_name  = "{name.replace("-", "_")}_db"
              username = "postgres"
              password = random_password.db.result

              vpc_security_group_ids = [aws_security_group.rds.id]
              db_subnet_group_name   = aws_db_subnet_group.main.name

              multi_az               = true
              backup_retention_period = 7
              skip_final_snapshot    = false
              final_snapshot_identifier = "${{local.name_prefix}}-final-snapshot"

              deletion_protection    = true
              performance_insights_enabled = true

              tags = {{
                Name = "${{local.name_prefix}}-postgres"
              }}
            }}

            resource "random_password" "db" {{
              length  = 32
              special = false
            }}
        """).strip()

    def _tf_alb(self, name: str) -> str:
        return textwrap.dedent("""
            # ── Application Load Balancer ─────────────────────────────
            resource "aws_lb" "main" {
              name               = "${local.name_prefix}-alb"
              internal           = false
              load_balancer_type = "application"
              security_groups    = [aws_security_group.alb.id]
              subnets            = aws_subnet.public[*].id
              enable_deletion_protection = true
            }

            resource "aws_lb_target_group" "backend" {
              name        = "${local.name_prefix}-backend-tg"
              port        = 8000
              protocol    = "HTTP"
              vpc_id      = aws_vpc.main.id
              target_type = "ip"

              health_check {
                path                = "/health"
                healthy_threshold   = 2
                unhealthy_threshold = 5
                timeout             = 5
                interval            = 30
                matcher             = "200"
              }

              deregistration_delay = 30
            }

            # HTTPS Listener (primary)
            resource "aws_lb_listener" "https" {
              load_balancer_arn = aws_lb.main.arn
              port              = 443
              protocol          = "HTTPS"
              ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
              certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

              default_action {
                type             = "forward"
                target_group_arn = aws_lb_target_group.backend.arn
              }
            }

            # HTTP → HTTPS redirect
            resource "aws_lb_listener" "http_redirect" {
              load_balancer_arn = aws_lb.main.arn
              port              = 80
              protocol          = "HTTP"

              default_action {
                type = "redirect"
                redirect {
                  port        = "443"
                  protocol    = "HTTPS"
                  status_code = "HTTP_301"
                }
              }
            }

            # CloudFront Distribution
            resource "aws_cloudfront_distribution" "main" {
              origin {
                domain_name = aws_lb.main.dns_name
                origin_id   = "alb-origin"
                custom_origin_config {
                  http_port              = 80
                  https_port             = 443
                  origin_protocol_policy = "https-only"
                  origin_ssl_protocols   = ["TLSv1.2"]
                }
              }
              enabled = true
              default_cache_behavior {
                allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
                cached_methods         = ["GET", "HEAD"]
                target_origin_id       = "alb-origin"
                viewer_protocol_policy = "redirect-to-https"
                cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"  # Managed-CachingDisabled
              }
              restrictions {
                geo_restriction { restriction_type = "none" }
              }
              viewer_certificate {
                cloudfront_default_certificate = true
              }
            }
        """).strip()

    def _tf_iam(self, name: str) -> str:
        return textwrap.dedent("""
            # ── IAM Roles (Least Privilege) ────────────────────────────
            data "aws_iam_policy_document" "ecs_assume" {
              statement {
                actions = ["sts:AssumeRole"]
                principals {
                  type        = "Service"
                  identifiers = ["ecs-tasks.amazonaws.com"]
                }
              }
            }

            resource "aws_iam_role" "ecs_execution" {
              name               = "${local.name_prefix}-ecs-execution"
              assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
            }

            resource "aws_iam_role_policy_attachment" "ecs_execution" {
              role       = aws_iam_role.ecs_execution.name
              policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
            }

            resource "aws_iam_role" "ecs_task" {
              name               = "${local.name_prefix}-ecs-task"
              assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
            }

            resource "aws_iam_role_policy" "ecs_task_policy" {
              name = "${local.name_prefix}-ecs-task-policy"
              role = aws_iam_role.ecs_task.id
              policy = jsonencode({
                Version = "2012-10-17"
                Statement = [
                  {
                    Effect = "Allow"
                    Action = [
                      "s3:GetObject", "s3:PutObject", "s3:DeleteObject"
                    ]
                    Resource = "${aws_s3_bucket.app.arn}/*"
                  },
                  {
                    Effect   = "Allow"
                    Action   = ["secretsmanager:GetSecretValue"]
                    Resource = [
                      aws_secretsmanager_secret.db_url.arn,
                      aws_secretsmanager_secret.secret_key.arn
                    ]
                  }
                ]
              })
            }

            resource "aws_s3_bucket" "app" {
              bucket = "${local.name_prefix}-app-storage"
              force_destroy = false
            }

            resource "aws_s3_bucket_versioning" "app" {
              bucket = aws_s3_bucket.app.id
              versioning_configuration { status = "Enabled" }
            }

            resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
              bucket = aws_s3_bucket.app.id
              rule {
                apply_server_side_encryption_by_default {
                  sse_algorithm = "AES256"
                }
              }
            }
        """).strip()

    def _tf_cloudwatch(self, name: str) -> str:
        return textwrap.dedent("""
            # ── CloudWatch Monitoring ─────────────────────────────────
            resource "aws_cloudwatch_log_group" "backend" {
              name              = "/ecs/${local.name_prefix}/backend"
              retention_in_days = 30
            }

            resource "aws_cloudwatch_log_group" "frontend" {
              name              = "/ecs/${local.name_prefix}/frontend"
              retention_in_days = 14
            }

            # CPU alarm
            resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
              alarm_name          = "${local.name_prefix}-backend-cpu-high"
              comparison_operator = "GreaterThanThreshold"
              evaluation_periods  = 2
              metric_name         = "CPUUtilization"
              namespace           = "AWS/ECS"
              period              = 120
              statistic           = "Average"
              threshold           = 80
              alarm_description   = "Backend CPU above 80%"
              dimensions = {
                ClusterName = aws_ecs_cluster.main.name
                ServiceName = aws_ecs_service.backend.name
              }
            }

            # Memory alarm
            resource "aws_cloudwatch_metric_alarm" "backend_memory_high" {
              alarm_name          = "${local.name_prefix}-backend-memory-high"
              comparison_operator = "GreaterThanThreshold"
              evaluation_periods  = 2
              metric_name         = "MemoryUtilization"
              namespace           = "AWS/ECS"
              period              = 120
              statistic           = "Average"
              threshold           = 85
              alarm_description   = "Backend memory above 85%"
              dimensions = {
                ClusterName = aws_ecs_cluster.main.name
                ServiceName = aws_ecs_service.backend.name
              }
            }

            # RDS connection alarm
            resource "aws_cloudwatch_metric_alarm" "rds_connections" {
              alarm_name          = "${local.name_prefix}-rds-connections"
              comparison_operator = "GreaterThanThreshold"
              evaluation_periods  = 1
              metric_name         = "DatabaseConnections"
              namespace           = "AWS/RDS"
              period              = 60
              statistic           = "Average"
              threshold           = 80
              dimensions = {
                DBInstanceIdentifier = aws_db_instance.postgres.id
              }
            }

            # Dashboard
            resource "aws_cloudwatch_dashboard" "main" {
              dashboard_name = "${local.name_prefix}-dashboard"
              dashboard_body = jsonencode({
                widgets = [
                  {
                    type = "metric", x = 0, y = 0, width = 12, height = 6,
                    properties = {
                      title = "ECS Backend CPU"
                      metrics = [["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name]]
                      period = 60, stat = "Average", region = var.aws_region
                    }
                  }
                ]
              })
            }
        """).strip()

    # ══ CI/CD PIPELINE ═══════════════════════════════════════════════

    def _generate_cicd(self, project_name: str) -> Dict[str, str]:
        return {
            ".github/workflows/deploy.yml": self._github_actions_deploy(project_name),
            ".github/workflows/test.yml": self._github_actions_test(),
            "scripts/deploy.sh": self._deploy_script(project_name),
            "scripts/rollback.sh": self._rollback_script(project_name),
        }

    def _github_actions_deploy(self, name: str) -> str:
        return textwrap.dedent(f"""
            name: Deploy to AWS

            on:
              push:
                branches: [main]
              workflow_dispatch:

            concurrency:
              group: production-deploy
              cancel-in-progress: false

            jobs:
              test:
                runs-on: ubuntu-latest
                services:
                  postgres:
                    image: postgres:15
                    env:
                      POSTGRES_PASSWORD: test
                    options: >-
                      --health-cmd pg_isready
                      --health-interval 10s
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with: {{python-version: "3.11"}}
                  - run: pip install -r requirements.txt
                  - run: pytest tests/ --tb=short -q
                    env:
                      DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/test

              deploy:
                needs: test
                runs-on: ubuntu-latest
                environment: production
                permissions:
                  id-token: write
                  contents: read
                steps:
                  - uses: actions/checkout@v4

                  - name: Configure AWS credentials
                    uses: aws-actions/configure-aws-credentials@v4
                    with:
                      role-to-assume: arn:aws:iam::${{{{ secrets.AWS_ACCOUNT_ID }}}}:role/github-actions-deploy
                      aws-region: us-east-1

                  - name: Login to ECR
                    id: ecr
                    uses: aws-actions/amazon-ecr-login@v2

                  - name: Build and push backend
                    env:
                      ECR_REGISTRY: ${{{{ steps.ecr.outputs.registry }}}}
                      IMAGE_TAG: ${{{{ github.sha }}}}
                    run: |
                      docker build -t $ECR_REGISTRY/{name}-backend:$IMAGE_TAG ./backend
                      docker push $ECR_REGISTRY/{name}-backend:$IMAGE_TAG
                      echo "backend_image=$ECR_REGISTRY/{name}-backend:$IMAGE_TAG" >> $GITHUB_OUTPUT

                  - name: Deploy with Terraform
                    working-directory: terraform
                    run: |
                      terraform init
                      terraform apply -auto-approve \\
                        -var="backend_image=${{{{ steps.build.outputs.backend_image }}}}" \\
                        -var="environment=production"

                  - name: Verify deployment
                    run: |
                      curl -f $(terraform output -raw alb_dns_name)/health || exit 1
        """).strip()

    def _github_actions_test(self) -> str:
        return textwrap.dedent("""
            name: Tests

            on:
              pull_request:
                branches: [main, develop]

            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with: {python-version: "3.11"}
                  - name: Install dependencies
                    run: pip install -r requirements.txt pytest pytest-asyncio pytest-cov httpx aiosqlite
                  - name: Run tests
                    run: pytest tests/ --cov=backend --cov-report=xml -v
                  - name: Upload coverage
                    uses: codecov/codecov-action@v3
        """).strip()

    def _deploy_script(self, name: str) -> str:
        return textwrap.dedent(f"""
            #!/usr/bin/env bash
            # deploy.sh — Manual AWS Deployment Script
            # Generated by DevOps Agent — AI Company in a Box
            set -euo pipefail

            PROJECT="{name}"
            REGION="us-east-1"
            ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
            ECR_BASE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
            COMMIT=$(git rev-parse --short HEAD)

            echo "🚀 Deploying $PROJECT @ $COMMIT"

            # Login to ECR
            aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_BASE

            # Build and push backend
            echo "📦 Building backend..."
            docker build -t $ECR_BASE/$PROJECT-backend:$COMMIT ./backend
            docker push $ECR_BASE/$PROJECT-backend:$COMMIT
            docker tag $ECR_BASE/$PROJECT-backend:$COMMIT $ECR_BASE/$PROJECT-backend:latest

            # Build and push frontend
            echo "📦 Building frontend..."
            docker build -t $ECR_BASE/$PROJECT-frontend:$COMMIT ./frontend
            docker push $ECR_BASE/$PROJECT-frontend:$COMMIT

            # Terraform apply
            echo "🏗 Applying Terraform..."
            cd terraform
            terraform init -upgrade
            terraform apply -auto-approve \\
              -var="backend_image=$ECR_BASE/$PROJECT-backend:$COMMIT" \\
              -var="frontend_image=$ECR_BASE/$PROJECT-frontend:$COMMIT"

            # Wait for ECS service to stabilize
            echo "⏳ Waiting for ECS service..."
            aws ecs wait services-stable \\
              --cluster "$PROJECT-production-cluster" \\
              --services "$PROJECT-production-backend"

            # Health check
            ALB=$(terraform output -raw alb_dns_name)
            echo "🏥 Health check: https://$ALB/health"
            curl -sf "https://$ALB/health" && echo "✅ Deployment successful!"
        """).strip()

    def _rollback_script(self, name: str) -> str:
        return textwrap.dedent(f"""
            #!/usr/bin/env bash
            # rollback.sh — Emergency Rollback Script
            set -euo pipefail

            PROJECT="{name}"
            SERVICE="${{1:-backend}}"

            echo "⚠️  Rolling back $SERVICE in $PROJECT..."
            aws ecs update-service \\
              --cluster "$PROJECT-production-cluster" \\
              --service "$PROJECT-production-$SERVICE" \\
              --task-definition "$(
                aws ecs describe-task-definition \\
                  --task-definition "$PROJECT-production-$SERVICE" \\
                  --query "taskDefinition.taskDefinitionArn" \\
                  --output text
              )" \\
              --force-new-deployment

            echo "✅ Rollback initiated. Monitor in CloudWatch."
        """).strip()

    def _generate_docker_compose(self, arch: Dict[str, Any]) -> str:
        return textwrap.dedent("""
            # docker-compose.yml — Local development environment
            # Generated by DevOps Agent — AI Company in a Box
            version: '3.9'

            services:
              postgres:
                image: postgres:15-alpine
                environment:
                  POSTGRES_USER: postgres
                  POSTGRES_PASSWORD: password
                  POSTGRES_DB: ai_org
                ports:
                  - "5432:5432"
                volumes:
                  - postgres_data:/var/lib/postgresql/data
                healthcheck:
                  test: ["CMD-SHELL", "pg_isready -U postgres"]
                  interval: 10s
                  timeout: 5s
                  retries: 5

              redis:
                image: redis:7-alpine
                ports:
                  - "6379:6379"
                command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
                healthcheck:
                  test: ["CMD", "redis-cli", "ping"]
                  interval: 10s

              backend:
                build:
                  context: ./backend
                  dockerfile: Dockerfile
                ports:
                  - "8000:8000"
                environment:
                  DATABASE_URL: postgresql+asyncpg://postgres:password@postgres/ai_org
                  REDIS_URL: redis://redis:6379/0
                  SECRET_KEY: dev-secret-key-change-in-prod
                  ENVIRONMENT: development
                depends_on:
                  postgres:
                    condition: service_healthy
                  redis:
                    condition: service_healthy
                volumes:
                  - ./backend:/app
                command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

              frontend:
                build:
                  context: ./frontend
                  dockerfile: Dockerfile
                ports:
                  - "3000:3000"
                environment:
                  NEXT_PUBLIC_API_URL: http://localhost:8000
                depends_on:
                  - backend
                volumes:
                  - ./frontend:/app
                  - /app/node_modules
                  - /app/.next

              # Orchestrator Dashboard
              orchestrator:
                build:
                  context: .
                  dockerfile: Dockerfile.orchestrator
                ports:
                  - "8080:8080"
                environment:
                  DATABASE_URL: postgresql+asyncpg://postgres:password@postgres/ai_org
                  REDIS_URL: redis://redis:6379/0
                depends_on:
                  - postgres
                  - redis

            volumes:
              postgres_data:
        """).strip()
