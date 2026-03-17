"""
CTO Agent - Chief Technology Officer
Designs the complete technical architecture based on the CEO's business plan.
Outputs: tech stack, database schema, API contracts, cost estimates, infra spec.
"""

import json
from typing import Any

import structlog

from .base_agent import BaseAgent

logger = structlog.get_logger(__name__)

# AWS pricing estimates (simplified, USD/month)
AWS_PRICING = {
    "ECS_Fargate_1vCPU_2GB": 14.40,
    "RDS_t3_micro_PostgreSQL": 15.84,
    "RDS_t3_small_PostgreSQL": 31.68,
    "ALB": 18.00,
    "CloudFront_10GB": 0.85,
    "S3_10GB": 0.23,
    "ElastiCache_t3_micro": 11.52,
    "OpenSearch_t3_small": 35.04,
    "Cognito_1000_MAU": 0.0055,
    "Route53": 0.50,
    "Certificate": 0.0,
}


class CTOAgent(BaseAgent):
    """
    CTO Agent designs the full technical architecture.
    Cost-aware: selects the cheapest viable architecture within budget.
    """

    ROLE = "CTO"

    @property
    def system_prompt(self) -> str:
        return """You are the CTO of an autonomous AI software company.
You design production-grade, cloud-native architectures.

Your decisions are:
- Cost-conscious (always check against budget)
- Security-first (least privilege, zero trust)
- Scalable but not over-engineered
- AWS-native (prefer managed services)
- Developer-friendly (clear contracts, documented APIs)

You always produce valid JSON output with complete technical specifications.
You explain your architectural decisions with rationale.
"""

    async def run(
        self,
        business_plan: dict[str, Any] | None = None,
        budget_usd: float = 200.0,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Design complete system architecture from business plan."""
        logger.info("CTO Agent: Designing architecture")
        if context:
            await context.emit_event(
                type(
                    "E",
                    (),
                    {
                        "to_dict": lambda s: {
                            "type": "thinking",
                            "agent": self.ROLE,
                            "message": "Evaluating AWS services and cost constraints for the given MVP...",
                            "level": "info",
                        }
                    },
                )()
            )
        raw_features = business_plan.get("mvp_features", []) if business_plan else []
        features = []
        for f in raw_features:
            if isinstance(f, dict):
                features.append(f.get("name", str(f)))
            else:
                features.append(str(f))

        prompt = f"""
Design a production AWS architecture for this project.

Business Vision: {business_plan.get('vision', '')}
MVP Features: {json.dumps(features)}
Budget: ${budget_usd}/month
Target Users Year 1: {business_plan.get('estimated_users_year1', 1000)}

Return a JSON architecture specification:
{{
  "frontend": {{"framework": "Next.js 14 (Web) or Expo/React Native (Mobile)", "hosting": "ECS/Amplify", "cdn": "CloudFront"}},
  "backend": {{"framework": "FastAPI", "language": "Python 3.11", "runtime": "ECS Fargate"}},
  "database": {{"type": "PostgreSQL 15", "hosting": "RDS", "instance": "db.t3.micro"}},
  "cache": {{"type": "Redis 7", "hosting": "ElastiCache", "instance": "cache.t3.micro"}},
  "auth": {{"service": "AWS Cognito", "type": "JWT + OAuth2"}},
  "storage": {{"service": "S3", "purpose": "file uploads, artifacts"}},
  "cdn": {{"service": "CloudFront", "regions": ["us-east-1"]}},
  "monitoring": {{"services": ["CloudWatch", "X-Ray", "OpenTelemetry"]}},
  "ci_cd": {{"pipeline": "GitHub Actions + AWS CodeDeploy"}},
  "database_schema": [
    {{
      "table": "users",
      "columns": [
        {{"name": "id", "type": "UUID", "primary_key": true}},
        {{"name": "email", "type": "VARCHAR(255)", "unique": true}},
        {{"name": "created_at", "type": "TIMESTAMP"}}
      ]
    }}
  ],
  "api_contracts": [
    {{"method": "POST", "path": "/api/auth/login", "description": "User login", "auth": false}},
    {{"method": "POST", "path": "/api/auth/register", "description": "Register user", "auth": false}},
    {{"method": "GET", "path": "/api/items", "description": "List items", "auth": true}}
  ],
  "environment_variables": ["DATABASE_URL", "REDIS_URL", "JWT_SECRET", "AWS_REGION"],
  "security": {{
    "cors": "Restricted to frontend domain",
    "rate_limiting": "100 req/min per IP",
    "waf": "AWS WAF Basic rules",
    "encryption": "AES-256 at rest, TLS 1.3 in transit"
  }},
  "estimated_monthly_cost_usd": 95,
  "cost_breakdown": {{}},
  "scaling_policy": "Auto-scale ECS at 70% CPU",
  "disaster_recovery": "Multi-AZ RDS, S3 versioning"
}}
"""

        raw = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format="json_object",
        )

        try:
            arch = json.loads(raw)
        except json.JSONDecodeError:
            arch = self._default_architecture(budget_usd)

        # Validate and adjust for budget
        arch = self._validate_cost(arch, budget_usd)

        if context:
            await context.emit_event(
                type(
                    "E",
                    (),
                    {
                        "to_dict": lambda s: {
                            "type": "thinking",
                            "agent": self.ROLE,
                            "message": f"Drafted Architecture:\nFrontend: {arch.get('frontend', {}).get('framework')}\nBackend: {arch.get('backend', {}).get('framework')}\nDatabase: {arch.get('database', {}).get('type')}",
                            "level": "info",
                        }
                    },
                )()
            )

        # Self-critique the architecture
        arch = await self.self_critique(arch)

        if context:
            context.decision_log.log(
                agent_role=self.ROLE,
                decision_type="architecture",
                description="System architecture designed",
                rationale=f"Optimized for ${budget_usd}/month budget with {len(features)} features",
                input_context={"features": features, "budget": budget_usd},
                output={k: v for k, v in arch.items() if k != "database_schema"},
                confidence=0.92,
                tags=["architecture", "aws", "cost"],
            )
            context.artifacts.save(
                artifact_type="document",
                name="system_architecture",
                content=arch,
                agent_role=self.ROLE,
                tags=["architecture"],
                file_extension=".json",
            )

        logger.info(
            "CTO: Architecture designed",
            estimated_cost=arch.get("estimated_monthly_cost_usd"),
            budget=budget_usd,
        )
        return arch

    def _validate_cost(self, arch: dict[str, Any], budget: float) -> dict[str, Any]:
        """Downgrade components if estimated cost exceeds budget."""
        est = arch.get("estimated_monthly_cost_usd", 100)
        if est > budget:
            logger.warning(
                "Architecture cost exceeds budget, optimizing", cost=est, budget=budget
            )
            # Downgrade database instance
            if "database" in arch:
                arch["database"]["instance"] = "db.t3.micro"
            # Remove optional services
            if "cache" in arch and est - 11 < budget:
                arch["cache"] = None
            arch["estimated_monthly_cost_usd"] = min(est, budget * 0.85)
            arch["_cost_optimized"] = True
        return arch

    def _default_architecture(self, budget: float) -> dict[str, Any]:
        return {
            "frontend": {
                "framework": "Next.js 14",
                "hosting": "ECS Fargate",
                "cdn": "CloudFront",
            },
            "backend": {
                "framework": "FastAPI",
                "language": "Python 3.11",
                "runtime": "ECS Fargate",
            },
            "database": {
                "type": "PostgreSQL 15",
                "hosting": "RDS",
                "instance": "db.t3.micro",
            },
            "cache": {
                "type": "Redis 7",
                "hosting": "ElastiCache",
                "instance": "cache.t3.micro",
            },
            "auth": {"service": "AWS Cognito", "type": "JWT + OAuth2"},
            "storage": {"service": "S3"},
            "cdn": {"service": "CloudFront"},
            "monitoring": {"services": ["CloudWatch", "X-Ray"]},
            "ci_cd": {"pipeline": "GitHub Actions"},
            "database_schema": [
                {
                    "table": "users",
                    "columns": [
                        {"name": "id", "type": "UUID", "primary_key": True},
                        {"name": "email", "type": "VARCHAR(255)", "unique": True},
                        {"name": "hashed_password", "type": "TEXT"},
                        {"name": "is_active", "type": "BOOLEAN", "default": True},
                        {"name": "created_at", "type": "TIMESTAMP WITH TIME ZONE"},
                        {"name": "updated_at", "type": "TIMESTAMP WITH TIME ZONE"},
                    ],
                },
                {
                    "table": "items",
                    "columns": [
                        {"name": "id", "type": "UUID", "primary_key": True},
                        {"name": "user_id", "type": "UUID", "foreign_key": "users.id"},
                        {"name": "title", "type": "VARCHAR(255)"},
                        {"name": "description", "type": "TEXT"},
                        {"name": "status", "type": "VARCHAR(50)"},
                        {"name": "created_at", "type": "TIMESTAMP WITH TIME ZONE"},
                        {"name": "updated_at", "type": "TIMESTAMP WITH TIME ZONE"},
                    ],
                },
            ],
            "api_contracts": [
                {"method": "POST", "path": "/api/auth/login", "auth": False},
                {"method": "POST", "path": "/api/auth/register", "auth": False},
                {"method": "GET", "path": "/api/items", "auth": True},
                {"method": "POST", "path": "/api/items", "auth": True},
                {"method": "PUT", "path": "/api/items/{id}", "auth": True},
                {"method": "DELETE", "path": "/api/items/{id}", "auth": True},
            ],
            "security": {
                "cors": "Restricted to frontend domain",
                "rate_limiting": "100 req/min per IP",
                "encryption": "AES-256 at rest, TLS 1.3 in transit",
            },
            "estimated_monthly_cost_usd": min(95, budget * 0.85),
            "scaling_policy": "Auto-scale ECS at 70% CPU",
            "disaster_recovery": "Multi-AZ RDS, S3 versioning",
        }
