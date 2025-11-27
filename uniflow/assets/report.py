"""Report asset for generated reports and visualizations."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from uniflow.assets.base import Asset, AssetMetadata


ReportFormat = Literal["html", "pdf", "markdown", "json"]


@dataclass
class ReportMetadata(AssetMetadata):
    """Metadata specific to Reports."""

    report_format: str = "html"
    title: str | None = None
    author: str | None = None
    generated_at: str | None = None
    file_path: str | None = None
    file_size_bytes: int = 0
    sections: list[str] = field(default_factory=list)


class Report(Asset):
    """Asset representing a generated report.

    Reports can be HTML dashboards, PDF documents, markdown files, or JSON data.

    Example:
        ```python
        from uniflow import Report

        # Create HTML report
        report = Report.create(
            content=html_content,
            name="experiment_report",
            format="html",
            title="Experiment Results",
            sections=["Overview", "Metrics", "Conclusions"],
        )

        # Save to file
        report.save_to_file("reports/experiment_report.html")
        ```
    """

    def __init__(
        self,
        name: str,
        content: Any | None = None,
        report_format: ReportFormat = "html",
        title: str | None = None,
        file_path: str | None = None,
        **kwargs,
    ):
        """Initialize a Report.

        Args:
            name: Name of the report
            content: Report content (string or bytes)
            report_format: Report format
            title: Report title
            file_path: Path to saved report file
            **kwargs: Additional metadata
        """
        # Extract Report-specific arguments before passing to parent
        # report_format is already correct
        report_title = title or name
        report_file_path = file_path

        # Pass only Asset-compatible kwargs to parent
        super().__init__(name=name, **kwargs)

        # Add Report-specific attributes after parent init
        self.metadata.report_format = report_format
        self.metadata.title = report_title
        self.metadata.generated_at = datetime.now().isoformat()
        self.metadata.file_path = report_file_path
        self.metadata.file_size_bytes = 0
        self.metadata.sections = []

        self._content = content

        if content and isinstance(content, (str, bytes)):
            self.metadata.file_size_bytes = len(content)

    @property
    def content(self) -> Any | None:
        """Get report content."""
        return self._content

    @property
    def report_format(self) -> str:
        """Get report format."""
        return self.metadata.report_format

    @property
    def title(self) -> str | None:
        """Get report title."""
        return self.metadata.title

    @property
    def file_path(self) -> str | None:
        """Get file path if saved."""
        return self.metadata.file_path

    @property
    def sections(self) -> list[str]:
        """Get report sections."""
        return self.metadata.sections

    @classmethod
    def create(
        cls,
        content: Any,
        name: str | None = None,
        report_format: ReportFormat = "html",
        title: str | None = None,
        sections: list[str] | None = None,
        **kwargs,
    ) -> "Report":
        """Factory method to create a Report.

        Args:
            content: Report content
            name: Report name (auto-generated if not provided)
            report_format: Report format
            title: Report title
            sections: List of section names
            **kwargs: Additional metadata

        Returns:
            New Report instance
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"report_{timestamp}"

        if sections:
            kwargs["sections"] = sections

        return cls(
            name=name,
            content=content,
            report_format=report_format,
            title=title or name,
            **kwargs,
        )

    def save_to_file(self, path: Path | str) -> Path:
        """Save report content to file.

        Args:
            path: File path to save to

        Returns:
            Path where file was saved

        Raises:
            ValueError: If report has no content
        """
        if self._content is None:
            raise ValueError("Cannot save report with no content")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        if isinstance(self._content, bytes):
            with open(path, "wb") as f:
                f.write(self._content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(self._content))

        # Update metadata
        self.metadata.file_path = str(path)
        self.metadata.file_size_bytes = path.stat().st_size

        return path

    @classmethod
    def load_from_file(cls, path: Path | str, name: str | None = None) -> "Report":
        """Load report from file.

        Args:
            path: File path to load from
            name: Report name (uses filename if not provided)

        Returns:
            Report instance

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Report file not found: {path}")

        # Detect format from extension
        format_map = {
            ".html": "html",
            ".htm": "html",
            ".pdf": "pdf",
            ".md": "markdown",
            ".markdown": "markdown",
            ".json": "json",
        }
        report_format = format_map.get(path.suffix.lower(), "html")

        # Read content
        if report_format == "pdf":
            with open(path, "rb") as f:
                content = f.read()
        else:
            with open(path, encoding="utf-8") as f:
                content = f.read()

        # Use filename as name if not provided
        if name is None:
            name = path.stem

        return cls(
            name=name,
            content=content,
            report_format=report_format,
            file_path=str(path),
        )

    def to_html(self) -> str:
        """Convert report to HTML string.

        Returns:
            HTML content
        """
        if self.report_format == "html":
            return str(self._content)

        elif self.report_format == "markdown":
            try:
                import markdown

                return markdown.markdown(str(self._content))
            except ImportError:
                # Fallback: wrap in pre tags
                return f"<html><body><pre>{self._content}</pre></body></html>"

        elif self.report_format == "json":
            import json

            data = json.loads(str(self._content))
            # Simple JSON to HTML conversion
            html = "<html><body><pre>"
            html += json.dumps(data, indent=2)
            html += "</pre></body></html>"
            return html

        else:
            return f"<html><body><p>Format {self.report_format} not supported for HTML conversion</p></body></html>"

    def open_in_browser(self) -> None:
        """Open report in web browser.

        Works best with HTML and PDF formats.
        """
        import webbrowser
        import tempfile

        if self.file_path:
            # Open existing file
            webbrowser.open(f"file://{Path(self.file_path).absolute()}")
        else:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode="w" if isinstance(self._content, str) else "wb",
                suffix=f".{self.report_format}",
                delete=False,
            ) as f:
                if isinstance(self._content, bytes):
                    f.write(self._content)
                else:
                    f.write(str(self._content))

                temp_path = f.name

            webbrowser.open(f"file://{Path(temp_path).absolute()}")

    def to_dict(self) -> dict[str, Any]:
        """Convert Report to dictionary.

        Returns:
            Dictionary representation (excluding large content)
        """
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "type": self.metadata.asset_type,
            "report_format": self.report_format,
            "title": self.title,
            "file_path": self.file_path,
            "file_size_bytes": self.metadata.file_size_bytes,
            "sections": self.sections,
            "generated_at": self.metadata.generated_at,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "properties": self.properties,
        }

    def __repr__(self) -> str:
        size_kb = self.metadata.file_size_bytes / 1024 if self.metadata.file_size_bytes else 0
        return f"Report(name='{self.name}', format='{self.report_format}', size={size_kb:.1f}KB, title='{self.title}')"
