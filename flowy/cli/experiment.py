"""Experiment tracking CLI commands."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json


def list_experiments_cmd(limit: int = 10, pipeline: Optional[str] = None) -> List[Dict[str, Any]]:
    """List experiments.

    Args:
        limit: Maximum number of experiments to return
        pipeline: Filter by pipeline name

    Returns:
        List of experiment dictionaries
    """
    from flowy.tracking.experiment import Experiment

    experiments_dir = Path(".flowy/experiments")

    if not experiments_dir.exists():
        return []

    experiments = []

    for exp_file in experiments_dir.glob("*.json"):
        try:
            with open(exp_file, 'r') as f:
                exp_data = json.load(f)

            # Filter by pipeline if specified
            if pipeline and exp_data.get('pipeline_name') != pipeline:
                continue

            experiments.append(exp_data)
        except:
            continue

    # Sort by created_at
    experiments.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return experiments[:limit]


def compare_runs(run_ids: List[str]) -> str:
    """Compare multiple experiment runs.

    Args:
        run_ids: List of run IDs to compare

    Returns:
        Formatted comparison string
    """
    from flowy.tracking.runs import Run

    runs = []
    for run_id in run_ids:
        run_path = Path(f".flowy/runs/{run_id}.json")
        if run_path.exists():
            run = Run.load(run_path)
            runs.append(run)

    if not runs:
        return "No runs found"

    # Build comparison table
    lines = []
    lines.append("\nRun Comparison:")
    lines.append("-" * 80)

    # Headers
    lines.append(f"{'Metric':<30} " + " ".join(f"{r.id[:8]:>12}" for r in runs))
    lines.append("-" * 80)

    # Get all metric names
    all_metrics = set()
    for run in runs:
        all_metrics.update(run.metadata.metrics.keys())

    # Print metrics
    for metric in sorted(all_metrics):
        values = []
        for run in runs:
            value = run.metadata.metrics.get(metric, '-')
            if isinstance(value, float):
                values.append(f"{value:>12.4f}")
            else:
                values.append(f"{str(value):>12}")

        lines.append(f"{metric:<30} " + " ".join(values))

    lines.append("-" * 80)

    # Get all parameter names
    all_params = set()
    for run in runs:
        all_params.update(run.metadata.parameters.keys())

    if all_params:
        lines.append("\nParameters:")
        lines.append("-" * 80)

        for param in sorted(all_params):
            values = []
            for run in runs:
                value = run.metadata.parameters.get(param, '-')
                values.append(f"{str(value):>12}")

            lines.append(f"{param:<30} " + " ".join(values))

        lines.append("-" * 80)

    # Duration
    lines.append("\nDuration:")
    durations = [f"{r.metadata.duration:>12.2f}s" if r.metadata.duration else f"{'N/A':>12}"
                 for r in runs]
    lines.append(f"{'Time':<30} " + " ".join(durations))

    lines.append("-" * 80)

    return "\n".join(lines)


def export_experiment(run_id: str, format: str = "html") -> str:
    """Export experiment run.

    Args:
        run_id: Run ID to export
        format: Export format (html, json, markdown)

    Returns:
        Path to exported file
    """
    from flowy.tracking.runs import Run

    run_path = Path(f".flowy/runs/{run_id}.json")
    if not run_path.exists():
        raise FileNotFoundError(f"Run {run_id} not found")

    run = Run.load(run_path)

    output_dir = Path(f".flowy/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    if format == "json":
        output_file = output_dir / f"{run_id}.json"
        run.save(output_file)

    elif format == "markdown":
        output_file = output_dir / f"{run_id}.md"
        markdown = generate_markdown_report(run)
        with open(output_file, 'w') as f:
            f.write(markdown)

    elif format == "html":
        output_file = output_dir / f"{run_id}.html"
        html = generate_html_report(run)
        with open(output_file, 'w') as f:
            f.write(html)

    else:
        raise ValueError(f"Unknown format: {format}")

    return str(output_file)


def generate_markdown_report(run) -> str:
    """Generate markdown report for run."""
    lines = []
    lines.append(f"# Run {run.id}")
    lines.append(f"\n**Status:** {run.status}")
    lines.append(f"**Duration:** {run.metadata.duration:.2f}s")
    lines.append(f"**Started:** {run.metadata.start_time}")

    if run.metadata.metrics:
        lines.append("\n## Metrics")
        for key, value in run.metadata.metrics.items():
            lines.append(f"- **{key}:** {value}")

    if run.metadata.parameters:
        lines.append("\n## Parameters")
        for key, value in run.metadata.parameters.items():
            lines.append(f"- **{key}:** {value}")

    return "\n".join(lines)


def generate_html_report(run) -> str:
    """Generate HTML report for run."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Run {run.id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .status {{ font-weight: bold; color: #4CAF50; }}
    </style>
</head>
<body>
    <h1>Run {run.id}</h1>
    <p><strong>Status:</strong> <span class="status">{run.status}</span></p>
    <p><strong>Duration:</strong> {run.metadata.duration:.2f}s</p>
    <p><strong>Started:</strong> {run.metadata.start_time}</p>

    <h2>Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
"""

    for key, value in run.metadata.metrics.items():
        html += f"        <tr><td>{key}</td><td>{value}</td></tr>\n"

    html += """
    </table>

    <h2>Parameters</h2>
    <table>
        <tr><th>Parameter</th><th>Value</th></tr>
"""

    for key, value in run.metadata.parameters.items():
        html += f"        <tr><td>{key}</td><td>{value}</td></tr>\n"

    html += """
    </table>
</body>
</html>
"""
    return html
