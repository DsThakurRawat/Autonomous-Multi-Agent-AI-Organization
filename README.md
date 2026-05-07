# SARANG — Autonomous Research Swarm

SARANG is a high-fidelity, autonomous research environment designed to deconstruct complex scientific papers, extract formal mathematical frameworks, and synthesize reproducible implementations.

## 🚀 The Research Swarm
Powered by **Gemini 2.0 Flash**, SARANG orchestrates a specialized team of autonomous agents:

*   **Research Intelligence**: Synthesizes high-level strategy and hypothesis deconstruction.
*   **Math Architect**: Extracts and formalizes LaTeX equations and theorems.
*   **Implementation Specialist**: Generates validated Python simulations and scripts.
*   **Visual Insights**: Analyzes genomics data, figures, and visual evidence.
*   **Reproducibility Engineer**: Ensures every claim is backed by executable validation.
*   **Peer Reviewer**: Critiques logic and ensures scientific rigor.
*   **Compute Monitor**: Optimizes resource allocation and cost efficiency.

## 🛠️ Architecture
- **Intelligence** (Python): FastAPI service with multi-agent reasoning chains, semantic caching, and real LLM dispatch.
- **Gateway** (Go): Gin-based HTTP/WebSocket gateway with Redis pubsub relay.
- **Dashboard** (Next.js): Minimal TypeScript UI for research interaction.
- **Router** (Python): Mixture of Experts (MoE) vector-based agent selection.

## 🚦 Quick Start
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env  # Add your GEMINI_API_KEY

# 3. Launch everything
./dev.sh
```

Or manually:
```bash
# Terminal 1: Python agents
source venv/bin/activate && PYTHONPATH=. python3 agents_service/api/main.py

# Terminal 2: Go gateway
cd gateway && go run cmd/gateway/main.go

# Terminal 3: Dashboard
cd dashboard && npm run dev
```

Open **http://localhost:3000** in your browser.

---
*SARANG — Scientific Analysis & Reproducible Agentic Network Gateway*
