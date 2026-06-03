"""Custom exception hierarchy for the Enterprise Stack Registry.

All exceptions inherit from ``StackError`` and provide rich, human-readable
error messages that explain *what* went wrong, *why* it matters, and *how*
to fix it.
"""

from __future__ import annotations


class StackError(Exception):
    """Base exception for all enterprise stack errors."""

    def __init__(self, message: str, *, details: str | None = None, suggestion: str | None = None):
        self.details = details
        self.suggestion = suggestion
        full = message
        if details:
            full += f"\n\nDetails:\n  {details}"
        if suggestion:
            full += f"\n\nSuggested fix:\n  {suggestion}"
        super().__init__(full)


class StackNotFoundError(StackError):
    """Raised when a stack definition cannot be found."""

    def __init__(
        self,
        stack_name: str,
        *,
        source: str | None = None,
        available: list[str] | None = None,
    ):
        self.stack_name = stack_name
        self.source = source
        self.available = available

        msg = f"Stack '{stack_name}' not found"
        if source:
            msg += f" in source: {source}"

        details = None
        suggestion = None

        if available:
            suggestion = f"Available stacks: {', '.join(available)}"
        else:
            suggestion = (
                "Check your flowyml.yaml registry.sources configuration, "
                "or use 'flowyml stack list' to see available stacks."
            )

        super().__init__(msg, details=details, suggestion=suggestion)


class StackValidationError(StackError):
    """Raised when a stack definition fails validation.

    Provides the field path, why it matters, and a suggested fix.
    """

    def __init__(
        self,
        stack_name: str,
        *,
        field: str | None = None,
        reason: str | None = None,
        suggestion: str | None = None,
    ):
        self.stack_name = stack_name
        self.field = field
        self.reason = reason

        msg = f"Invalid stack definition: {stack_name}"

        details_parts = []
        if field:
            details_parts.append(f"Missing or invalid field:\n    {field}")
        if reason:
            details_parts.append(f"Why it matters:\n    {reason}")

        details = "\n\n  ".join(details_parts) if details_parts else None

        super().__init__(msg, details=details, suggestion=suggestion)


class StackSourceError(StackError):
    """Raised when a stack source cannot be loaded or accessed."""

    def __init__(
        self,
        source_uri: str,
        *,
        reason: str | None = None,
        suggestion: str | None = None,
    ):
        self.source_uri = source_uri

        msg = f"Failed to load stack source: {source_uri}"

        if not suggestion:
            suggestion = (
                "Verify the source URI is correct and accessible. "
                "For Git sources, ensure the repository and ref exist."
            )

        super().__init__(msg, details=reason, suggestion=suggestion)


class StackLockError(StackError):
    """Raised when stack locking or verification fails."""

    def __init__(
        self,
        message: str,
        *,
        stack_name: str | None = None,
        expected_digest: str | None = None,
        actual_digest: str | None = None,
    ):
        self.stack_name = stack_name
        self.expected_digest = expected_digest
        self.actual_digest = actual_digest

        details = None
        suggestion = None

        if expected_digest and actual_digest:
            details = f"Expected digest: {expected_digest}\n" f"  Actual digest:   {actual_digest}"
            suggestion = (
                f"The stack '{stack_name}' has changed since it was locked. "
                f"Run 'flowyml stack update --stack {stack_name}' to update the lock file, "
                f"or 'flowyml stack lock --stack {stack_name}' to re-lock."
            )

        super().__init__(message, details=details, suggestion=suggestion)


class PolicyViolationError(StackError):
    """Raised when a policy check fails before execution.

    Includes the rule name, what failed, and a human-readable suggestion.
    """

    def __init__(
        self,
        message: str,
        *,
        rule_name: str | None = None,
        violations: list[str] | None = None,
    ):
        self.rule_name = rule_name
        self.violations = violations or []

        details = None
        if violations:
            details = "Violations:\n" + "\n".join(f"  • {v}" for v in violations)

        suggestion = (
            "Review the stack's policy configuration or contact the platform team "
            "to request an exception or a new approved stack."
        )

        super().__init__(message, details=details, suggestion=suggestion)


class StackSecurityError(StackError):
    """Raised when a security check fails (e.g., signature verification)."""

    def __init__(
        self,
        message: str,
        *,
        stack_name: str | None = None,
        suggestion: str | None = None,
    ):
        self.stack_name = stack_name

        if not suggestion:
            suggestion = (
                "Ensure the stack definition is signed by a trusted key. "
                "Contact the platform team if you believe this is an error."
            )

        super().__init__(message, suggestion=suggestion)
