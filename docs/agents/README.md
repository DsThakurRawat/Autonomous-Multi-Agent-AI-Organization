# Agent Subsystem — Technical Reference

> **Module**: `agents/`
> **Language**: Python 3.12
> **Key Dependency**: `structlog`, `pydantic`, LLM provider SDKs

---

## 1. Overview

The Agent Subsystem is the cognitive core of Proximus. It defines a hierarchy of specialist AI workers — each responsible for a distinct phase of the software development lifecycle. All agents inherit from a common `BaseAgent` class that provides unified LLM access, security tooling, and cost tracking.

### Design Principles
1.  **Single Responsibility**: Each agent owns exactly one domain (strategy, architecture, code, etc.).
2.  **Provider Agnosticism**: Any agent can be backed by Bedrock, OpenAI, Anthropic, or Google Gemini without code changes.
3.  **Self-Critique Loop**: Every agent evaluates its own output before returning it to the orchestrator.
4.  **Auditability**: All LLM calls, tool invocations, and decisions are logged to an append-only `DecisionLog`.

---

## 2. Class Hierarchy

```
BaseAgent (Abstract)
├── CEOAgent          — Strategic planning & PRD generation
├── CTOAgent          — Technical architecture & cost-aware design
├── BackendAgent      — FastAPI code generation & AST validation
├── FrontendAgent     — Next.js/React UI generation
├── QAAgent           — Test writing, security scanning, contract validation
├── DevOpsAgent       — Dockerfile, Terraform, CI/CD pipeline generation
└── FinanceAgent      — Real-time cost governance & optimization
```

---

## 3. `BaseAgent` — The Foundation

**Source**: [`agents/base_agent.py`](../agents/base_agent.py)

`BaseAgent` is the abstract base class that every specialist inherits. It provides:

### 3.1. Unified LLM Interface (`call_llm`)

A single method to call any supported LLM provider. The provider is selected at agent instantiation time via the `ModelRegistry`.

```python
raw_response = await self.call_llm(
    messages=[{"role": "user", "content": prompt}],
    temperature=0.4,
    response_format="json_object",
)
```

**Supported Providers**:

| Provider | SDK | Auth Mechanism |
| :--- | :--- | :--- |
| Amazon Bedrock | `boto3` (Converse API) | IAM Role / `AWS_ACCESS_KEY_ID` |
| Google Gemini | `google-genai` | `GOOGLE_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |

**Key Features**:
-   **Semantic Caching**: Identical prompts within a session return cached responses, saving tokens.
-   **Per-Call Cost Tracking**: Token usage (input + output) is recorded to the `CostLedger` after every call.
-   **Automatic Retries**: Transient API failures (rate limits, 5xx) trigger exponential backoff.

### 3.2. Security Layer

Every agent has built-in security capabilities:

-   **PII Scrubbing**: Before logging, all outputs are passed through the Rust `security-check` binary's `scrub` task to redact emails, API keys, and IP addresses.
-   **AST Validation**: Before writing Python code to disk, the `validate_python` task checks for dangerous imports (`os`, `subprocess`, `shutil`) and unsafe calls (`eval`, `exec`, `compile`).

### 3.3. Self-Critique (`self_critique`)

After generating output, every agent calls `self_critique()` to evaluate its own work. This method re-invokes the LLM with a meta-prompt asking it to score the output on completeness, correctness, and adherence to the original requirements.

### 3.4. System Prompt Construction

The `_build_full_prompt()` method combines:
1.  The agent's domain-specific `system_prompt` (e.g., "You are the CTO...").
2.  Global organization instructions (local mode directives, budget constraints).
3.  Tool-use instructions (how to call `file_edit`, `git`, `linter`).

---

## 4. Specialist Agents — Detailed Reference

### 4.1. `CEOAgent` — Chief Executive Officer

**Source**: [`agents/ceo_agent.py`](../agents/ceo_agent.py) · **Role Enum**: `AgentRole.CEO`

**Responsibility**: Converts a raw business idea into a structured Product Requirements Document (PRD).

**Input**: A natural language business idea string and a budget constraint.

**Output Schema** (JSON):
```json
{
  "vision": "One-sentence product description",
  "target_users": "Who benefits",
  "problem_statement": "What pain it solves",
  "mvp_features": [
    {"name": "Feature", "priority": "P0/P1/P2", "description": "..."}
  ],
  "milestones": [
    {"phase": "Phase name", "duration_days": 1, "deliverables": ["..."]}
  ],
  "risk_assessment": [
    {"risk": "Risk", "impact": "High/Medium/Low", "mitigation": "..."}
  ],
  "success_metrics": ["Metric 1", "Metric 2"],
  "revenue_model": "How it makes money",
  "estimated_users_year1": 1000,
  "go_to_market": "User acquisition strategy"
}
```

**Fallback Behavior**: If JSON parsing fails, `_extract_plan_fallback()` generates a safe, generic MVP template (Auth, Dashboard, CRUD, Notifications) to keep the pipeline moving.

---

### 4.2. `CTOAgent` — Chief Technology Officer

**Source**: [`agents/cto_agent.py`](../agents/cto_agent.py) · **Role Enum**: `AgentRole.CTO`

**Responsibility**: Designs the full AWS-native technical architecture from the CEO's business plan.

**Input**: The CEO's `business_plan` dict and the budget constraint.

**Output**: A comprehensive architecture specification including:
-   Frontend/Backend/Database/Cache technology selections.
-   Full `database_schema` with table definitions and column types.
-   `api_contracts` listing every REST endpoint.
-   `security` configuration (CORS, rate limiting, WAF, encryption).
-   `estimated_monthly_cost_usd` with per-service breakdown.
-   Disaster recovery and scaling policies.

**Cost Awareness**: The `_validate_cost()` method post-processes the LLM output. If the estimated cost exceeds the budget, it automatically downgrades instances (e.g., `db.t3.micro`) and removes optional services like the cache layer.

**Built-in Pricing Table**: `AWS_PRICING` dict contains simplified monthly cost estimates for common services (ECS Fargate, RDS, ALB, S3, etc.), used for validation.

---

### 4.3. `BackendAgent` — Backend Software Engineer

**Source**: [`agents/backend_agent.py`](../agents/backend_agent.py) · **Role Enum**: `AgentRole.ENGINEER_BACKEND`

**Responsibility**: Generates production-quality FastAPI backend code, including:
-   Pydantic models and SQLAlchemy ORM.
-   RESTful API endpoints with JWT authentication.
-   Database migration scripts.
-   `requirements.txt` and configuration files.

**Key Behavior**:
-   **Surgical File Editing**: Uses `LocalFileEditTool` for precise modifications rather than full-file rewrites.
-   **AST Validation**: All generated Python code is validated via the Rust security binary before being written to disk.
-   **Template Fallback**: If the LLM produces invalid code, `_safe_template_backend()` generates a working, minimal FastAPI application.

---

### 4.4. `FrontendAgent` — Frontend Software Engineer

**Source**: [`agents/frontend_agent.py`](../agents/frontend_agent.py) · **Role Enum**: `AgentRole.ENGINEER_FRONTEND`

**Responsibility**: Generates Next.js frontend applications with:
-   React components with Tailwind CSS.
-   API integration layer connected to the backend.
-   Authentication pages (Login, Register).
-   Responsive layouts and dashboard views.

---

### 4.5. `QAAgent` — Quality Assurance

**Source**: [`agents/qa_agent.py`](../agents/qa_agent.py) · **Role Enum**: `AgentRole.QA`

**Responsibility**: Ensures code quality through:
-   Unit test generation (`pytest`).
-   API contract validation against the CTO's specification.
-   Security scanning using `bandit`.
-   Execution of generated tests with result reporting.

---

### 4.6. `DevOpsAgent` — Infrastructure & Deployment

**Source**: [`agents/devops_agent.py`](../agents/devops_agent.py) · **Role Enum**: `AgentRole.DEVOPS`

**Responsibility**: Generates all infrastructure-as-code and deployment artifacts:
-   `Dockerfile` (multi-stage builds for backend and frontend).
-   `docker-compose.yml` for local development.
-   Terraform modules for AWS (ECS, RDS, ALB, S3, CloudWatch).
-   GitHub Actions CI/CD pipelines.

**Local Mode Behavior**: In standalone mode, Terraform `apply` is simulated if the `terraform` binary is not installed on the host.

---

### 4.7. `FinanceAgent` — Chief Financial Officer

**Source**: [`agents/finance_agent.py`](../agents/finance_agent.py) · **Role Enum**: `AgentRole.FINANCE`

**Responsibility**: Real-time cost governance and budget enforcement.

**Output**: A comprehensive financial report including:
-   Budget overview (spend, remaining, utilization %).
-   Per-service cost breakdown.
-   Actionable optimization recommendations (e.g., "Purchase 1-year Reserved Instance for RDS").
-   ROI analysis comparing AI-driven development cost vs. manual developer cost.
-   Savings Plan recommendations.
-   Severity-based alerts (WARNING at 80%, CRITICAL at 95%).

---

## 5. Model Registry

**Source**: [`agents/model_registry.py`](../agents/model_registry.py)

The `ModelRegistry` is the single source of truth for default LLM assignments per agent role. It defines `AGENT_MODEL_DEFAULTS`, a dictionary mapping each `AgentRole` to a `ModelConfig(provider, model)`.

**Resolution Order** (when the system selects a model for an agent):
1.  User's per-role preference (from Dashboard Settings API).
2.  User's stored API key for a specific provider.
3.  `AGENT_MODEL_DEFAULTS` from the registry.
4.  Ultimate fallback: `amazon.nova-lite-v1:0` on Bedrock.

---

## 6. Adding a New Agent

To add a new specialist role (e.g., `SecurityAgent`):

1.  **Define the role** in `agents/roles.py`:
    ```python
    SECURITY = "Security"
    ```
2.  **Create the agent file** `agents/security_agent.py`, inheriting from `BaseAgent`.
3.  **Implement `run()`** with domain-specific logic and LLM prompts.
4.  **Register in the TUI/Runner**: Add it to the `agent_classes` list in `tui.py` and `desktop_nova.py`.
5.  **Add a default model** in `agents/model_registry.py`.
