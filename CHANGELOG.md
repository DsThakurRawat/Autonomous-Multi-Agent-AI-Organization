# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

### Removed
-

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
