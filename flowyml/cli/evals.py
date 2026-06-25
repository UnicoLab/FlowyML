"""FlowyML Evaluations — CLI Commands.

Adds the `flowyml eval` command group with subcommands for running,
listing, comparing evaluations, and managing scorers.
"""

import json
import logging

import rich_click as click
from flowyml.cli.rich_utils import recho

logger = logging.getLogger(__name__)


@click.group("eval")
def eval_cli():
    """📊 Evaluation commands — run, compare, and manage evaluations."""
    pass


@eval_cli.command("run")
@click.option("--data", "-d", required=True, help="Path to evaluation data (CSV or JSON)")
@click.option(
    "--scorers",
    "-s",
    multiple=True,
    help="Scorer names to use (e.g., --scorers accuracy --scorers f1_score)",
)
@click.option("--experiment", "-e", default=None, help="Experiment name for tracking")
@click.option("--threshold", "-t", type=float, default=None, help="Pass/fail threshold")
@click.option("--output", "-o", default=None, help="Output file for results (JSON)")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "summary"]),
    default="table",
    help="Output format",
)
def run_eval(data, scorers, experiment, threshold, output, fmt):
    """Run evaluations on a dataset with specified scorers.

    Examples:
        flowyml eval run -d test_data.csv -s accuracy -s f1_score

        flowyml eval run -d genai_data.json -s relevance -s toxicity -e my_exp
    """
    from flowyml.evals import evaluate, EvalDataset, get_scorer

    # Load data
    if data.endswith(".csv"):
        eval_ds = EvalDataset.from_csv(data)
    elif data.endswith(".json"):
        with open(data) as f:
            raw_data = json.load(f)
        if isinstance(raw_data, list):
            eval_ds = EvalDataset.create_genai(name="cli_dataset", examples=raw_data)
        else:
            eval_ds = EvalDataset(name="cli_dataset", data=raw_data)
    else:
        recho(f"[red]❌Unsupported data format: {data}. Use .csv or .json")
        raise SystemExit(1)

    # Build scorers
    scorer_list = []
    for s_name in scorers:
        try:
            scorer = get_scorer(s_name, threshold=threshold)
            scorer_list.append(scorer)
        except ValueError as e:
            recho(f"[red]❌{e}")
            raise SystemExit(1)

    if not scorer_list:
        recho("[red]❌No scorers specified. Use --scorers <name>")
        raise SystemExit(1)

    recho(f"🔄 Running {len(scorer_list)} scorer(s) on {eval_ds.num_examples} examples...")

    # Run evaluation
    result = evaluate(
        data=eval_ds,
        scorers=scorer_list,
        experiment=experiment,
        store=True,
    )

    # Display results
    if fmt == "json":
        recho(json.dumps(result.to_dict(), indent=2, default=str))
    elif fmt == "summary":
        recho(f"\n📊 Evaluation Summary (ID: {result.eval_id[:8]})")
        recho(f"   Dataset: {result.dataset_name} ({eval_ds.num_examples} examples)")
        recho(f"   Passed: {'✅' if result.passed else '❌'}")
        recho(f"   Pass Rate: {result.pass_rate:.1%}")
        recho("\n   Scores:")
        for name, value in result.summary.items():
            status = "✅" if result.scores.get(name, [{}])[0].passed is not False else "❌"
            recho(f"   {status} {name}: {value:.4f}")
    else:
        # Table format
        recho(f"\n{'─' * 60}")
        recho(f"  📊 Evaluation Results  |  ID: {result.eval_id[:8]}")
        recho(f"{'─' * 60}")
        recho(f"  {'Scorer':<25} {'Score':>10} {'Status':>8}")
        recho(f"  {'─' * 45}")
        for name, value in result.summary.items():
            feedbacks = result.scores.get(name, [])
            passed = feedbacks[0].passed if feedbacks else None
            status = "✅" if passed is True else ("❌" if passed is False else "—")
            recho(f"  {name:<25} {value:>10.4f} {status:>8}")
        recho(f"{'─' * 60}")
        recho(
            f"  Overall: {'✅ PASSED' if result.passed else '❌ FAILED'}  |  Pass Rate: {result.pass_rate:.1%}",
        )
        recho(f"{'─' * 60}")

    # Save output
    if output:
        with open(output, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        recho(f"\n💾 Results saved to {output}")


@eval_cli.command("list")
@click.option("--experiment", "-e", default=None, help="Filter by experiment name")
@click.option("--limit", "-n", type=int, default=20, help="Max results to show")
def list_evals(experiment, limit):
    """List recent evaluation runs.

    Examples:
        flowyml eval list

        flowyml eval list -e my_experiment -n 10
    """
    recho("📋 Recent Evaluation Runs")
    recho(f"{'─' * 70}")
    recho(f"  {'ID':<10} {'Experiment':<20} {'Status':<12} {'Scorers':<20} {'Date'}")
    recho(f"  {'─' * 65}")

    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        runs = store.list_runs(limit=limit)

        eval_runs = [r for r in runs if r.get("tags", {}).get("type") == "evaluation"]
        if experiment:
            eval_runs = [r for r in eval_runs if experiment in r.get("pipeline_name", "")]

        if not eval_runs:
            recho("  No evaluation runs found.")
        else:
            for run in eval_runs[:limit]:
                run_id = run.get("run_id", "")[:8]
                exp = run.get("pipeline_name", "—")[:18]
                status = run.get("status", "—")
                scorer_names = run.get("parameters", {}).get("scorer_names", [])
                scorers_str = ", ".join(scorer_names[:3])
                if len(scorer_names) > 3:
                    scorers_str += f" +{len(scorer_names) - 3}"
                date = run.get("start_time", "—")[:16]
                recho(f"  {run_id:<10} {exp:<20} {status:<12} {scorers_str:<20} {date}")

    except Exception as e:
        recho(f"  ⚠️ Could not load runs: {e}")

    recho(f"{'─' * 70}")


@eval_cli.command("show")
@click.argument("eval_id")
def show_eval(eval_id):
    """Show detailed results for an evaluation run.

    Examples:
        flowyml eval show abc12345
    """
    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        run = store.load_run(eval_id)
        if not run:
            recho(f"[red]❌Evaluation '{eval_id}' not found")
            raise SystemExit(1)

        recho(f"\n📊 Evaluation: {eval_id}")
        recho(json.dumps(run, indent=2, default=str))

    except SystemExit:
        raise
    except Exception as e:
        recho(f"[red]❌Error: {e}")


@eval_cli.command("compare")
@click.argument("eval_ids", nargs=-1)
@click.option("--threshold", "-t", type=float, default=0.05, help="Regression threshold")
def compare_evals(eval_ids, threshold):
    """Compare two or more evaluation runs.

    Examples:
        flowyml eval compare abc12345 def67890
    """
    if len(eval_ids) < 2:
        recho("[red]❌Need at least 2 evaluation IDs to compare")
        raise SystemExit(1)

    recho(f"\n📊 Comparing {len(eval_ids)} Evaluations")
    recho(f"{'─' * 70}")

    try:
        from flowyml.storage.sql import SQLMetadataStore

        store = SQLMetadataStore()
        runs = []
        for eid in eval_ids:
            run = store.load_run(eid)
            if run:
                runs.append(run)
            else:
                recho(f"  ⚠️ Could not load: {eid}")

        if len(runs) >= 2:
            metrics_a = runs[0].get("metrics", {})
            metrics_b = runs[1].get("metrics", {})
            all_metrics = set(metrics_a.keys()) | set(metrics_b.keys())

            recho(
                f"  {'Metric':<20} {eval_ids[0][:8]:>10} {eval_ids[1][:8]:>10} {'Delta':>10} {'Status':>8}",
            )
            recho(f"  {'─' * 60}")

            for metric in sorted(all_metrics):
                val_a = metrics_a.get(metric, "—")
                val_b = metrics_b.get(metric, "—")
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    delta = val_a - val_b
                    status = "⬆️" if delta > threshold else ("⬇️" if delta < -threshold else "➡️")
                    recho(
                        f"  {metric:<20} {val_a:>10.4f} {val_b:>10.4f} {delta:>+10.4f} {status}",
                    )
                else:
                    recho(f"  {metric:<20} {str(val_a):>10} {str(val_b):>10}")

    except Exception as e:
        recho(f"[red]❌Error: {e}")

    recho(f"{'─' * 70}")


@eval_cli.command("scorers")
@click.option(
    "--type",
    "scorer_type",
    default=None,
    help="Filter by type (classification, regression, genai)",
)
def list_available_scorers(scorer_type):
    """List all available scorers.

    Examples:
        flowyml eval scorers

        flowyml eval scorers --type classification
    """
    from flowyml.evals.scorers import list_scorers

    scorers = list_scorers(scorer_type)

    recho("\n🎯 Available Scorers")
    if scorer_type:
        recho(f"   (filtered: {scorer_type})")
    recho(f"{'─' * 70}")
    recho(f"  {'Name':<25} {'Type':<18} {'Description'}")
    recho(f"  {'─' * 65}")

    for s in scorers:
        recho(f"  {s['name']:<25} {s['type']:<18} {s['description'][:30]}")

    recho(f"{'─' * 70}")
    recho(f"  Total: {len(scorers)} scorer(s)")


@eval_cli.command("assert")
@click.option("--data", "-d", required=True, help="Path to evaluation data")
@click.option("--scorers", "-s", multiple=True, required=True, help="Scorer names")
@click.option(
    "--min-score",
    type=(str, float),
    multiple=True,
    help="Min score assertion: --min-score accuracy 0.9",
)
@click.option(
    "--max-score",
    type=(str, float),
    multiple=True,
    help="Max score assertion: --max-score toxicity 0.3",
)
@click.option("--pass-rate", type=float, default=None, help="Min pass rate (0.0-1.0)")
@click.option("--fail-on-error", is_flag=True, help="Exit with code 1 on assertion failure")
def assert_eval(data, scorers, min_score, max_score, pass_rate, fail_on_error):
    r"""Run evaluations with CI/CD assertions.

    Examples:
        flowyml eval assert -d test.csv -s accuracy -s f1_score \\
            --min-score accuracy 0.9 --min-score f1_score 0.85 \\
            --pass-rate 0.95 --fail-on-error
    """
    from flowyml.evals import evaluate, EvalDataset, EvalAssert, get_scorer

    # Load data
    if data.endswith(".csv"):
        eval_ds = EvalDataset.from_csv(data)
    elif data.endswith(".json"):
        with open(data) as f:
            raw_data = json.load(f)
        if isinstance(raw_data, list):
            eval_ds = EvalDataset.create_genai(name="assert_dataset", examples=raw_data)
        else:
            eval_ds = EvalDataset(name="assert_dataset", data=raw_data)
    else:
        recho(f"[red]❌Unsupported data format: {data}")
        raise SystemExit(1)

    # Build scorers
    scorer_list = []
    for s_name in scorers:
        try:
            scorer_list.append(get_scorer(s_name))
        except ValueError as e:
            recho(f"[red]❌{e}")
            raise SystemExit(1)

    # Run evaluation
    result = evaluate(data=eval_ds, scorers=scorer_list, store=False)

    # Build assertions
    assertions = EvalAssert(result)
    for metric, threshold in min_score:
        assertions.assert_min_score(metric, threshold)
    for metric, threshold in max_score:
        assertions.assert_max_score(metric, threshold)
    if pass_rate is not None:
        assertions.assert_pass_rate(pass_rate)

    # Validate
    try:
        all_passed = assertions.validate(raise_on_failure=False)
    except Exception:
        all_passed = False

    # Display results
    recho(f"\n{'─' * 60}")
    recho("  🔍 Assertion Results")
    recho(f"{'─' * 60}")

    for a in assertions.results:
        status = "✅" if a.passed else "❌"
        recho(f"  {status} {a.name}: {a.message}")

    recho(f"{'─' * 60}")

    if all_passed:
        recho("  ✅ All assertions PASSED")
    else:
        recho("  ❌ Some assertions FAILED")
        if fail_on_error:
            raise SystemExit(1)
