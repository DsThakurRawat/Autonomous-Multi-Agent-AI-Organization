# SARANG — Autonomous Research Swarm

SARANG is a high-fidelity, autonomous research environment designed to deconstruct complex scientific papers, extract formal mathematical frameworks, and synthesize reproducible implementations.

## 🚀 The Research Swarm
Powered by **Gemini 1.5**, **Claude 3.5**, and **GPT-4o**, SARANG orchestrates a specialized team of autonomous agents:

*   **Lead Researcher**: Synthesizes high-level strategy and hypothesis deconstruction.
*   **Math Architect**: Extracts and formalizes LaTeX equations and theorems.
*   **Implementation Specialist**: Generates validated Python simulations and scripts.
*   **Visual Insights**: Analyzes genomics data, figures, and visual evidence.
*   **Reproducibility Engineer**: Ensures every claim is backed by executable validation.
*   **Peer Reviewer**: Critiques logic and ensures scientific rigor.

## 🛠️ Architecture
- **Frontend**: Next.js (TypeScript) + Vanilla CSS (Premium Claude-style UI).
- **Orchestrator**: Go Gateway (Mission management & WebSocket streaming).
- **Intelligence**: Python Swarm Service (Real LLM reasoning & tool execution).
- **Router**: Mixture of Experts (MoE) vector-based agent selection.

## 🚦 Quick Start
1.  **Configure API Keys**: Add your Gemini/Claude/OpenAI keys to `.env`.
2.  **Launch Gateway**: `cd gateway && go run cmd/gateway/main.go`
3.  **Launch Agents**: `cd agents_service && python api/main.py`
4.  **Start Dashboard**: `cd dashboard && npm run dev`

---
*SARANG — Scientific Analysis & Reproducible Agentic Network Gateway*
