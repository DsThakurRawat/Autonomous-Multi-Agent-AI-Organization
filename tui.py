import json
import httpx
import websockets
import asyncio
from datetime import datetime
from collections.abc import Generator
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.binding import Binding


class ProximusNovaTUI(App):
    """A Textual app to manage the Proximus-Nova Orchestrator live."""

    CSS = """
    Screen {
        background: #09090b;
        color: #f1f5f9;
    }
    
    #log {
        height: 1fr;
        border: solid #27272a;
        background: #09090b;
        padding: 1;
    }
    
    #cmd_input {
        dock: bottom;
        margin: 1 0;
        border: solid #10b981;
        background: #09090b;
        color: #f1f5f9;
    }
    
    Header {
        background: #050505;
        color: #34d399;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_log", "Clear Log", show=True),
    ]

    TITLE = "Proximus-Nova Orchestrator"
    SUB_TITLE = "Live Control Plane"

    def compose(self) -> Generator[ComposeResult, None, None]:
        yield Header(show_clock=True)
        yield RichLog(id="log", highlight=True, wrap=True, markup=True)
        yield Input(
            placeholder="➜ Type a goal (e.g. 'Build a Next.js landing page...')",
            id="cmd_input",
        )
        yield Input(
            placeholder="➜ Your Business Goal (e.g. 'Build a SaaS scaffold')",
            id="cmd_input",
        )
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)

        # Initial boot sequence logs
        log.write("[bold cyan]Loading Proximus-Nova kernel...[/]")
        log.write("[bold cyan]Initializing AI sub-systems: [/][bold green][OK][/]")
        log.write(
            "[bold cyan]Mounting Model Context Protocol (MCP): [/][bold green][OK][/]"
        )
        log.write(
            "[bold cyan]Connecting to Amazon Bedrock Nova Foundation: [/][bold green][READY][/]"
        )
        log.write("\n[dim]Awaiting command... Type 'exit' to quit.[/]")

        self.query_one(Input).focus()

    def action_clear_log(self) -> None:
        """Action for clearing the log."""
        self.query_one(RichLog).clear()

    async def simulate_execution(self, command: str) -> None:
        """Simulate execution logic streaming into the log."""
        log = self.query_one(RichLog)
        await asyncio.sleep(0.5)
        log.write(f"[dim]\\[Orchestrator] Parsing intent for: '{command}'[/]")
        await asyncio.sleep(1.0)
        log.write("[bold magenta]\\[Engineer Agent][/] ➜ Generating execution plan...")
        await asyncio.sleep(1.5)
        log.write(
            "[bold yellow]\\[System][/] ➜ Executing terminal command mapping context."
        )
        await asyncio.sleep(2.0)
        log.write(
            "[bold green]\\[Success][/] Task simulated successfully. (Run full system to see actual agent workflows)."
        )
        log.write("[bold cyan]Proximus-Nova TUI v1.0[/]")
        log.write("[dim]Searching for orchestrator at http://localhost:8080...[/]")
        self.query_one(Input).focus()

    async def stream_events(self, project_id: str):
        log = self.query_one(RichLog)
        uri = f"ws://localhost:8080/ws/{project_id}"

        try:
            async with websockets.connect(uri) as websocket:
                log.write(f"[bold green]Connected to project {project_id}[/]")

                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    event_type = data.get("type", "unknown")
                    agent = data.get("agent", "System")
                    text = data.get("message", "")

                    # Formatting based on role
                    colors = {
                        "CEO": "blue",
                        "CTO": "magenta",
                        "Engineer_Backend": "green",
                        "Engineer_Frontend": "cyan",
                        "QA": "yellow",
                        "DevOps": "red",
                        "Orchestrator": "white",
                    }
                    color = colors.get(agent, "dim")

                    timestamp = datetime.now().strftime("%H:%M:%S")

                    if event_type == "thinking":
                        log.write(
                            f"[dim]{timestamp}[/] [bold {color}]\\[{agent}][/] [italic dim]{text}[/]"
                        )
                    elif event_type == "task_start":
                        log.write(
                            f"[dim]{timestamp}[/] [bold {color}]\\[{agent}][/] ➜ Starting: [bold]{text}[/]"
                        )
                    elif event_type == "task_completed":
                        log.write(
                            f"[dim]{timestamp}[/] [bold {color}]\\[{agent}][/] ✅ [green]Completed[/]"
                        )
                    elif event_type == "phase_change":
                        log.write(f"\n[bold white]── PHASE CHANGE: {text} ──[/]\n")
                    else:
                        log.write(
                            f"[dim]{timestamp}[/] [bold {color}]\\[{agent}][/] {text}"
                        )

        except Exception as e:
            log.write(f"[bold red]Connection lost: {str(e)}[/]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        idea = event.value.strip()
        if not idea:
            return

        input_widget = self.query_one(Input)
        log = self.query_one(RichLog)

        input_widget.value = ""

        if idea.lower() in ("exit", "quit"):
            self.exit()
            return

        log.write(f"\n[bold white]➜ {idea}[/]")
        self.run_worker(self.simulate_execution(idea), exclusive=True)

        log.write(f"\n[bold white]🚀 Launching Goal:[/] {idea}")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8080/v1/projects",
                    json={"idea": idea, "name": idea[:30]},
                    timeout=10.0,
                )
                resp.raise_for_status()
                project = resp.json()
                project_id = project["id"]

                # Start listener background task
                self.run_worker(self.stream_events(project_id))

        except Exception as e:
            log.write(f"[bold red]Failed to launch project: {str(e)}[/]")


if __name__ == "__main__":
    ProximusNovaTUI().run()
