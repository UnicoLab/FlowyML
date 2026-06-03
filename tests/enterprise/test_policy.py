"""Tests for the enterprise policy engine."""

import copy

import pytest

from flowyml.stacks.enterprise.exceptions import PolicyViolationError
from flowyml.stacks.enterprise.models import StackDefinition
from flowyml.stacks.enterprise.policy import (
    BackendAllowedRule,
    CostLimitRule,
    MaxRuntimeRule,
    PolicyContext,
    PolicyEngine,
    ProjectPermissionRule,
    SignedStackRule,
    UserPermissionRule,
)


class TestPolicyEngineDefaults:
    """PolicyEngine initialization and default rules."""

    def test_policy_engine_default_rules(self):
        """Default engine loads exactly 12 built-in rules."""
        engine = PolicyEngine()
        rules = PolicyEngine.get_default_rules()
        assert len(rules) == 12, f"Expected 12 default rules, got {len(rules)}"


class TestPolicyChecks:
    """Individual policy rule validation."""

    def test_policy_check_passes_valid_stack(self, sample_stack):
        """A stack with no restrictions passes all policy checks."""
        engine = PolicyEngine()
        ctx = PolicyContext(stack=sample_stack)
        # Should NOT raise
        engine.check(ctx)

    def test_policy_check_fails_denied_package(self, azureml_stack):
        """Using a denied package triggers PolicyViolationError."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="alice",
            user_groups=["ml-team"],
            pipeline_packages=["torch-nightly"],
        )
        with pytest.raises(PolicyViolationError):
            engine.check(ctx)

    def test_policy_check_fails_custom_image(self, azureml_stack):
        """allowCustomDockerImage=False with a baseImage set fails base_image_approved."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="alice",
            user_groups=["ml-team"],
        )
        results = engine.validate(ctx)
        image_result = next(r for r in results if r.rule_name == "base_image_approved")
        assert (
            image_result.status == "failed"
        ), "base_image_approved should fail when custom images are disallowed but one is set"

    def test_policy_check_user_permission_pass(self, azureml_stack):
        """User in an allowed group passes user_permission rule."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="alice",
            user_groups=["data-science"],
        )
        results = engine.validate(ctx)
        perm_result = next(r for r in results if r.rule_name == "user_permission")
        assert perm_result.status == "passed", "User in 'data-science' should be authorised"

    def test_policy_check_user_permission_fail(self, azureml_stack):
        """User NOT in any allowed group fails user_permission rule."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="bob",
            user_groups=["finance-team"],
        )
        results = engine.validate(ctx)
        perm_result = next(r for r in results if r.rule_name == "user_permission")
        assert perm_result.status == "failed", "User in 'finance-team' should be denied"

    def test_policy_check_project_permission(self, sample_stack_dict):
        """Project not in allowedProjects fails project_permission rule."""
        data = copy.deepcopy(sample_stack_dict)
        data["spec"]["permissions"] = {"allowedProjects": ["ml-project"]}
        stack = StackDefinition.from_dict(data)

        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=stack,
            project_name="other-project",
        )
        results = engine.validate(ctx)
        proj_result = next(r for r in results if r.rule_name == "project_permission")
        assert proj_result.status == "failed", "Project 'other-project' should be denied"

    def test_policy_check_signed_stack_required(self, sample_stack_dict):
        """requireSignedStack=True with signature.enabled=False fails signed_stack."""
        data = copy.deepcopy(sample_stack_dict)
        data["spec"]["policies"] = {"requireSignedStack": True}
        data["spec"]["security"] = {"signature": {"enabled": False, "provider": "cosign"}}
        stack = StackDefinition.from_dict(data)

        engine = PolicyEngine()
        ctx = PolicyContext(stack=stack)
        results = engine.validate(ctx)
        sig_result = next(r for r in results if r.rule_name == "signed_stack")
        assert sig_result.status == "failed", "Unsigned stack should fail signed_stack rule"

    def test_policy_check_max_runtime(self, azureml_stack):
        """maxRuntimeMinutes set produces a warning."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="alice",
            user_groups=["ml-team"],
        )
        results = engine.validate(ctx)
        rt_result = next(r for r in results if r.rule_name == "max_runtime")
        assert rt_result.status == "warning", "max_runtime should warn when a limit is configured"
        assert "120" in rt_result.message, "Warning should mention the 120-minute limit"

    def test_policy_check_cost_limit(self, sample_stack_dict):
        """maxEstimatedCostUsd set produces a warning."""
        data = copy.deepcopy(sample_stack_dict)
        data["spec"]["policies"] = {"maxEstimatedCostUsd": 50.0}
        stack = StackDefinition.from_dict(data)

        engine = PolicyEngine()
        ctx = PolicyContext(stack=stack)
        results = engine.validate(ctx)
        cost_result = next(r for r in results if r.rule_name == "cost_limit")
        assert cost_result.status == "warning", "cost_limit should warn when a budget is set"

    def test_policy_engine_custom_rules(self, sample_stack):
        """Engine initialised with custom rules only runs those rules."""
        engine = PolicyEngine(rules=[BackendAllowedRule()])
        ctx = PolicyContext(stack=sample_stack)
        results = engine.validate(ctx)
        assert len(results) == 1, "Only one custom rule should produce one result"
        assert results[0].rule_name == "backend_allowed"

    def test_policy_violation_error_raised(self, azureml_stack):
        """PolicyViolationError carries the violations list."""
        engine = PolicyEngine()
        ctx = PolicyContext(
            stack=azureml_stack,
            user="nobody",
            user_groups=["outsiders"],
            pipeline_packages=["torch-nightly"],
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            engine.check(ctx)
        assert len(exc_info.value.violations) >= 1, "Should report at least one violation"
