#!/usr/bin/env python3
"""
Quick-start demo runner.
Runs the full AI company pipeline locally without AWS - simulates all agent outputs.
Usage: python run_demo.py "Your business idea here"
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

from google import genai

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


async def run_full_demo(idea: str):
    """Simulate the full multi-agent pipeline with rich console output."""

    console.print(
        Panel.fit(
            f"[bold bright_magenta]🏢 Autonomous Multi-Agent AI Organization[/]\n"
            f"[dim]AI Company in a Box - Demo Mode[/]\n\n"
            f"[bold white]Business Idea:[/] {idea}",
            border_style="bright_magenta",
        )
    )

    # Import agents
    from agents.ceo_agent import CEOAgent
    from agents.cto_agent import CTOAgent
    from agents.engineer_agent import EngineerAgent
    from agents.qa_agent import QAAgent
    from agents.devops_agent import DevOpsAgent
    from agents.finance_agent import FinanceAgent
    from orchestrator.memory.project_memory import ProjectMemory
    from orchestrator.memory.decision_log import DecisionLog
    from orchestrator.memory.cost_ledger import CostLedger
    from orchestrator.memory.artifacts_store import ArtifactsStore

    # Load environment variables
    load_dotenv()

    # Dynamic LLM Setup
    llm_client = None
    model_name = "gemini-2.5-flash"
    gemini_key = os.getenv("GEMINI_API_KEY")

    if gemini_key and gemini_key != "your-gemini-key":
        llm_client = genai.Client(api_key=gemini_key)
        console.print("[dim]LLM initialized: Google Gemini[/dim]")
    else:
        console.print(
            "[yellow bold]⚠️ No valid Gemini API key found. Agents will run in mock mode.[/yellow bold]"
        )

    project_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Initialize shared memory
    memory = ProjectMemory(project_id=project_id)
    decision_log = DecisionLog(project_id=project_id)
    cost_ledger = CostLedger(project_id=project_id, budget_usd=200.0)
    artifacts = ArtifactsStore(project_id=project_id, output_dir="./output")

    memory.project_config = {"business_idea": idea, "budget_usd": 200.0}

    # -- Phase 1: CEO ------------------------------------------─
    console.print("\n[bold yellow]👑 CEO Agent[/] - Strategy Phase")
    ceo = CEOAgent(llm_client=llm_client, model_name=model_name)
    with console.status("[yellow]Analyzing business idea...[/]"):
        plan = await ceo.run(business_idea=idea, budget_usd=200.0)
        memory.business_plan = plan
        await asyncio.sleep(0.5)

    _print_plan(plan)

    # -- Phase 2: CTO ------------------------------------------─
    console.print("\n[bold blue]🏗 CTO Agent[/] - Architecture Phase")
    cto = CTOAgent(llm_client=llm_client, model_name=model_name)
    with console.status("[blue]Designing system architecture...[/]"):
        arch = await cto.run(business_plan=plan, budget_usd=200.0)
        memory.architecture = arch
        await asyncio.sleep(0.5)

    _print_arch(arch)

    # -- Phase 3: Engineers --------------------------------------
    console.print("\n[bold cyan]⚙️ Engineer Agents[/] - Build Phase (parallel)")
    eng_be = EngineerAgent(mode="backend", llm_client=llm_client, model_name=model_name)
    eng_fe = EngineerAgent(
        mode="frontend", llm_client=llm_client, model_name=model_name
    )

    class MockCtx:
        def __init__(self):
            self.memory = memory
            self.project_id = memory.project_id
            self.decision_log = decision_log
            self.cost_ledger = cost_ledger
            self.artifacts = artifacts

        async def emit_event(self, e):
            pass

    mock_ctx = MockCtx()

    with console.status("[cyan]Generating backend + frontend code in parallel...[/]"):
        results = await asyncio.gather(
            eng_be.run(context=mock_ctx), eng_fe.run(context=mock_ctx)
        )
        await asyncio.sleep(0.5)

    be_result, fe_result = results
    console.print(f"  ✅ Backend: [green]{be_result['file_count']} files[/] generated")
    console.print(f"  ✅ Frontend: [green]{fe_result['file_count']} files[/] generated")

    # -- Phase 4: QA --------------------------------------------─
    console.print("\n[bold green]🧪 QA Agent[/] - Testing Phase")
    qa = QAAgent(llm_client=llm_client, model_name=model_name)
    with console.status("[green]Running tests and security scan...[/]"):
        qa_result = await qa.run(context=mock_ctx)
        await asyncio.sleep(0.5)

    tr = qa_result["test_results"]
    console.print(f"  ✅ Tests: [green]{tr['passed']}/{tr['total']} passed[/]")
    console.print(
        f"  ✅ Security: [green]{qa_result['security_scan']['high_severity']} high-severity[/] issues"
    )
    console.print(
        f"  ✅ Coverage: [green]{qa_result['coverage']['line_coverage_pct']}%[/]"
    )

    # -- Phase 5: DevOps ------------------------------------------─
    console.print("\n[bold bright_cyan]🚀 DevOps Agent[/] - Deployment Phase")
    devops = DevOpsAgent(llm_client=llm_client, model_name=model_name)
    with console.status("[bright_cyan]Provisioning AWS and deploying...[/]"):
        devops_result = await devops.run(context=mock_ctx, project_name="ai-org")
        deployment = devops_result["deployment"]
        await asyncio.sleep(0.5)

    console.print(
        f"  ✅ Infra: [green]{len(devops_result['infrastructure_files'])} Terraform files[/]"
    )
    console.print(f"  ✅ Deployed: [bright_cyan link]{deployment['public_url']}[/]")
    console.print(
        f"  ✅ HTTPS: [green]{'Enabled' if deployment.get('https_enabled', False) else 'Disabled'}[/]"
    )

    # -- Phase 6: Finance ------------------------------------------
    console.print("\n[bold magenta]💰 Finance Agent[/] - Cost Analysis")
    finance = FinanceAgent(llm_client=llm_client, model_name=model_name)
    with console.status("[magenta]Analyzing AWS costs...[/]"):
        fin_result = await finance.run(context=mock_ctx, budget_usd=200.0)
        await asyncio.sleep(0.3)

    bov = fin_result["budget_overview"]
    console.print(f"  💵 Spent: [yellow]${bov['current_spend_usd']:.2f}[/] of $200")
    console.print(f"  📊 Status: {bov['status']}")
    console.print(
        f"  💡 {len(fin_result['optimizations'])} optimization opportunities found"
    )

    # -- Final Summary --------------------------------------------─
    _print_summary(project_id, idea, deployment, fin_result, artifacts)


def _print_plan(plan):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Feature", style="white")
    table.add_column("Priority", style="yellow")
    for f in plan.get("mvp_features", [])[:5]:
        if isinstance(f, dict):
            table.add_row(f.get("name", ""), f.get("priority", "P1"))
        else:
            table.add_row(str(f), "P1")
    console.print(table)


def _print_arch(arch):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Layer", style="cyan")
    table.add_column("Technology", style="white")
    for k, v in [
        ("Frontend", arch.get("frontend", {}).get("framework", "Next.js")),
        ("Backend", arch.get("backend", {}).get("framework", "FastAPI")),
        ("Database", arch.get("database", {}).get("type", "PostgreSQL")),
        ("Cloud", "AWS ECS Fargate"),
        ("Est. Cost", f"${arch.get('estimated_monthly_cost_usd',95)}/mo"),
    ]:
        table.add_row(k, str(v))
    console.print(table)


def _print_summary(project_id, idea, deployment, fin_result, artifacts):
    console.print(
        Panel(
            f"[bold bright_green]🎉 PROJECT COMPLETE![/]\n\n"
            f"[bold white]Idea:[/] {idea[:60]}\n"
            f"[bold white]Project ID:[/] {project_id}\n\n"
            f"[bold white]🌐 Public URL:[/] [bright_cyan]{deployment['public_url']}[/]\n"
            f"[bold white]💰 Total Cost:[/] ${fin_result['budget_overview']['current_spend_usd']:.2f}/mo\n"
            f"[bold white]📦 Artifacts:[/] {len(artifacts._artifacts)} files generated\n"
            f"[bold white]⏱ Time:[/] ~19 seconds (production would be ~3-5 min)\n\n"
            f"[dim]Output saved to: ./output/{project_id}/[/]",
            border_style="bright_green",
            title="[bold]AI Company in a Box - Results[/]",
        )
    )


if __name__ == "__main__":
    idea = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Build a SaaS platform for student internship application tracking"
    )
    asyncio.run(run_full_demo(idea))
