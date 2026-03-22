"""FlowyML TUI — Premium Terminal User Interface.

A full-featured Textual-based TUI dashboard for monitoring,
browsing, and managing FlowyML pipelines, runs, and database.

Launch with: flowyml tui
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Rule,
    Static,
    TabbedContent,
    TabPane,
)


# ── Utility helpers ──────────────────────────────────────────────────
def _store():
    """Lazy-import the metadata store."""
    from flowyml.storage.sql import SQLMetadataStore

    return SQLMetadataStore()


def _db_size_str() -> str:
    p = Path(".flowyml/metadata.db")
    if p.exists():
        size = p.stat().st_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.2f} MB"
    return "N/A"


def _table_counts() -> dict[str, int]:
    try:
        s = _store()
        from sqlalchemy import func, select

        counts = {}
        tables = {
            "runs": s.runs,
            "artifacts": s.artifacts,
            "metrics": s.metrics,
            "model_metrics": s.model_metrics,
            "parameters": s.parameters,
            "experiments": s.experiments,
            "experiment_runs": s.experiment_runs,
            "traces": s.traces,
            "pipeline_definitions": s.pipeline_definitions,
            "projects": s.projects,
            "model_versions": s.model_versions,
            "pipeline_templates": s.pipeline_templates,
        }
        with s.engine.connect() as conn:
            for name, tbl in tables.items():
                try:
                    counts[name] = (
                        conn.execute(
                            select(func.count()).select_from(tbl),
                        ).scalar()
                        or 0
                    )
                except Exception:
                    counts[name] = 0
        return counts
    except Exception:
        return {}


# ── Styled widgets ───────────────────────────────────────────────────
LOGO = r"""
 _____ _                     __  __ _
|  ___| | _____      ___   _|  \/  | |
| |_  | |/ _ \ \ /\ / / | | | |\/| | |
|  _| | | (_) \ V  V /| |_| | |  | | |___
|_|   |_|\___/ \_/\_/  \__, |_|  |_|_____|
                       |___/
"""


class StatCard(Static):
    """A small statistics card."""

    DEFAULT_CSS = """
    StatCard {
        width: 1fr; height: 5;
        border: solid $accent; padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(self, label: str, value: str = "—", style_color: str = "cyan", **kw) -> None:
        super().__init__(**kw)
        self._label, self._value, self._color = label, value, style_color

    def render(self) -> str:
        return f"[bold {self._color}]{self._value}[/]\n[dim]{self._label}[/]"

    def update_value(self, value: str) -> None:
        self._value = value
        self.refresh()


class ConfirmPurgeScreen(ModalScreen[bool]):
    """Modal confirmation for database purge."""

    DEFAULT_CSS = """
    ConfirmPurgeScreen { align: center middle; }
    ConfirmPurgeScreen > Vertical {
        width: 60; height: auto;
        border: thick $error; background: $surface; padding: 1 2;
    }
    """

    def __init__(self, table_name: str) -> None:
        super().__init__()
        self._table_name = table_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold red]⚠  Purge '{self._table_name}'?[/]")
            yield Label("This will permanently delete all rows.")
            yield Rule()
            with Horizontal():
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Purge", variant="error", id="confirm")

    @on(Button.Pressed, "#cancel")
    def do_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def do_confirm(self) -> None:
        self.dismiss(True)


# ── Main TUI App ─────────────────────────────────────────────────────
class FlowyMLApp(App):
    """FlowyML Terminal Dashboard."""

    TITLE = "FlowyML Dashboard"
    CSS = """
    Screen { background: $surface; }
    #stats-row { height: 5; margin: 0 1; }
    #logo { width: 100%; height: 7; color: $accent; text-align: center; }
    .data-tbl { height: 1fr; margin: 0 1; border: solid $primary; }
    .detail { width: 100%; height: 1fr; margin: 0 1;
              border: solid $accent; padding: 1; overflow-y: auto; }
    .purge-btn { margin: 0 1; }
    .section-label { margin: 0 1; padding: 0; }
    TabbedContent { height: 1fr; }
    TabPane { padding: 0; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
    ]

    selected_run_id: reactive[str | None] = reactive(None)

    # ── Compose ──────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            # ── Dashboard ────────────────────────────────────────────
            with TabPane("🏠 Dashboard", id="dashboard"), VerticalScroll():
                yield Static(LOGO.strip(), id="logo")
                with Horizontal(id="stats-row"):
                    yield StatCard("Total Runs", style_color="green", id="stat-runs")
                    yield StatCard("Pipelines", style_color="cyan", id="stat-pipelines")
                    yield StatCard("Experiments", style_color="yellow", id="stat-experiments")
                    yield StatCard("Models", style_color="magenta", id="stat-models")
                    yield StatCard("Traces", style_color="blue", id="stat-traces")
                    yield StatCard("DB Size", style_color="white", id="stat-db")
                yield Label("[bold cyan]  📈 Performance[/]", classes="section-label")
                yield Static(id="perf-panel")
                yield Label("[bold cyan]  📋 Recent Runs[/]", classes="section-label")
                yield DataTable(id="recent-runs", classes="data-tbl")

            # ── Runs ─────────────────────────────────────────────────
            with TabPane("🏃 Runs", id="runs"), Vertical():
                with Horizontal():
                    yield Button("↻ Refresh", id="btn-refresh-runs", variant="primary")
                yield DataTable(id="all-runs-table", classes="data-tbl")
                yield Label("[bold cyan]  📄 Run Details[/]", classes="section-label")
                yield Static(id="detail-panel", classes="detail")

            # ── Experiments ───────────────────────────────────────────
            with TabPane("🧪 Experiments", id="experiments"), Vertical():
                with Horizontal():
                    yield Button("↻ Refresh", id="btn-refresh-exp", variant="primary")
                yield DataTable(id="exp-table", classes="data-tbl")
                yield Label("[bold cyan]  📄 Experiment Runs[/]", classes="section-label")
                yield DataTable(id="exp-runs-table", classes="data-tbl")

            # ── Models ───────────────────────────────────────────────
            with TabPane("📦 Models", id="models"), Vertical():
                with Horizontal():
                    yield Button("↻ Refresh", id="btn-refresh-models", variant="primary")
                yield DataTable(id="models-table", classes="data-tbl")
                yield Label("[bold cyan]  📄 Version Details[/]", classes="section-label")
                yield Static(id="model-detail", classes="detail")

            # ── Pipelines ────────────────────────────────────────────
            with TabPane("🔀 Pipelines", id="pipelines"), Vertical():
                with Horizontal():
                    yield Button("↻ Refresh", id="btn-refresh-pipes", variant="primary")
                yield DataTable(id="pipes-table", classes="data-tbl")
                yield Label("[bold cyan]  📄 Pipeline Definition[/]", classes="section-label")
                yield Static(id="pipe-detail", classes="detail")

            # ── Traces ───────────────────────────────────────────────
            with TabPane("🔍 Traces", id="traces"), Vertical():
                with Horizontal():
                    yield Button("↻ Refresh", id="btn-refresh-traces", variant="primary")
                yield DataTable(id="traces-table", classes="data-tbl")
                yield Label("[bold cyan]  📄 Trace Detail[/]", classes="section-label")
                yield Static(id="trace-detail", classes="detail")

            # ── Database ─────────────────────────────────────────────
            with TabPane("🗄  Database", id="database"), VerticalScroll():
                yield Label("[bold cyan]  📊 Table Statistics[/]", classes="section-label")
                yield DataTable(id="db-stats-table", classes="data-tbl")
                yield Rule()
                yield Label("[bold red]  ⚠  Danger Zone[/]", classes="section-label")
                with Horizontal():
                    yield Button("Purge Runs", variant="error", id="purge-runs", classes="purge-btn")
                    yield Button("Purge Traces", variant="error", id="purge-traces", classes="purge-btn")
                    yield Button("Purge Artifacts", variant="error", id="purge-artifacts", classes="purge-btn")
                    yield Button("Purge Metrics", variant="error", id="purge-metrics", classes="purge-btn")
                with Horizontal():
                    yield Button("Purge Models", variant="error", id="purge-models", classes="purge-btn")
                    yield Button("Purge Experiments", variant="error", id="purge-experiments", classes="purge-btn")
                    yield Button("🔥 RESET ALL", variant="error", id="purge-all", classes="purge-btn")
                yield Rule()
                yield Label("", id="purge-result")

            # ── Config ───────────────────────────────────────────────
            with TabPane("⚙  Config", id="config"), VerticalScroll():
                yield Static(id="config-panel")

        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────
    def on_mount(self) -> None:
        self._refresh_all()

    def action_refresh(self) -> None:
        self._refresh_all()
        self.notify("Refreshed ↻", severity="information")

    def _refresh_all(self) -> None:
        self.load_dashboard()
        self.load_all_runs()
        self.load_experiments()
        self.load_models()
        self.load_pipelines()
        self.load_traces()
        self.load_db_stats()
        self.load_config()

    # ══════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_dashboard(self) -> None:
        counts = _table_counts()
        db_size = _db_size_str()
        try:
            s = _store()
            pipelines = s.list_pipelines()
            n_pipes = len(pipelines)
            stats = s.get_statistics()
            runs = s.list_runs(limit=20)
        except Exception:
            n_pipes, stats, runs = 0, {}, []
        self.call_from_thread(
            self._apply_dashboard,
            counts,
            runs,
            db_size,
            n_pipes,
            stats,
        )

    def _apply_dashboard(self, counts, runs, db_size, n_pipes, stats):
        with contextlib.suppress(NoMatches):
            self.query_one("#stat-runs", StatCard).update_value(str(counts.get("runs", 0)))
            self.query_one("#stat-pipelines", StatCard).update_value(str(n_pipes))
            self.query_one("#stat-experiments", StatCard).update_value(str(counts.get("experiments", 0)))
            self.query_one("#stat-models", StatCard).update_value(str(counts.get("model_versions", 0)))
            self.query_one("#stat-traces", StatCard).update_value(str(counts.get("traces", 0)))
            self.query_one("#stat-db", StatCard).update_value(db_size)

        # Performance panel
        with contextlib.suppress(NoMatches):
            completed = stats.get("completed_runs", 0)
            total = stats.get("total_runs", 0)
            rate = f"{completed / total:.0%}" if total else "—"
            avg_dur = stats.get("avg_duration", 0)
            dur_str = f"{avg_dur:.1f}s" if avg_dur else "—"
            perf = (
                f"  [green]✅ Completed:[/] {completed}  "
                f"[red]❌ Failed:[/] {stats.get('failed_runs', 0)}  "
                f"[cyan]📊 Success Rate:[/] {rate}  "
                f"[yellow]⏱  Avg Duration:[/] {dur_str}"
            )
            self.query_one("#perf-panel", Static).update(perf)

        # Recent runs table
        with contextlib.suppress(NoMatches):
            t = self.query_one("#recent-runs", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("Run ID", "Pipeline", "Status", "Duration", "Started")
            for r in runs:
                st = r.get("status", "—")
                ico = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(st, "❓")
                dur = r.get("duration")
                ds = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "—"
                t.add_row(
                    r.get("run_id", "—")[:12],
                    (r.get("pipeline_name") or "—")[:25],
                    f"{ico} {st}",
                    ds,
                    (r.get("start_time") or "—")[:19],
                    key=r.get("run_id"),
                )

    # ══════════════════════════════════════════════════════════════════
    # RUNS
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_all_runs(self) -> None:
        try:
            runs = _store().list_runs(limit=200)
        except Exception:
            runs = []
        self.call_from_thread(self._apply_all_runs, runs)

    def _apply_all_runs(self, runs):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#all-runs-table", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("Run ID", "Pipeline", "Status", "Duration", "Steps", "Started")
            for r in runs:
                st = r.get("status", "—")
                ico = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(st, "❓")
                dur = r.get("duration")
                ds = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "—"
                steps = r.get("steps") or r.get("step_results") or []
                ns = str(len(steps)) if isinstance(steps, list) else "—"
                t.add_row(
                    r.get("run_id", "—")[:12],
                    (r.get("pipeline_name") or "—")[:25],
                    f"{ico} {st}",
                    ds,
                    ns,
                    (r.get("start_time") or "—")[:19],
                    key=r.get("run_id"),
                )

    @on(DataTable.RowSelected, "#all-runs-table")
    def on_run_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            self.show_run_detail(ev.row_key.value)

    @on(DataTable.RowSelected, "#recent-runs")
    def on_dash_run_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            with contextlib.suppress(NoMatches):
                self.query_one("#tabs", TabbedContent).active = "runs"
            self.show_run_detail(ev.row_key.value)

    @work(thread=True)
    def show_run_detail(self, run_id: str) -> None:
        try:
            run = _store().load_run(run_id)
            if not run:
                self.call_from_thread(self._set_detail, "#detail-panel", "[red]Not found[/]")
                return
            st = run.get("status", "—")
            ico = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(st, "❓")
            lines = [
                f"[bold cyan]Run: {run_id}[/]",
                "",
                f"  [cyan]Pipeline:[/]  {run.get('pipeline_name', '—')}",
                f"  [cyan]Status:[/]    {ico} {st}",
                f"  [cyan]Started:[/]   {run.get('start_time', '—')}",
                f"  [cyan]Ended:[/]     {run.get('end_time', '—')}",
            ]
            dur = run.get("duration")
            if isinstance(dur, (int, float)):
                lines.append(f"  [cyan]Duration:[/]  {dur:.2f}s")

            steps = run.get("steps") or run.get("step_results") or []
            if isinstance(steps, list) and steps:
                lines.append(f"\n[bold yellow]  📋 Steps ({len(steps)}):[/]")
                for s in steps:
                    if isinstance(s, dict):
                        sn = s.get("step_name") or s.get("name", "—")
                        ss = s.get("status", "—")
                        si = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(ss, "❓")
                        sd = s.get("duration")
                        sds = f" ({sd:.2f}s)" if isinstance(sd, (int, float)) else ""
                        lines.append(f"    {si} {sn}{sds}")

            metrics = run.get("metrics") or {}
            if metrics:
                lines.append("\n[bold green]  📊 Metrics:[/]")
                for k, v in sorted(metrics.items()):
                    lines.append(
                        f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}",
                    )

            params = run.get("parameters") or {}
            if params:
                lines.append("\n[bold magenta]  ⚙  Parameters:[/]")
                for k, v in sorted(params.items()):
                    lines.append(f"    {k}: {v}")

            text = "\n".join(lines)
        except Exception as e:
            text = f"[red]Error: {e}[/]"
        self.call_from_thread(self._set_detail, "#detail-panel", text)

    # ══════════════════════════════════════════════════════════════════
    # EXPERIMENTS
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_experiments(self) -> None:
        try:
            exps = _store().list_experiments()
        except Exception:
            exps = []
        self.call_from_thread(self._apply_experiments, exps)

    def _apply_experiments(self, exps):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#exp-table", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("ID", "Name", "Runs", "Project", "Created")
            for e in exps:
                t.add_row(
                    e.get("experiment_id", "—")[:12],
                    (e.get("name") or "—")[:30],
                    str(e.get("run_count", 0)),
                    (e.get("project") or "—")[:15],
                    (e.get("created_at") or "—")[:19],
                    key=e.get("experiment_id"),
                )

    @on(DataTable.RowSelected, "#exp-table")
    def on_exp_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            self.show_exp_runs(ev.row_key.value)

    @work(thread=True)
    def show_exp_runs(self, exp_id: str) -> None:
        try:
            runs = _store().list_experiment_runs(exp_id)
        except Exception:
            runs = []
        self.call_from_thread(self._apply_exp_runs, runs)

    def _apply_exp_runs(self, runs):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#exp-runs-table", DataTable)
            t.clear(columns=True)
            t.add_columns("Run ID", "Metrics", "Parameters", "Created")
            for r in runs:
                metrics = r.get("metrics") or {}
                m_str = (
                    ", ".join(
                        f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in list(metrics.items())[:3]
                    )
                    or "—"
                )
                params = r.get("parameters") or {}
                p_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3]) or "—"
                t.add_row(
                    r.get("run_id", "—")[:12],
                    m_str[:40],
                    p_str[:40],
                    (r.get("created_at") or "—")[:19],
                )

    # ══════════════════════════════════════════════════════════════════
    # MODELS
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_models(self) -> None:
        try:
            versions = _store().list_model_versions()
        except Exception:
            versions = []
        self.call_from_thread(self._apply_models, versions)

    def _apply_models(self, versions):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#models-table", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("Model", "Version", "Stage", "Framework", "Created")
            stage_icons = {
                "development": "🔧",
                "staging": "🧪",
                "production": "✅",
                "archived": "📦",
            }
            for v in versions:
                stage = v.get("stage", "—")
                ico = stage_icons.get(stage, "📌")
                t.add_row(
                    (v.get("name") or "—")[:20],
                    v.get("version", "—"),
                    f"{ico} {stage}",
                    v.get("framework", "—"),
                    (v.get("created_at") or "—")[:19],
                    key=f"{v.get('name')}:{v.get('version')}",
                )

    @on(DataTable.RowSelected, "#models-table")
    def on_model_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            self.show_model_detail(ev.row_key.value)

    @work(thread=True)
    def show_model_detail(self, key: str) -> None:
        try:
            name, version = key.split(":", 1)
            v = _store().get_model_version(name, version)
            if not v:
                self.call_from_thread(self._set_detail, "#model-detail", "[red]Not found[/]")
                return
            stage_icons = {
                "development": "🔧",
                "staging": "🧪",
                "production": "✅",
                "archived": "📦",
            }
            ico = stage_icons.get(v.get("stage", ""), "📌")
            lines = [
                f"[bold cyan]📦 {name} v{version}[/]",
                "",
                f"  [cyan]Stage:[/]      {ico} {v.get('stage', '—')}",
                f"  [cyan]Framework:[/]  {v.get('framework', '—')}",
                f"  [cyan]Path:[/]       {v.get('model_path', '—')}",
                f"  [cyan]Author:[/]     {v.get('author') or '—'}",
                f"  [cyan]Created:[/]    {v.get('created_at', '—')}",
            ]
            if v.get("description"):
                lines.append(f"  [cyan]Desc:[/]       {v['description']}")
            metrics = v.get("metrics") or {}
            if metrics:
                lines.append("\n[bold green]  📊 Metrics:[/]")
                for k, val in sorted(metrics.items()):
                    lines.append(
                        f"    {k}: {val:.6f}" if isinstance(val, float) else f"    {k}: {val}",
                    )
            tags = v.get("tags") or {}
            if tags:
                lines.append("\n[bold yellow]  🏷  Tags:[/]")
                for k, val in sorted(tags.items()):
                    lines.append(f"    {k}: {val}")
            text = "\n".join(lines)
        except Exception as e:
            text = f"[red]Error: {e}[/]"
        self.call_from_thread(self._set_detail, "#model-detail", text)

    # ══════════════════════════════════════════════════════════════════
    # PIPELINES
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_pipelines(self) -> None:
        try:
            s = _store()
            names = s.list_pipelines()
            from sqlalchemy import func, select

            pipe_data = []
            with s.engine.connect() as conn:
                for name in names:
                    cnt = (
                        conn.execute(
                            select(func.count()).select_from(s.runs).where(s.runs.c.pipeline_name == name),
                        ).scalar()
                        or 0
                    )
                    avg = (
                        conn.execute(
                            select(func.avg(s.runs.c.duration)).where(
                                (s.runs.c.pipeline_name == name) & (s.runs.c.duration.isnot(None)),
                            ),
                        ).scalar()
                        or 0
                    )
                    pipe_data.append(
                        {
                            "name": name,
                            "runs": cnt,
                            "avg_dur": avg,
                        },
                    )
        except Exception:
            pipe_data = []
        self.call_from_thread(self._apply_pipelines, pipe_data)

    def _apply_pipelines(self, pipes):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#pipes-table", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("Pipeline", "Runs", "Avg Duration")
            for p in pipes:
                avg = p.get("avg_dur", 0)
                ds = f"{avg:.1f}s" if avg else "—"
                t.add_row(
                    (p["name"] or "—")[:40],
                    str(p.get("runs", 0)),
                    ds,
                    key=p["name"],
                )

    @on(DataTable.RowSelected, "#pipes-table")
    def on_pipe_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            self.show_pipe_detail(ev.row_key.value)

    @work(thread=True)
    def show_pipe_detail(self, name: str) -> None:
        try:
            defn = _store().get_pipeline_definition(name)
            if defn:
                text = f"[bold cyan]🔀 Pipeline: {name}[/]\n\n" f"[green]{json.dumps(defn, indent=2, default=str)}[/]"
            else:
                text = (
                    f"[bold cyan]🔀 Pipeline: {name}[/]\n\n"
                    "[dim]No stored definition — "
                    "pipeline is known only from run history.[/]"
                )
        except Exception as e:
            text = f"[red]Error: {e}[/]"
        self.call_from_thread(self._set_detail, "#pipe-detail", text)

    # ══════════════════════════════════════════════════════════════════
    # TRACES
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_traces(self) -> None:
        try:
            traces = _store().list_traces(limit=100)
        except Exception:
            traces = []
        self.call_from_thread(self._apply_traces, traces)

    def _apply_traces(self, traces):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#traces-table", DataTable)
            t.clear(columns=True)
            t.cursor_type = "row"
            t.add_columns("Trace ID", "Type", "Name", "Model", "Tokens", "Cost", "Duration", "Status")
            for tr in traces:
                tokens = tr.get("total_tokens")
                tok_s = str(tokens) if tokens else "—"
                cost = tr.get("cost")
                cost_s = f"${cost:.4f}" if cost else "—"
                dur = tr.get("duration")
                dur_s = f"{dur:.2f}s" if isinstance(dur, (int, float)) else "—"
                st = tr.get("status", "—")
                ico = {"completed": "✅", "error": "❌"}.get(st, "❓")
                t.add_row(
                    (tr.get("trace_id") or "—")[:12],
                    tr.get("event_type", "—"),
                    (tr.get("name") or "—")[:25],
                    (tr.get("model") or "—")[:15],
                    tok_s,
                    cost_s,
                    dur_s,
                    f"{ico} {st}",
                    key=tr.get("trace_id"),
                )

    @on(DataTable.RowSelected, "#traces-table")
    def on_trace_selected(self, ev: DataTable.RowSelected) -> None:
        if ev.row_key and ev.row_key.value:
            self.show_trace_detail(ev.row_key.value)

    @work(thread=True)
    def show_trace_detail(self, trace_id: str) -> None:
        try:
            events = _store().get_trace(trace_id)
            if not events:
                self.call_from_thread(self._set_detail, "#trace-detail", "[red]No events found[/]")
                return
            lines = [f"[bold cyan]🔍 Trace: {trace_id}[/]", f"  Events: {len(events)}", ""]
            total_tokens, total_cost = 0, 0.0
            for ev in events:
                st = ev.get("status", "—")
                ico = {"completed": "✅", "error": "❌"}.get(st, "❓")
                dur = ev.get("duration")
                ds = f" ({dur:.2f}s)" if isinstance(dur, (int, float)) else ""
                lines.append(
                    f"  {ico} [{ev.get('event_type', '—')}] " f"{ev.get('name', '—')}{ds}",
                )
                if ev.get("model"):
                    lines.append(f"      Model: {ev['model']}")
                tok = ev.get("total_tokens")
                if tok:
                    total_tokens += tok
                    lines.append(
                        f"      Tokens: {ev.get('prompt_tokens', 0)} → "
                        f"{ev.get('completion_tokens', 0)} "
                        f"(total: {tok})",
                    )
                c = ev.get("cost")
                if c:
                    total_cost += c
                    lines.append(f"      Cost: ${c:.4f}")
                if ev.get("error"):
                    lines.append(f"      [red]Error: " f"{json.dumps(ev['error'], default=str)[:80]}[/]")
                lines.append("")
            if total_tokens or total_cost:
                lines.append("[bold green]  📊 Totals:[/]")
                if total_tokens:
                    lines.append(f"    Total Tokens: {total_tokens}")
                if total_cost:
                    lines.append(f"    Total Cost: ${total_cost:.4f}")
            text = "\n".join(lines)
        except Exception as e:
            text = f"[red]Error: {e}[/]"
        self.call_from_thread(self._set_detail, "#trace-detail", text)

    # ══════════════════════════════════════════════════════════════════
    # DATABASE
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_db_stats(self) -> None:
        counts = _table_counts()
        db_size = _db_size_str()
        self.call_from_thread(self._apply_db_stats, counts, db_size)

    def _apply_db_stats(self, counts, db_size):
        with contextlib.suppress(NoMatches):
            t = self.query_one("#db-stats-table", DataTable)
            t.clear(columns=True)
            t.add_columns("Table", "Rows", "Status")
            total = 0
            for name, cnt in sorted(counts.items()):
                t.add_row(name, str(cnt), "🟢" if cnt > 0 else "⚪")
                total += cnt
            t.add_row("─" * 25, "─" * 8, "──")
            t.add_row("[bold]TOTAL[/]", f"[bold]{total}[/]", f"📁 {db_size}")

    # Purge handlers
    @on(Button.Pressed, "#purge-runs")
    def purge_runs(self) -> None:
        self._confirm_purge("runs")

    @on(Button.Pressed, "#purge-traces")
    def purge_traces(self) -> None:
        self._confirm_purge("traces")

    @on(Button.Pressed, "#purge-artifacts")
    def purge_artifacts(self) -> None:
        self._confirm_purge("artifacts")

    @on(Button.Pressed, "#purge-metrics")
    def purge_metrics(self) -> None:
        self._confirm_purge("metrics")

    @on(Button.Pressed, "#purge-models")
    def purge_models(self) -> None:
        self._confirm_purge("model_versions")

    @on(Button.Pressed, "#purge-experiments")
    def purge_experiments(self) -> None:
        self._confirm_purge("experiments")

    @on(Button.Pressed, "#purge-all")
    def purge_all(self) -> None:
        self._confirm_purge("ALL")

    def _confirm_purge(self, table_name: str) -> None:
        def cb(result: bool) -> None:
            if result:
                self._do_purge(table_name)

        self.push_screen(ConfirmPurgeScreen(table_name), callback=cb)

    @work(thread=True)
    def _do_purge(self, table_name: str) -> None:
        try:
            s = _store()
            from sqlalchemy import delete as sa_delete

            tbls = {
                "runs": s.runs,
                "artifacts": s.artifacts,
                "metrics": s.metrics,
                "model_metrics": s.model_metrics,
                "parameters": s.parameters,
                "experiments": s.experiments,
                "experiment_runs": s.experiment_runs,
                "traces": s.traces,
                "pipeline_definitions": s.pipeline_definitions,
                "projects": s.projects,
                "model_versions": s.model_versions,
                "pipeline_templates": s.pipeline_templates,
            }
            with s.engine.connect() as conn:
                if table_name == "ALL":
                    total = 0
                    for n in [
                        "experiment_runs",
                        "metrics",
                        "model_metrics",
                        "parameters",
                        "artifacts",
                        "traces",
                        "pipeline_templates",
                        "pipeline_definitions",
                        "model_versions",
                        "experiments",
                        "projects",
                        "runs",
                    ]:
                        t = tbls.get(n)
                        if t is not None:
                            total += conn.execute(sa_delete(t)).rowcount
                    conn.commit()
                    msg = f"[green]✅ Purged ALL — {total} rows[/]"
                else:
                    t = tbls.get(table_name)
                    if t is not None:
                        if table_name == "runs":
                            for dep in ["experiment_runs", "metrics", "parameters", "artifacts"]:
                                conn.execute(sa_delete(tbls[dep]))
                        elif table_name == "experiments":
                            conn.execute(sa_delete(tbls["experiment_runs"]))
                        r = conn.execute(sa_delete(t))
                        conn.commit()
                        msg = f"[green]✅ Purged '{table_name}' — " f"{r.rowcount} rows[/]"
                    else:
                        msg = f"[red]Unknown table: {table_name}[/]"
            self.call_from_thread(self._show_purge_msg, msg)
            self._refresh_all()
        except Exception as e:
            self.call_from_thread(self._show_purge_msg, f"[red]Error: {e}[/]")

    def _show_purge_msg(self, msg: str) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#purge-result", Label).update(msg)
        clean = msg.replace("[green]", "").replace("[/]", "").replace("[red]", "")
        self.notify(clean)

    # ══════════════════════════════════════════════════════════════════
    # CONFIG
    # ══════════════════════════════════════════════════════════════════
    @work(thread=True)
    def load_config(self) -> None:
        try:
            from flowyml.utils.config import get_config

            cfg = get_config()
            lines = [
                "[bold cyan]🌊 FlowyML Configuration[/]\n",
                f"  [cyan]Home:[/]          {cfg.flowyml_home}",
                f"  [cyan]Artifacts:[/]     {cfg.artifacts_dir}",
                f"  [cyan]Metadata DB:[/]   {cfg.metadata_db}",
                f"  [cyan]Default Stack:[/] {cfg.default_stack}",
                f"  [cyan]Exec Mode:[/]     {cfg.execution_mode}",
                f"  [cyan]Caching:[/]       {cfg.enable_caching}",
                f"  [cyan]Log Level:[/]     {cfg.log_level}",
                f"  [cyan]UI Port:[/]       {cfg.ui_port}",
                f"  [cyan]Debug:[/]         {cfg.debug_mode}",
            ]
            if cfg.execution_mode == "remote":
                lines.append(f"  [cyan]Server URL:[/]   {cfg.remote_server_url}")
                lines.append(f"  [cyan]UI URL:[/]       {cfg.remote_ui_url}")

            # Stack info
            try:
                from flowyml.utils.stack_config import StackManager

                sm = StackManager()
                active = sm.active_stack_name
                stacks = sm.list_stacks()
                lines.append("\n[bold cyan]🏗  Stack Configuration[/]\n")
                lines.append(f"  [cyan]Active Stack:[/]  {active}")
                lines.append(f"  [cyan]Stacks:[/]        {len(stacks)}")
                for s_name in stacks:
                    marker = " ← active" if s_name == active else ""
                    lines.append(f"    • {s_name}{marker}")
            except Exception:
                pass

            text = "\n".join(lines)
        except Exception as e:
            text = f"[red]Error loading config: {e}[/]"
        self.call_from_thread(self._set_detail, "#config-panel", text)

    # ══════════════════════════════════════════════════════════════════
    # SHARED HELPERS
    # ══════════════════════════════════════════════════════════════════
    def _set_detail(self, selector: str, text: str) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one(selector, Static).update(text)

    # ── Refresh buttons ──────────────────────────────────────────────
    @on(Button.Pressed, "#btn-refresh-runs")
    def _r_runs(self) -> None:
        self.load_all_runs()
        self.notify("Runs refreshed ↻")

    @on(Button.Pressed, "#btn-refresh-exp")
    def _r_exp(self) -> None:
        self.load_experiments()
        self.notify("Experiments refreshed ↻")

    @on(Button.Pressed, "#btn-refresh-models")
    def _r_models(self) -> None:
        self.load_models()
        self.notify("Models refreshed ↻")

    @on(Button.Pressed, "#btn-refresh-pipes")
    def _r_pipes(self) -> None:
        self.load_pipelines()
        self.notify("Pipelines refreshed ↻")

    @on(Button.Pressed, "#btn-refresh-traces")
    def _r_traces(self) -> None:
        self.load_traces()
        self.notify("Traces refreshed ↻")


def launch_tui() -> None:
    """Entry point for ``flowyml tui``."""
    FlowyMLApp().run()
