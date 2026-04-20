# Technical Deep-Dive: Desktop Mastery

Proximus Nova's **Desktop Workbench** mode is powered by a standalone, zero-infrastructure Python orchestration engine. This guide explains the internals of the local swarm and how it achieves high-precision host-native engineering.

---

## 🧠 The Standalone Engine (`orchestrator/planner.py`)

Unlike the Enterprise mode which relies on Go and Kafka, the Desktop Nova mode uses the `OrchestratorEngine` directly in-process.

### Core Execution Loop
1. **Bootstrap**: The `desktop_nova.py` or `tui.py` instantiates all specialist agents (CEO, CTO, Engineers, etc.) with local LLM clients.
2. **Strategy Phase**: The **CEO Agent** analyzes the goal and produces a structured `BusinessPlan`.
3. **Architecture Phase**: The **CTO Agent** builds a technical roadmap and directory structure.
4. **DAG Generation**: The engine builds a Directed Acyclic Graph (DAG) of tasks using `TaskGraph`.
5. **Parallel Execution**: The engine uses `asyncio.gather` to execute independent tasks (e.g., Backend and Frontend) in parallel on the local host.

---

## 💾 Local Persistent Memory

Since Desktop Nova does not use PostgreSQL, it relies on a filesystem-based memory system located in `orchestrator/memory/`:

- **ProjectMemory**: Stores the core state of the project (Idea, Tech Stack, PRDs).
- **DecisionLog**: A chronological record of every AI decision, tool call, and reasoning step.
- **ArtifactsStore**: Manages all generated files, logs, and build artifacts.
- **CostLedger**: Tracks token usage and estimated USD costs in real-time.

All data is persisted in the `./output/<project_id>/` directory, allowing missions to be resumed or audited later.

---

## 🪚 Surgical Tooling: `LocalFileEditTool`

The hallmark of Proximus Precision is the **Surgical Edit** loop. Instead of overwriting files entirely, agents use a precision search-and-replace tool.

### Why Surgery?
1. **Efficiency**: Only changes the lines that matter, saving massive amounts of tokens.
2. **Safety**: Prevents agents from accidentally deleting large blocks of existing, working code.
3. **Context Preservation**: Keeps the file's structure and comments intact exactly as the user wrote them.

### Logic Flow:
1. Agent reads the target file.
2. Agent identifies the `target_content` (the exact block to change).
3. Agent produces the `replacement_content`.
4. The tool performs an atomic search-and-replace on the host disk.

---

## 🕹️ Desktop Control Center (`tui.py`)

The Proximus TUI is the "Primary Interface" for the organization. It bypasses all web complexity to provide a direct console link to the agents.

- **Standalone Mode**: Wire-level integration with the `OrchestratorEngine`.
- **Live Event Stream**: Every agent "thought" and "action" is streamed to the terminal via the `ExecutionEvent` bus.
- **Host Sync**: Every file change made by the agents is immediately visible on your disk.

---

## ⚖️ Standalone vs Enterprise

| Feature | Desktop Nova | Enterprise SaaS |
| :--- | :--- | :--- |
| **Orchestrator** | Python (In-Process) | Go (gRPC Service) |
| **Event Bus** | `asyncio.Queue` | Apache Kafka |
| **State Store** | Filesystem (JSON) | PostgreSQL |
| **Dashboard** | TUI (Textual) | Next.js (Web) |
| **Isolation** | Host Native | Docker / gVisor |
