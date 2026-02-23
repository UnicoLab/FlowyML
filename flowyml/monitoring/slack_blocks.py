"""Slack Block Kit message builders for rich notifications.

This module provides utilities for building professional-looking Slack messages
using Block Kit components.
"""

from datetime import datetime
from typing import Any


def _get_emoji(level: str) -> str:
    """Get emoji for notification level."""
    return {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "success": "✅",
        "critical": "🚨",
    }.get(level, "📢")


def _get_color(level: str) -> str:
    """Get color for notification level."""
    return {
        "info": "#36a64f",
        "warning": "#ff9900",
        "error": "#ff0000",
        "success": "#2eb886",
        "critical": "#8b0000",
    }.get(level, "#cccccc")


def build_header_block(text: str, emoji: str = "") -> dict:
    """Build a header block."""
    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{emoji} {text}" if emoji else text,
            "emoji": True,
        },
    }


def build_section_block(text: str, accessory: dict | None = None) -> dict:
    """Build a section block with markdown text."""
    block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text,
        },
    }
    if accessory:
        block["accessory"] = accessory
    return block


def build_context_block(elements: list[str]) -> dict:
    """Build a context block with multiple text elements."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": el} for el in elements],
    }


def build_divider() -> dict:
    """Build a divider block."""
    return {"type": "divider"}


def build_fields_section(fields: dict[str, Any]) -> dict:
    """Build a section with multiple fields."""
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f"*{key}*\n{value}"} for key, value in fields.items()],
    }


def build_button_accessory(text: str, url: str, style: str = "primary") -> dict:
    """Build a button accessory."""
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": text, "emoji": True},
        "url": url,
        "style": style,
    }


def build_pipeline_success_message(
    pipeline_name: str,
    run_id: str,
    duration: float,
    metrics: dict[str, float] | None = None,
    ui_url: str | None = None,
) -> dict:
    """Build a rich message for pipeline success."""
    emoji = _get_emoji("success")

    blocks = [
        build_header_block("Pipeline Completed Successfully", emoji),
        build_section_block(f"*{pipeline_name}* finished in `{duration:.2f}s`"),
        build_divider(),
        build_fields_section(
            {
                "Run ID": f"`{run_id[:12]}...`",
                "Duration": f"{duration:.2f} seconds",
                "Status": "✅ Success",
                "Completed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        ),
    ]

    if metrics:
        metrics_text = "\n".join([f"• *{k}*: `{v:.4f}`" for k, v in metrics.items()])
        blocks.append(build_section_block(f"*Metrics:*\n{metrics_text}"))

    if ui_url:
        blocks.append(
            build_section_block(
                "View run details in the FlowyML dashboard:",
                accessory=build_button_accessory("View Run", f"{ui_url}/runs/{run_id}"),
            ),
        )

    blocks.append(
        build_context_block([f"FlowyML | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]),
    )

    return {
        "attachments": [
            {
                "color": _get_color("success"),
                "blocks": blocks,
            },
        ],
    }


def build_pipeline_failure_message(
    pipeline_name: str,
    run_id: str,
    error: str,
    step_name: str | None = None,
    ui_url: str | None = None,
) -> dict:
    """Build a rich message for pipeline failure."""
    emoji = _get_emoji("error")

    blocks = [
        build_header_block("Pipeline Failed", emoji),
        build_section_block(f"*{pipeline_name}* encountered an error"),
        build_divider(),
        build_fields_section(
            {
                "Run ID": f"`{run_id[:12]}...`",
                "Status": "❌ Failed",
                "Failed At": step_name or "Unknown step",
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        ),
        build_section_block(f"*Error:*\n```{error[:500]}```"),
    ]

    if ui_url:
        blocks.append(
            build_section_block(
                "Investigate the failure in the FlowyML dashboard:",
                accessory=build_button_accessory(
                    "View Run",
                    f"{ui_url}/runs/{run_id}",
                    style="danger",
                ),
            ),
        )

    blocks.append(
        build_context_block([f"FlowyML | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]),
    )

    return {
        "attachments": [
            {
                "color": _get_color("error"),
                "blocks": blocks,
            },
        ],
    }


def build_drift_warning_message(
    feature: str,
    psi: float,
    threshold: float = 0.2,
    model_name: str | None = None,
    ui_url: str | None = None,
) -> dict:
    """Build a rich message for data drift detection."""
    emoji = _get_emoji("warning")
    severity = "High" if psi > 0.5 else "Medium" if psi > 0.25 else "Low"

    blocks = [
        build_header_block("Data Drift Detected", emoji),
        build_section_block(
            f"Drift detected in feature *{feature}*" + (f" for model *{model_name}*" if model_name else ""),
        ),
        build_divider(),
        build_fields_section(
            {
                "Feature": feature,
                "PSI Score": f"`{psi:.4f}`",
                "Threshold": f"`{threshold:.2f}`",
                "Severity": f"{'🔴' if severity == 'High' else '🟡' if severity == 'Medium' else '🟢'} {severity}",
            },
        ),
        build_section_block(
            "💡 *Recommended Actions:*\n"
            "• Review recent data pipeline changes\n"
            "• Check for upstream data quality issues\n"
            "• Consider retraining the model if drift persists",
        ),
    ]

    if ui_url:
        blocks.append(
            build_section_block(
                "View drift analysis in the dashboard:",
                accessory=build_button_accessory("View Analysis", f"{ui_url}/monitoring/drift"),
            ),
        )

    blocks.append(
        build_context_block(
            [f"FlowyML Monitoring | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
        ),
    )

    return {
        "attachments": [
            {
                "color": _get_color("warning"),
                "blocks": blocks,
            },
        ],
    }


def build_model_promoted_message(
    model_name: str,
    version: str,
    from_stage: str,
    to_stage: str,
    author: str | None = None,
    metrics: dict[str, float] | None = None,
    ui_url: str | None = None,
) -> dict:
    """Build a rich message for model promotion."""
    emoji = "🚀" if to_stage == "production" else "📦"

    blocks = [
        build_header_block(f"Model Promoted to {to_stage.title()}", emoji),
        build_section_block(f"*{model_name}* version `{version}` has been promoted"),
        build_divider(),
        build_fields_section(
            {
                "Model": model_name,
                "Version": f"`{version}`",
                "Transition": f"{from_stage} → *{to_stage}*",
                "Promoted By": author or "System",
            },
        ),
    ]

    if metrics:
        metrics_text = " | ".join([f"*{k}*: `{v:.4f}`" for k, v in metrics.items()])
        blocks.append(build_context_block([f"Metrics: {metrics_text}"]))

    if ui_url:
        blocks.append(
            build_section_block(
                "View model in registry:",
                accessory=build_button_accessory("View Model", f"{ui_url}/models/{model_name}"),
            ),
        )

    blocks.append(
        build_context_block([f"FlowyML Registry | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]),
    )

    return {
        "attachments": [
            {
                "color": _get_color("success") if to_stage == "production" else _get_color("info"),
                "blocks": blocks,
            },
        ],
    }


def build_simple_message(
    title: str,
    message: str,
    level: str = "info",
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Build a simple notification message."""
    emoji = _get_emoji(level)

    blocks = [
        build_header_block(title, emoji),
        build_section_block(message),
    ]

    if metadata:
        blocks.append(build_divider())
        blocks.append(build_fields_section(metadata))

    blocks.append(
        build_context_block([f"FlowyML | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]),
    )

    return {
        "attachments": [
            {
                "color": _get_color(level),
                "blocks": blocks,
            },
        ],
    }
