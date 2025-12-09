"""Rich display system for pipeline execution with beautiful CLI output."""

import time
from typing import Any
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.tree import Tree
    from rich.text import Text
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PipelineDisplay:
    """Beautiful CLI display for pipeline execution."""

    def __init__(self, pipeline_name: str, steps: list[Any], dag: Any, verbose: bool = True):
        """Initialize display system.

        Args:
            pipeline_name: Name of the pipeline
            steps: List of step objects
            dag: Pipeline DAG
            verbose: Whether to show detailed output
        """
        self.pipeline_name = pipeline_name
        self.steps = steps
        self.dag = dag
        self.verbose = verbose
        self.console = Console() if RICH_AVAILABLE else None
        self.step_status = {step.name: "pending" for step in steps}
        self.step_durations = {}
        self.step_outputs = {}
        self.step_errors = {}
        self.step_cached = {}
        self.start_time = None
        self.progress = None
        self.progress_tasks = {}  # Track progress tasks for each step
        if RICH_AVAILABLE:
            self._init_progress()

    def _init_progress(self) -> None:
        """Initialize progress display."""
        if not RICH_AVAILABLE:
            return
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def show_header(self) -> None:
        """Display pipeline header with DAG visualization."""
        if not self.verbose:
            return

        if RICH_AVAILABLE:
            # Rich header
            header = Panel(
                f"[bold cyan]🌊 flowyml Pipeline[/bold cyan]\n" f"[bold]{self.pipeline_name}[/bold]",
                border_style="cyan",
                box=box.ROUNDED,
            )
            self.console.print(header)
            self.console.print()

            # DAG visualization
            self._show_dag_rich()
        else:
            # Fallback header
            print("=" * 70)
            print(f"🌊 flowyml Pipeline: {self.pipeline_name}")
            print("=" * 70)
            print()
            self._show_dag_simple()

    def _show_dag_rich(self) -> None:
        """Show DAG using rich."""
        if not self.dag:
            return

        tree = Tree("📊 Pipeline Execution Plan")

        # Get topological order
        try:
            topo_order = self.dag.topological_sort()
        except Exception:
            topo_order = list(self.dag.nodes.values())

        # Group steps by execution group
        groups = defaultdict(list)
        for step in self.steps:
            if step.execution_group:
                groups[step.execution_group].append(step)
            else:
                groups[None].append(step)

        # Build tree
        for i, node in enumerate(topo_order, 1):
            step = next((s for s in self.steps if s.name == node.name), None)
            if not step:
                continue

            # Check if in a group
            group_name = step.execution_group
            if group_name and group_name in groups:
                # Add to group branch
                if not hasattr(self, "_group_branches"):
                    self._group_branches = {}
                if group_name not in self._group_branches:
                    group_branch = tree.add(f"📦 [cyan]{group_name}[/cyan]")
                    self._group_branches[group_name] = group_branch
                branch = self._group_branches[group_name]
            else:
                branch = tree

            # Step info
            deps = self.dag.edges.get(node.name, [])
            deps_str = f" → depends on: {', '.join(deps)}" if deps else ""

            inputs_str = f"Inputs: {', '.join(step.inputs)}" if step.inputs else "No inputs"
            outputs_str = f"Outputs: {', '.join(step.outputs)}" if step.outputs else "No outputs"

            step_text = f"[bold]{i}. {step.name}[/bold]\n" f"   {inputs_str}\n" f"   {outputs_str}"
            if deps_str:
                step_text += f"\n   [dim]{deps_str}[/dim]"

            branch.add(step_text)

        self.console.print(tree)
        self.console.print()

    def _show_dag_simple(self) -> None:
        """Show DAG using simple text."""
        if not self.dag:
            return

        print("Pipeline DAG:")
        print("=" * 70)

        try:
            topo_order = self.dag.topological_sort()
        except Exception:
            topo_order = list(self.dag.nodes.values())

        for i, node in enumerate(topo_order, 1):
            step = next((s for s in self.steps if s.name == node.name), None)
            if not step:
                continue

            deps = self.dag.edges.get(node.name, [])
            deps_str = f"Dependencies: {', '.join(deps)}" if deps else "Dependencies: none"

            inputs_str = f"Inputs: {step.inputs}" if step.inputs else "Inputs: []"
            outputs_str = f"Outputs: {step.outputs}" if step.outputs else "Outputs: []"

            group_str = f" [Group: {step.execution_group}]" if step.execution_group else ""

            print(f"{i}. {step.name}{group_str}")
            print(f"   {inputs_str}")
            print(f"   {outputs_str}")
            print(f"   {deps_str}")
            print()

    def show_execution_start(self) -> None:
        """Show execution start message."""
        self.start_time = time.time()
        if not self.verbose:
            return

        if RICH_AVAILABLE:
            # Use Text for styled output
            start_text = Text()
            start_text.append("🚀 ", style="bold")
            start_text.append("Starting pipeline execution...", style="bold green")
            self.console.print(start_text)
            self.console.print()

            # Start progress display if available
            if self.progress:
                self.progress.start()
        else:
            print("🚀 Starting pipeline execution...")
            print()

    def update_step_status(
        self,
        step_name: str,
        status: str,
        duration: float = None,
        cached: bool = False,
        error: str = None,
    ) -> None:
        """Update and display step status.

        Args:
            step_name: Name of the step
            status: Status (running, success, failed, cached)
            duration: Execution duration in seconds
            cached: Whether step was cached
            error: Error message if failed
        """
        self.step_status[step_name] = status
        if duration is not None:
            self.step_durations[step_name] = duration
        if cached:
            self.step_cached[step_name] = True
        if error:
            self.step_errors[step_name] = error

        if not self.verbose:
            return

        if RICH_AVAILABLE:
            self._update_step_rich(step_name, status, duration, cached, error)
        else:
            self._update_step_simple(step_name, status, duration, cached, error)

    def _update_step_rich(
        self,
        step_name: str,
        status: str,
        duration: float = None,
        cached: bool = False,
        error: str = None,
    ) -> None:
        """Update step display using rich with progress tracking."""
        if status == "running":
            # Use Text for better formatting
            icon = "⏳"
            color = "yellow"
            text_obj = Text()
            text_obj.append(f"{icon} ", style=color)
            text_obj.append(step_name, style=f"bold {color}")
            text_obj.append(" running...", style="dim")
            self.console.print(text_obj)

            # Start progress tracking if available
            if self.progress and step_name not in self.progress_tasks:
                task_id = self.progress.add_task(
                    f"[yellow]⏳ {step_name}[/yellow]",
                    total=100,
                )
                self.progress_tasks[step_name] = task_id
                self.progress.update(task_id, completed=50)  # Show progress

        elif status == "success":
            icon = "✅"
            color = "green"
            text_obj = Text()
            text_obj.append(f"{icon} ", style=color)
            text_obj.append(step_name, style=f"bold {color}")
            if cached:
                text_obj.append(" (cached)", style="dim italic")
            if duration:
                text_obj.append(f" ({duration:.2f}s)", style="dim")
            self.console.print(text_obj)

            # Complete progress task
            if self.progress and step_name in self.progress_tasks:
                task_id = self.progress_tasks[step_name]
                self.progress.update(task_id, completed=100)
                self.progress.remove_task(task_id)
                del self.progress_tasks[step_name]

        elif status == "failed":
            icon = "❌"
            color = "red"
            text_obj = Text()
            text_obj.append(f"{icon} ", style=color)
            text_obj.append(step_name, style=f"bold {color}")
            if error:
                text_obj.append(f" - {error[:100]}", style="red dim")
            self.console.print(text_obj)

            # Remove progress task on failure
            if self.progress and step_name in self.progress_tasks:
                task_id = self.progress_tasks[step_name]
                self.progress.remove_task(task_id)
                del self.progress_tasks[step_name]
        else:
            icon = "⏸️"
            text_obj = Text()
            text_obj.append(f"{icon} ", style="dim")
            text_obj.append(step_name, style="dim")
            self.console.print(text_obj)

    def _update_step_simple(
        self,
        step_name: str,
        status: str,
        duration: float = None,
        cached: bool = False,
        error: str = None,
    ) -> None:
        """Update step display using simple text."""
        if status == "running":
            print(f"⏳ {step_name} running...")
        elif status == "success":
            cached_text = " (cached)" if cached else ""
            duration_text = f" ({duration:.2f}s)" if duration else ""
            print(f"✅ {step_name}{cached_text}{duration_text}")
        elif status == "failed":
            error_text = f" - {error}" if error else ""
            print(f"❌ {step_name}{error_text}")
        else:
            print(f"⏸️ {step_name}")

    def show_summary(self, result: Any, ui_url: str = None, run_url: str = None) -> None:
        """Show execution summary.

        Args:
            result: PipelineResult object
            ui_url: Optional UI server URL
            run_url: Optional run-specific UI URL
        """
        if not self.verbose:
            return

        total_duration = time.time() - self.start_time if self.start_time else result.duration_seconds

        if RICH_AVAILABLE:
            self._show_summary_rich(result, total_duration, ui_url, run_url)
        else:
            self._show_summary_simple(result, total_duration, ui_url, run_url)

    def _show_summary_rich(self, result: Any, total_duration: float, ui_url: str = None, run_url: str = None) -> None:
        """Show summary using rich."""
        # Stop progress display if running
        if self.progress:
            self.progress.stop()
            self.console.print()

        self.console.print()

        # Summary table with enhanced styling
        table = Table(
            title="[bold cyan]📊 Execution Summary[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        table.add_column("Metric", style="cyan", no_wrap=True, width=20)
        table.add_column("Value", style="green", width=30)

        # Use Text for status with better formatting
        status_text = Text()
        if result.success:
            status_text.append("✅ ", style="green")
            status_text.append("SUCCESS", style="bold green")
        else:
            status_text.append("❌ ", style="red")
            status_text.append("FAILED", style="bold red")

        table.add_row("Pipeline", self.pipeline_name)
        table.add_row("Run ID", result.run_id[:16] + "...")
        table.add_row("Status", status_text)
        table.add_row("Duration", f"[green]{total_duration:.2f}s[/green]")
        table.add_row("Steps", f"[cyan]{len(result.step_results)}[/cyan]")

        # Count cached steps
        cached_count = sum(1 for r in result.step_results.values() if r.cached)
        if cached_count > 0:
            table.add_row("Cached Steps", f"[yellow]{cached_count}[/yellow]")

        self.console.print(table)
        self.console.print()

        # Show UI URL if available
        if run_url:
            ui_panel = Panel(
                f"[bold cyan]🌐 View in UI:[/bold cyan]\n[link={run_url}]{run_url}[/link]",
                border_style="cyan",
                box=box.ROUNDED,
            )
            self.console.print(ui_panel)
            self.console.print()
        elif ui_url:
            ui_panel = Panel(
                f"[bold cyan]🌐 UI Available:[/bold cyan]\n[link={ui_url}]{ui_url}[/link]",
                border_style="cyan",
                box=box.ROUNDED,
            )
            self.console.print(ui_panel)
            self.console.print()

        # Step results table
        step_table = Table(title="📋 Step Results", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Status", justify="center")
        step_table.add_column("Duration", justify="right")
        step_table.add_column("Details")

        for step_name, step_result in result.step_results.items():
            if step_result.success:
                status = "[green]✅[/green]"
                details = "[dim]Cached[/dim]" if step_result.cached else ""
            else:
                status = "[red]❌[/red]"
                details = f"[red]{step_result.error[:50]}...[/red]" if step_result.error else ""

            duration = f"{step_result.duration_seconds:.2f}s" if step_result.duration_seconds else "N/A"
            step_table.add_row(step_name, status, duration, details)

        self.console.print(step_table)
        self.console.print()

        # Outputs summary
        if result.outputs:
            outputs_panel = Panel(
                self._format_outputs_rich(result.outputs),
                title="📦 Outputs",
                border_style="cyan",
                box=box.ROUNDED,
            )
            self.console.print(outputs_panel)
            self.console.print()

    def _format_outputs_rich(self, outputs: dict) -> str:
        """Format outputs for rich display."""
        lines = []
        for key, value in outputs.items():
            # Skip internal/duplicate outputs (step names vs output names)
            if key in [s.name for s in self.steps] and any(
                out_name in outputs for s in self.steps for out_name in (s.outputs or []) if s.name == key
            ):
                continue  # Skip step name if we have the actual output name

            if hasattr(value, "__class__"):
                value_str = f"{value.__class__.__name__}"
                if hasattr(value, "name"):
                    value_str += f" (name: {value.name})"
                if hasattr(value, "version"):
                    value_str += f" (version: {value.version})"
                # Try to get more info for Asset types
                if hasattr(value, "__dict__"):
                    attrs = {
                        k: v
                        for k, v in value.__dict__.items()
                        if not k.startswith("_") and k not in ["name", "version"]
                    }
                    if attrs:
                        # Show first few attributes
                        attr_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
                        if len(attrs) > 3:
                            attr_str += "..."
                        value_str += f" [{attr_str}]"
            else:
                # For simple types, show a preview
                value_str = str(value)
                if len(value_str) > 80:
                    value_str = value_str[:80] + "..."
            lines.append(f"[cyan]{key}:[/cyan] {value_str}")
        return "\n".join(lines) if lines else "[dim]No outputs[/dim]"

    def _show_summary_simple(self, result: Any, total_duration: float, ui_url: str = None, run_url: str = None) -> None:
        """Show summary using simple text."""
        print()
        print("=" * 70)
        status_icon = "✅" if result.success else "❌"
        status_text = "SUCCESS" if result.success else "FAILED"
        print(f"{status_icon} Pipeline {status_text}!")
        print("=" * 70)
        print()
        print(f"Pipeline: {self.pipeline_name}")
        print(f"Run ID: {result.run_id}")
        print(f"Duration: {total_duration:.2f}s")
        print(f"Steps: {len(result.step_results)}")

        # Show UI URL if available
        if run_url:
            print()
            print(f"🌐 View in UI: {run_url}")
        elif ui_url:
            print()
            print(f"🌐 UI Available: {ui_url}")
        print()

        print("Step Results:")
        print("-" * 70)
        for step_name, step_result in result.step_results.items():
            icon = "✅" if step_result.success else "❌"
            cached = " (cached)" if step_result.cached else ""
            duration = f" ({step_result.duration_seconds:.2f}s)" if step_result.duration_seconds else ""
            print(f"  {icon} {step_name}{cached}{duration}")
            if step_result.error:
                print(f"     Error: {step_result.error[:100]}")
        print()

        if result.outputs:
            print("Outputs:")
            print("-" * 70)
            for key, value in result.outputs.items():
                # Skip internal/duplicate outputs
                if key in [s.name for s in self.steps] and any(
                    out_name in result.outputs for s in self.steps for out_name in (s.outputs or []) if s.name == key
                ):
                    continue

                if hasattr(value, "__class__"):
                    value_str = f"{value.__class__.__name__}"
                    if hasattr(value, "name"):
                        value_str += f" (name: {value.name})"
                    if hasattr(value, "version"):
                        value_str += f" (version: {value.version})"
                else:
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                print(f"  {key}: {value_str}")
            print()

        print("=" * 70)
