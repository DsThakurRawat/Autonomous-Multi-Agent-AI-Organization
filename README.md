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
- **Backend Swarm Engine** (Python): Pure Python FastAPI service managing WebSockets, multi-agent reasoning chains, tiered LLM routing (Gemini → Groq → Mock), and in-memory session management.
- **Frontend Dashboard** (Next.js): React UI with real-time agentic interactions.

## 🚦 Quick Start
```bash
# 1. Install Python & Node dependencies
pip install -r requirements.txt
cd dashboard && npm install && cd ..

# 2. Configure API keys
# Add your GEMINI_API_KEY and GROQ_API_KEY (comma separated for multiple keys)
cp .env.example .env  

# 3. Launch everything
./dev.sh
```

Or manually:
```bash
# Terminal 1: Python agents (Port 8000)
source venv/bin/activate && PYTHONPATH=. python3 agents_service/api/main.py

# Terminal 2: Dashboard (Port 3000)
cd dashboard && npm run dev
```

Open **http://localhost:3000** in your browser.

---
*SARANG — Scientific Analysis & Reproducible Agentic Network Gateway*
