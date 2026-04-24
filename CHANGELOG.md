# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **Modern Go 1.25.0**: Full support for newest Go features (generic type aliases, `iter` package).
- **Pydantic V2 Migration**: Upgraded all Python agents to Pydantic V2 for 5x performance gains in data validation.
- **MCP Server**: Native Model Context Protocol (MCP) server for secure, standardized tool execution.
- **Egress Proxy**: Secure egress gateway with domain-level allowlist enforcement for agents.
- **Rust-based Security**: High-performance AST validation and PII scrubbing services written in Rust.
- **Production-Grade Observability**: Unified distributed tracing with OpenTelemetry and Jaeger.

### Changed

- Updated `learning_roadmap.md` to reflect the 2026 production-grade architecture.
- Refined gRPC orchestrator schemas for better budget tracking.

### Fixed

- Markdown linting and formatting issues across documentation.

---

## [1.0.0] - 2026-03-17

### Added

- Initial project setup with Go orchestrator and Python agent swarm.
- Premium Next.js Vibe Dashboard for real-time task monitoring.
- Production-Grade Shielding (gVisor ready, tmpfs secrets, log redaction).
- Self-Healing Connectivity via Go Health Orchestrator.
- Atomic Git-based state recovery and checkpointing.
- Mixture-of-Experts (MoE) scoring for multi-model routing.
- Real-time budget exceeded notifications and governance.

### Commit Message Format

The project follows a standardized commit message convention to keep the history readable and searchable:

- `feat`: add Kafka lease model
- `fix`: resolve race condition
- `docs`: update setup guide
- `refactor`: optimize DAG traversal
- `test`: add unit tests
- `chore`: dependency update

### Changed

- Refined agent interaction patterns for higher reliability.
- Optimized Kafka event dispatching for atomic delivery.
- Improved documentation for open-source pivot.

### Fixed

- Environment setup bug on Ubuntu 24.04.
- Type errors in planner and agent registry.
- Redis connectivity gaps in health checks.
