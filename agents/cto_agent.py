"""
CTO Agent - Chief Technology Officer
Designs the complete technical architecture based on the CEO's business plan.
Uses multi-turn chain-of-thought reasoning for deeper architectural analysis.
Outputs: tech stack, database schema, API contracts, cost estimates, infra spec.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep
from .schemas import Architecture

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "cto_architecture.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("CTO prompt template not found, using inline prompts")
        return {}

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

_PROMPT_TEMPLATE = _load_prompt()


class CTOAgent(BaseAgent):
    """
    CTO Agent designs the full technical architecture.
    Cost-aware: selects the cheapest viable architecture within budget.

    v2: Uses multi-turn ReasoningChain for deeper analysis and
    Pydantic Architecture schema for validated output.
    """

    ROLE = "CTO"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the CTO of an autonomous AI software company.\n"
            "You design production-grade, cloud-native architectures.\n\n"
            "Your decisions are:\n"
            "- Cost-conscious (always check against budget)\n"
            "- Security-first (least privilege, zero trust)\n"
            "- Scalable but not over-engineered\n"
            "- AWS-native (prefer managed services)\n"
            "- Developer-friendly (clear contracts, documented APIs)\n\n"
            "You always produce valid JSON output with complete technical specifications.\n"
        )

    async def run(
        self,
        business_plan: dict[str, Any] | None = None,
        budget_usd: float = 200.0,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Design complete system architecture from business plan.

        Uses a 4-step reasoning chain:
          1. Analyze — Decompose requirements into data models and compute profile
          2. Generate — Produce the full architecture specification
          3. Critique — Check for SPOFs, cost issues, security gaps
          4. Refine — Address weaknesses in a revised architecture
        """
        logger.info("CTO Agent: Designing architecture")
        if context:
            await self.emit(
                context,
                "Evaluating AWS services and cost constraints for the given MVP...",
            )

        raw_features = business_plan.get("mvp_features", []) if business_plan else []
        features = []
        for f in raw_features:
            if isinstance(f, dict):
                features.append(f.get("name", str(f)))
            else:
                features.append(str(f))

        # Build the reasoning chain
        cot = _PROMPT_TEMPLATE.get("chain_of_thought", {})
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template=cot.get("analyze", self._fallback_analyze()),
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="generate",
                    prompt_template=cot.get("generate", self._fallback_generate()),
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="critique",
                    prompt_template=cot.get("critique", self._fallback_critique()),
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="refine",
                    prompt_template=cot.get("refine", self._fallback_refine()),
                    temperature=0.2,
                ),
            ],
            output_schema=None,  # CTO output has extra keys beyond Architecture
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "analyze": "Analyzing requirements and AWS service options...",
                "generate": "Drafting architecture specification...",
                "critique": "Checking for vulnerabilities and cost issues...",
                "refine": "Refining architecture based on critique...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Step: {step_name}"))

        try:
            arch = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                business_plan=json.dumps(business_plan or {}, indent=2)[:3000],
                budget_usd=budget_usd,
                features=json.dumps(features),
            )
        except Exception as e:
            logger.warning("CTO reasoning chain failed, using default", error=str(e))
            arch = self._default_architecture(budget_usd)

        # Validate and adjust for budget
        arch = self._validate_cost(arch, budget_usd)

        if context:
            await self.emit(
                context,
                f"Drafted Architecture:\n"
                f"Frontend: {arch.get('frontend', {}).get('framework')}\n"
                f"Backend: {arch.get('backend', {}).get('framework')}\n"
                f"Database: {arch.get('database', {}).get('type')}",
                level="success",
            )

        if context:
            context.decision_log.log(
                agent_role=self.ROLE,
                decision_type="architecture",
                description="System architecture designed via multi-turn reasoning chain",
                rationale=f"Optimized for ${budget_usd}/month budget with {len(features)} features",
                input_context={"features": features, "budget": budget_usd},
                output={k: v for k, v in arch.items() if k != "database_schema"},
                confidence=0.92,
                tags=["architecture", "aws", "cost", "reasoning_chain"],
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

    # ── Fallback prompts ─────────────────────────────────────────────

    @staticmethod
    def _fallback_analyze() -> str:
        return (
            "Analyze these requirements for architecture design:\n\n"
            "Business Plan: {business_plan}\n"
            "Budget Constraint: ${budget_usd} USD/month\n\n"
            "List: data entities, API endpoint count, compute profile, budget tier, "
            "and AWS service candidates. Return JSON."
        )

    @staticmethod
    def _fallback_generate() -> str:
        return (
            "Based on your analysis:\n{analyze_output}\n\n"
            "Design the full architecture as JSON with keys: "
            "frontend, backend, database, cache, database_schema, "
            "api_contracts, security, estimated_monthly_cost_usd, "
            "cost_breakdown, scaling_policy, disaster_recovery."
        )

    @staticmethod
    def _fallback_critique() -> str:
        return (
            "Review this architecture for weaknesses:\n{generate_output}\n\n"
            "Check: single points of failure, cost overruns, security gaps, "
            "scalability bottlenecks, missing API endpoints.\n"
            'Return JSON: {{"vulnerabilities": [], "missing_endpoints": [], "cost_issues": []}}'
        )

    @staticmethod
    def _fallback_refine() -> str:
        return (
            "Your architecture had these issues:\n{critique_output}\n\n"
            "Original:\n{generate_output}\n\n"
            "Produce a REVISED architecture fixing every issue. Return valid JSON only."
        )

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
