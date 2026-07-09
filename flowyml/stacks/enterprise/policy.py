"""Policy validation engine for the Enterprise Stack Registry.

This module implements a pluggable, rule-based policy engine that validates
stack usage against organizational constraints *before* execution begins.
Platform teams define policies in stack definitions; the engine enforces them.

Architecture::

    PolicyContext (stack + user + env metadata)
            ↓
    PolicyEngine.validate(context)
            ↓
    [Rule₁, Rule₂, …, Ruleₙ]  ← built-in + custom rules
            ↓
    list[PolicyResult]          ← pass / fail / warning per rule
            ↓
    PolicyEngine.check(context) ← raises PolicyViolationError on failure

Built-in rules::

    StackExistsRule         – stack definition must be non-None
    StackLockedRule         – lock file required when configured
    UserPermissionRule      – user group membership check
    ProjectPermissionRule   – project name check
    BackendAllowedRule      – backend in supported set
    BaseImageApprovedRule   – custom Docker image policy
    PackageAllowListRule    – pipeline packages vs. allowlist
    PackageDenyListRule     – pipeline packages vs. denylist
    ExternalNetworkRule     – external network access policy
    MaxRuntimeRule          – max runtime enforcement
    CostLimitRule           – estimated cost ceiling
    SignedStackRule         – signature requirement

Example::

    from flowyml.stacks.enterprise.policy import PolicyEngine, PolicyContext

    ctx = PolicyContext(
        stack=stack_def,
        user="alice",
        user_groups=["data-science"],
        project_name="churn-modeling",
        pipeline_packages=["pandas", "scikit-learn"],
    )
    engine = PolicyEngine()
    engine.check(ctx)  # raises PolicyViolationError on failure
"""

from __future__ import annotations

import logging
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from flowyml.stacks.enterprise.exceptions import PolicyViolationError
from flowyml.stacks.enterprise.models import SUPPORTED_BACKENDS, StackDefinition

logger = logging.getLogger(__name__)

__all__ = [
    "PolicyContext",
    "PolicyResult",
    "PolicyRule",
    "PolicyEngine",
    # Built-in rules
    "StackExistsRule",
    "StackLockedRule",
    "UserPermissionRule",
    "ProjectPermissionRule",
    "BackendAllowedRule",
    "BaseImageApprovedRule",
    "PackageAllowListRule",
    "PackageDenyListRule",
    "ExternalNetworkRule",
    "MaxRuntimeRule",
    "CostLimitRule",
    "SignedStackRule",
    "ModelDeployerAllowedRule",
    "ModelRegistryAllowedRule",
]


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class PolicyContext(BaseModel):
    """Contextual information supplied to every policy rule.

    This bundles all the metadata the policy engine needs to evaluate rules:
    the stack definition itself, the current user / project / environment,
    and the set of Python packages the pipeline will use.

    Attributes:
        stack: The resolved stack definition to validate.
        project_name: Name of the FlowyML project (from ``flowyml.yaml``).
        user: Identity of the user requesting execution.
        user_groups: Groups the user belongs to (e.g. AD / LDAP groups).
        environment: Target environment name (``dev``, ``staging``, ``prod``).
        pipeline_packages: Python packages the pipeline imports or installs.
        is_locked: Whether a lock file entry exists for the stack.
        lock_digest: Digest stored in the lock file, if present.
    """

    model_config = ConfigDict(extra="forbid")

    stack: StackDefinition
    project_name: str | None = None
    user: str | None = None
    user_groups: list[str] = Field(default_factory=list)
    environment: str | None = None
    pipeline_packages: list[str] = Field(default_factory=list)
    is_locked: bool = False
    lock_digest: str | None = None


class PolicyResult(BaseModel):
    """Outcome of a single policy rule evaluation.

    Attributes:
        rule_name: Machine-readable identifier for the rule that produced
            this result (e.g. ``"stack_locked"``).
        status: One of ``passed``, ``failed``, or ``warning``.
        message: Human-readable explanation of the outcome.
        suggestion: Optional actionable fix when the rule fails.
    """

    model_config = ConfigDict(extra="forbid")

    rule_name: str
    status: Literal["passed", "failed", "warning"]
    message: str
    suggestion: str | None = None


@runtime_checkable
class PolicyRule(Protocol):
    """Interface every policy rule must satisfy.

    Implementations are simple classes with a ``name`` attribute and a
    ``validate`` method.  The engine calls ``validate`` for each registered
    rule and collects the results.
    """

    name: str

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Evaluate this rule against *context*.

        Args:
            context: All metadata required for evaluation.

        Returns:
            A ``PolicyResult`` describing the outcome.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pass(rule_name: str, message: str) -> PolicyResult:
    """Create a passing ``PolicyResult``.

    Args:
        rule_name: Identifier of the rule that passed.
        message: Human-readable success message.

    Returns:
        A ``PolicyResult`` with ``status='passed'``.
    """
    return PolicyResult(rule_name=rule_name, status="passed", message=message)


def _fail(
    rule_name: str,
    message: str,
    suggestion: str | None = None,
) -> PolicyResult:
    """Create a failing ``PolicyResult``.

    Args:
        rule_name: Identifier of the rule that failed.
        message: Human-readable failure explanation.
        suggestion: Optional actionable remediation advice.

    Returns:
        A ``PolicyResult`` with ``status='failed'``.
    """
    return PolicyResult(
        rule_name=rule_name,
        status="failed",
        message=message,
        suggestion=suggestion,
    )


def _warn(
    rule_name: str,
    message: str,
    suggestion: str | None = None,
) -> PolicyResult:
    """Create a warning ``PolicyResult``.

    Args:
        rule_name: Identifier of the rule that produced the warning.
        message: Human-readable warning explanation.
        suggestion: Optional actionable advice.

    Returns:
        A ``PolicyResult`` with ``status='warning'``.
    """
    return PolicyResult(
        rule_name=rule_name,
        status="warning",
        message=message,
        suggestion=suggestion,
    )


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------


class StackExistsRule:
    """Verifies the stack definition is present and not ``None``.

    This is a safety-net rule that catches cases where stack resolution
    silently returned ``None`` instead of raising an error.
    """

    name: str = "stack_exists"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Check that ``context.stack`` is set.

        Args:
            context: Policy evaluation context.

        Returns:
            Passed if the stack exists, failed otherwise.
        """
        # Pydantic enforces non-None on the field, but the context may have
        # been constructed manually with a dict that somehow bypasses this.
        if context.stack is None:  # type: ignore[redundant-expr]
            return _fail(
                self.name,
                "No stack definition was provided. Cannot proceed with execution.",
                suggestion=(
                    "Ensure a valid stack name is specified in your flowyml.yaml or passed via the --stack CLI flag."
                ),
            )
        return _pass(self.name, "Stack definition is present.")


class StackLockedRule:
    """Checks that the stack is locked when the environment requires it.

    A locked stack has a recorded SHA-256 digest in ``flowyml.lock``.
    This ensures reproducibility: the same stack content is used across
    runs and environments.
    """

    name: str = "stack_locked"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify the stack is locked, if required.

        The rule *warns* when no lock is present (locking not enforced).
        When a digest *is* expected it compares against the live stack
        digest and fails on mismatch.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating lock status.
        """
        if not context.is_locked and context.lock_digest is None:
            return _warn(
                self.name,
                (
                    f"Stack '{context.stack.name}' is not locked. "
                    f"Running without a lock file may cause "
                    f"non-reproducible behaviour."
                ),
                suggestion=(
                    f"Run 'flowyml stack lock --stack {context.stack.name}' "
                    f"to create a lock file and pin the stack definition."
                ),
            )

        if context.lock_digest is not None:
            actual = context.stack.compute_digest()
            if actual != context.lock_digest:
                return _fail(
                    self.name,
                    (
                        f"Stack '{context.stack.name}' digest mismatch. "
                        f"The stack definition has changed since it was "
                        f"locked.\n"
                        f"  Expected: {context.lock_digest}\n"
                        f"  Actual:   {actual}"
                    ),
                    suggestion=(
                        f"Run 'flowyml stack update --stack "
                        f"{context.stack.name}' to update the lock file, "
                        f"or 'flowyml stack lock --stack "
                        f"{context.stack.name}' to re-lock with the "
                        f"current definition."
                    ),
                )

        return _pass(
            self.name,
            f"Stack '{context.stack.name}' is locked and verified.",
        )


class UserPermissionRule:
    """Checks that the user belongs to at least one allowed group.

    An empty ``allowedGroups`` list means the stack is open to everyone.
    """

    name: str = "user_permission"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify user group membership.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating whether the user is authorised.
        """
        allowed = context.stack.spec.permissions.allowed_groups
        if not allowed:
            return _pass(
                self.name,
                f"Stack '{context.stack.name}' has no group restrictions.",
            )

        if context.user is None:
            return _fail(
                self.name,
                (f"Stack '{context.stack.name}' is restricted to groups {allowed}, but no user identity was provided."),
                suggestion=(
                    "Set the FLOWYML_USER environment variable or log in "
                    "with 'flowyml auth login' to establish your identity."
                ),
            )

        if not context.user_groups:
            return _fail(
                self.name,
                (
                    f"User '{context.user}' has no group memberships. "
                    f"Stack '{context.stack.name}' requires membership in "
                    f"one of: {', '.join(allowed)}."
                ),
                suggestion=(f"Contact your administrator to be added to one of these groups: {', '.join(allowed)}."),
            )

        overlap = set(context.user_groups) & set(allowed)
        if not overlap:
            return _fail(
                self.name,
                (
                    f"User '{context.user}' is a member of "
                    f"{', '.join(context.user_groups)}, but stack "
                    f"'{context.stack.name}' requires membership in one "
                    f"of: {', '.join(allowed)}."
                ),
                suggestion=(
                    f"Request access to one of the required groups ({', '.join(allowed)}) or use a different stack."
                ),
            )

        return _pass(
            self.name,
            (f"User '{context.user}' is authorised via group(s): {', '.join(sorted(overlap))}."),
        )


class ProjectPermissionRule:
    """Checks that the project name is in the allowed list.

    An empty ``allowedProjects`` list means any project may use the stack.
    """

    name: str = "project_permission"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify the project is allowed to use this stack.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating whether the project is permitted.
        """
        allowed = context.stack.spec.permissions.allowed_projects
        if not allowed:
            return _pass(
                self.name,
                f"Stack '{context.stack.name}' has no project restrictions.",
            )

        if context.project_name is None:
            return _fail(
                self.name,
                (
                    f"Stack '{context.stack.name}' is restricted to projects "
                    f"{allowed}, but no project name was provided."
                ),
                suggestion=("Set 'project.name' in your flowyml.yaml or pass --project on the command line."),
            )

        if context.project_name not in allowed:
            return _fail(
                self.name,
                (
                    f"Project '{context.project_name}' is not allowed to "
                    f"use stack '{context.stack.name}'. Allowed projects: "
                    f"{', '.join(allowed)}."
                ),
                suggestion=(
                    f"Ask the stack owner "
                    f"({context.stack.metadata.owner or 'platform team'}) "
                    f"to add '{context.project_name}' to the stack's "
                    f"allowedProjects list, or use a different stack."
                ),
            )

        return _pass(
            self.name,
            (f"Project '{context.project_name}' is allowed for stack '{context.stack.name}'."),
        )


class BackendAllowedRule:
    """Validates the stack's backend is in the globally supported set."""

    name: str = "backend_allowed"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify the backend is supported.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating backend support status.
        """
        backend = context.stack.spec.backend
        if backend not in SUPPORTED_BACKENDS:
            return _fail(
                self.name,
                (f"Backend '{backend}' used by stack '{context.stack.name}' is not a supported execution backend."),
                suggestion=(
                    f"Supported backends: "
                    f"{', '.join(sorted(SUPPORTED_BACKENDS))}. "
                    f"Check the stack definition or contact the "
                    f"platform team."
                ),
            )

        return _pass(self.name, f"Backend '{backend}' is supported.")


class BaseImageApprovedRule:
    """Checks the custom Docker image policy.

    When ``allowCustomDockerImage`` is ``False`` in the stack policy, only
    platform-managed base images are allowed (i.e. ``baseImage`` must be
    ``None``).
    """

    name: str = "base_image_approved"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify Docker base image compliance.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating base image approval status.
        """
        policy = context.stack.spec.policies
        runtime = context.stack.spec.runtime

        if not policy.allow_custom_docker_image and runtime.base_image is not None:
            return _fail(
                self.name,
                (
                    f"Custom Docker images are not allowed for stack "
                    f"'{context.stack.name}'. The stack specifies base "
                    f"image '{runtime.base_image}', but the policy "
                    f"prohibits custom images."
                ),
                suggestion=(
                    "Use one of the approved platform images or request "
                    "a new stack from the platform team. To allow custom "
                    "images, set 'policies.allowCustomDockerImage: true' "
                    "in the stack definition."
                ),
            )

        if runtime.base_image is not None:
            return _pass(
                self.name,
                (f"Custom Docker image '{runtime.base_image}' is allowed by stack policy."),
            )

        return _pass(
            self.name,
            "No custom Docker image specified; using platform default.",
        )


class PackageAllowListRule:
    """Validates pipeline packages against the stack's allow list.

    An empty allow list means all packages are permitted.  When the list
    is non-empty, *every* pipeline package must appear in it.
    """

    name: str = "package_allowlist"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify all pipeline packages are in the allow list.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating package compliance.
        """
        allowed = context.stack.spec.policies.allowed_python_packages
        if not allowed:
            return _pass(
                self.name,
                (f"Stack '{context.stack.name}' has no package allowlist restrictions."),
            )

        if not context.pipeline_packages:
            return _pass(self.name, "No pipeline packages to validate.")

        disallowed = sorted(set(context.pipeline_packages) - set(allowed))
        if disallowed:
            return _fail(
                self.name,
                (
                    f"The following packages are not on the allowlist for "
                    f"stack '{context.stack.name}': "
                    f"{', '.join(disallowed)}."
                ),
                suggestion=(
                    f"Allowed packages: {', '.join(sorted(allowed))}. "
                    f"Remove disallowed packages from your pipeline or "
                    f"ask the platform team to update the stack's "
                    f"allowedPythonPackages."
                ),
            )

        return _pass(
            self.name,
            "All pipeline packages are on the allowlist.",
        )


class PackageDenyListRule:
    """Validates pipeline packages against the stack's deny list.

    If any pipeline package appears in the deny list, the rule fails.
    """

    name: str = "package_denylist"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify no pipeline packages are on the deny list.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating package compliance.
        """
        denied = context.stack.spec.policies.denied_python_packages
        if not denied:
            return _pass(
                self.name,
                f"Stack '{context.stack.name}' has no package denylist.",
            )

        if not context.pipeline_packages:
            return _pass(self.name, "No pipeline packages to validate.")

        blocked = sorted(set(context.pipeline_packages) & set(denied))
        if blocked:
            return _fail(
                self.name,
                (f"The following packages are denied for stack '{context.stack.name}': {', '.join(blocked)}."),
                suggestion=(
                    "Remove the denied packages from your pipeline "
                    "dependencies. If you believe a package should be "
                    "allowed, contact the platform team to update the "
                    "stack's deniedPythonPackages."
                ),
            )

        return _pass(
            self.name,
            "No pipeline packages are on the denylist.",
        )


class ExternalNetworkRule:
    """Checks whether external network access is allowed.

    This rule *warns* rather than fails, because external network status
    is informational for the user; actual enforcement happens at the
    infrastructure level.
    """

    name: str = "external_network"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify external network access policy.

        Args:
            context: Policy evaluation context.

        Returns:
            Result with network access status.
        """
        if not context.stack.spec.policies.allow_external_network:
            return _warn(
                self.name,
                (
                    f"External network access is disabled for stack "
                    f"'{context.stack.name}'. Pipeline steps that require "
                    f"internet access (downloading data, calling APIs) "
                    f"will fail."
                ),
                suggestion=(
                    "Ensure all required data and dependencies are "
                    "available within the private network. If external "
                    "access is needed, use a stack that permits it or "
                    "request a policy exception."
                ),
            )

        return _pass(
            self.name,
            (f"External network access is allowed for stack '{context.stack.name}'."),
        )


class MaxRuntimeRule:
    """Validates the maximum pipeline runtime constraint.

    This rule warns when a max runtime is configured so users are aware
    of the ceiling.  Actual enforcement occurs during execution.
    """

    name: str = "max_runtime"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Report the max runtime policy.

        Args:
            context: Policy evaluation context.

        Returns:
            Warning if a max runtime is set, pass otherwise.
        """
        max_min = context.stack.spec.policies.max_runtime_minutes
        if max_min is not None:
            return _warn(
                self.name,
                (
                    f"Stack '{context.stack.name}' enforces a maximum "
                    f"runtime of {max_min} minute(s). Pipelines exceeding "
                    f"this limit will be terminated."
                ),
                suggestion=(
                    "Design your pipeline steps to complete within the "
                    "time limit. Consider splitting long-running tasks "
                    "into smaller steps."
                ),
            )

        return _pass(
            self.name,
            f"Stack '{context.stack.name}' has no maximum runtime limit.",
        )


class CostLimitRule:
    """Validates the estimated cost ceiling.

    Like ``MaxRuntimeRule``, this surfaces the constraint rather than
    enforcing it at validation time — actual cost is tracked at runtime.
    """

    name: str = "cost_limit"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Report the cost limit policy.

        Args:
            context: Policy evaluation context.

        Returns:
            Warning if a cost limit is set, pass otherwise.
        """
        max_cost = context.stack.spec.policies.max_estimated_cost_usd
        if max_cost is not None:
            return _warn(
                self.name,
                (
                    f"Stack '{context.stack.name}' enforces a maximum "
                    f"estimated cost of ${max_cost:.2f} USD. Runs "
                    f"exceeding this budget may be terminated."
                ),
                suggestion=(
                    "Monitor resource consumption and optimise compute "
                    "settings. If higher budgets are needed, contact the "
                    "platform team."
                ),
            )

        return _pass(
            self.name,
            f"Stack '{context.stack.name}' has no cost limit.",
        )


class SignedStackRule:
    """Checks the stack signature requirement.

    When ``requireSignedStack`` is ``True``, the stack must have signature
    verification enabled.  This prevents tampering with stack definitions.
    """

    name: str = "signed_stack"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify signature requirement compliance.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating signature status.
        """
        if context.stack.spec.policies.require_signed_stack:
            if not context.stack.spec.security.signature.enabled:
                return _fail(
                    self.name,
                    (
                        f"Stack '{context.stack.name}' requires a signed "
                        f"stack definition, but signature verification "
                        f"is not enabled."
                    ),
                    suggestion=(
                        "Enable signature verification in the stack's "
                        "security configuration "
                        "('security.signature.enabled: true') and sign "
                        "the stack definition before use."
                    ),
                )

        return _pass(
            self.name,
            (f"Stack '{context.stack.name}' signature policy is satisfied."),
        )


class ModelDeployerAllowedRule:
    """Validates the stack's model deployer against the policy allowlist.

    An empty ``allowedModelDeployers`` list means any deployer flavor is
    permitted.  When the stack has no ``deployment`` section this rule is a
    no-op.
    """

    name: str = "model_deployer_allowed"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify the declared model deployer is allowed.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating whether the deployer flavor is permitted.
        """
        deployment = context.stack.spec.deployment
        allowed = context.stack.spec.policies.allowed_model_deployers

        if deployment is None or deployment.model_deployer is None:
            return _pass(self.name, "No model deployer declared for this stack.")

        flavor = deployment.model_deployer
        if not allowed:
            return _pass(
                self.name,
                f"Stack '{context.stack.name}' has no model deployer restrictions.",
            )

        if flavor not in allowed:
            return _fail(
                self.name,
                (
                    f"Model deployer '{flavor}' is not allowed for stack "
                    f"'{context.stack.name}'. Allowed: {', '.join(sorted(allowed))}."
                ),
                suggestion=(
                    f"Use one of the approved deployers ({', '.join(sorted(allowed))}) "
                    f"or ask the stack owner "
                    f"({context.stack.metadata.owner or 'platform team'}) to allow "
                    f"'{flavor}'."
                ),
            )

        return _pass(
            self.name,
            f"Model deployer '{flavor}' is approved for stack '{context.stack.name}'.",
        )


class ModelRegistryAllowedRule:
    """Validates the stack's model registry against the policy allowlist.

    An empty ``allowedModelRegistries`` list means any registry flavor is
    permitted.  When the stack has no ``deployment`` section this rule is a
    no-op.
    """

    name: str = "model_registry_allowed"

    def validate(self, context: PolicyContext) -> PolicyResult:
        """Verify the declared model registry is allowed.

        Args:
            context: Policy evaluation context.

        Returns:
            Result indicating whether the registry flavor is permitted.
        """
        deployment = context.stack.spec.deployment
        allowed = context.stack.spec.policies.allowed_model_registries

        if deployment is None or deployment.model_registry is None:
            return _pass(self.name, "No model registry declared for this stack.")

        flavor = deployment.model_registry
        if not allowed:
            return _pass(
                self.name,
                f"Stack '{context.stack.name}' has no model registry restrictions.",
            )

        if flavor not in allowed:
            return _fail(
                self.name,
                (
                    f"Model registry '{flavor}' is not allowed for stack "
                    f"'{context.stack.name}'. Allowed: {', '.join(sorted(allowed))}."
                ),
                suggestion=(
                    f"Use one of the approved registries ({', '.join(sorted(allowed))}) "
                    f"or ask the stack owner "
                    f"({context.stack.metadata.owner or 'platform team'}) to allow "
                    f"'{flavor}'."
                ),
            )

        return _pass(
            self.name,
            f"Model registry '{flavor}' is approved for stack '{context.stack.name}'.",
        )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PolicyEngine:
    """Orchestrates policy rule evaluation against a ``PolicyContext``.

    The engine runs every registered rule and collects results.  Rules are
    evaluated in registration order; all rules run regardless of earlier
    failures (fail-open collection, fail-closed on ``check``).

    Args:
        rules: Explicit list of rules to use.  When ``None`` (default),
            all built-in rules are registered automatically.

    Example::

        engine = PolicyEngine()
        results = engine.validate(ctx)  # collect all results
        engine.check(ctx)  # raise on first failure

        # Custom rule set:
        engine = PolicyEngine(
            rules=[BackendAllowedRule(), PackageDenyListRule()],
        )
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules: list[PolicyRule] = rules if rules is not None else self.get_default_rules()

    # -- Public API ---------------------------------------------------------

    def validate(self, context: PolicyContext) -> list[PolicyResult]:
        """Run all rules and return their results.

        Every rule is evaluated regardless of earlier failures so that the
        caller receives a complete picture of all policy compliance issues.

        Args:
            context: Policy evaluation context.

        Returns:
            Ordered list of ``PolicyResult`` objects, one per rule.
        """
        results: list[PolicyResult] = []
        for rule in self._rules:
            try:
                results.append(rule.validate(context))
            except Exception:
                logger.exception(
                    "Policy rule '%s' raised an unexpected exception",
                    rule.name,
                )
                results.append(
                    _fail(
                        rule.name,
                        (f"Policy rule '{rule.name}' encountered an internal error during evaluation."),
                        suggestion=("This is likely a bug. Contact the platform team and include the full traceback."),
                    ),
                )
        return results

    def check(self, context: PolicyContext) -> None:
        """Run all rules and raise on any failure.

        This is the enforcement entry-point: if *any* rule returns
        ``status='failed'``, a ``PolicyViolationError`` is raised with
        all failure messages collected.

        Args:
            context: Policy evaluation context.

        Raises:
            PolicyViolationError: When one or more rules fail.
        """
        results = self.validate(context)
        failures = [r for r in results if r.status == "failed"]

        if failures:
            violations = [r.message for r in failures]
            first_rule = failures[0].rule_name

            stack_name = context.stack.name
            summary = f"Policy validation failed for stack '{stack_name}': {len(failures)} rule(s) violated."

            raise PolicyViolationError(
                summary,
                rule_name=first_rule,
                violations=violations,
            )

    # -- Class methods ------------------------------------------------------

    @classmethod
    def get_default_rules(cls) -> list[PolicyRule]:
        """Return a fresh list of all built-in policy rules.

        The rules are returned in recommended evaluation order.

        Returns:
            Ordered list of built-in rule instances.
        """
        return [
            StackExistsRule(),
            StackLockedRule(),
            UserPermissionRule(),
            ProjectPermissionRule(),
            BackendAllowedRule(),
            BaseImageApprovedRule(),
            PackageAllowListRule(),
            PackageDenyListRule(),
            ExternalNetworkRule(),
            MaxRuntimeRule(),
            CostLimitRule(),
            SignedStackRule(),
            ModelDeployerAllowedRule(),
            ModelRegistryAllowedRule(),
        ]
