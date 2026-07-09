"""Champion / challenger model promotion.

Compares a freshly-trained *challenger* version against the current *champion*
(the version currently in a given stage, e.g. ``production``) on a chosen
metric, promotes the challenger if it improves by at least ``min_improvement``,
and optionally triggers a redeploy of the new champion.

Designed to be dropped straight into a FlowyML ``@step``::

    @step(inputs=["candidate_version"])
    def gate(candidate_version: str):
        return promote_if_better(
            "churn", candidate_version, metric="auc",
            auto_deploy=True,
            deployment_spec=DeploymentSpec(name="churn", model=ModelRef("churn", stage="production"),
                                           runtime="fastapi", target="openshift"),
        )
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from flowyml.deployment.models import DeploymentSpec


@dataclass
class PromotionDecision:
    """Outcome of a champion/challenger comparison."""

    promoted: bool
    reason: str
    metric: str
    model_name: str
    challenger_version: str
    challenger_score: float | None = None
    champion_version: str | None = None
    champion_score: float | None = None
    improvement: float | None = None
    higher_is_better: bool = True
    comparison: dict[str, Any] = field(default_factory=dict)
    deployment: Any = None  # DeploymentResult when auto_deploy triggered

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.deployment is not None and hasattr(self.deployment, "to_dict"):
            data["deployment"] = self.deployment.to_dict()
        return data


def promote_if_better(
    name: str,
    candidate_version: str,
    *,
    metric: str,
    higher_is_better: bool = True,
    registry: Any = None,
    min_improvement: float = 0.0,
    to_stage: str = "production",
    compare_against: str = "production",
    archive_previous: bool = True,
    auto_deploy: bool = False,
    deployment_spec: DeploymentSpec | None = None,
    deployment_service: Any = None,
) -> PromotionDecision:
    """Promote ``candidate_version`` to ``to_stage`` iff it beats the champion.

    Args:
        name: Registered model name.
        candidate_version: The challenger version to evaluate.
        metric: Metric key stored on the model versions to compare.
        higher_is_better: Whether a larger metric value is better.
        registry: Registry object (defaults to built-in ``ModelRegistry``).
        min_improvement: Minimum absolute delta required to promote.
        to_stage: Stage to promote the challenger into if it wins.
        compare_against: Stage whose current version is the champion.
        archive_previous: Archive the previous champion after promotion.
        auto_deploy: Deploy the new champion when it is promoted.
        deployment_spec: Spec used for auto-deploy (its model ref is repointed
            to the promoted version).
        deployment_service: Optional pre-built ``DeploymentService``.

    Returns:
        A :class:`PromotionDecision`.
    """
    from flowyml.registry.model_registry import ModelRegistry, ModelStage

    reg = registry if registry is not None else ModelRegistry()

    challenger = reg.get_version(name, candidate_version)
    if challenger is None:
        raise ValueError(f"Challenger version '{candidate_version}' of model '{name}' not found")

    challenger_score = (challenger.metrics or {}).get(metric)
    if challenger_score is None:
        raise ValueError(
            f"Challenger '{name}:{candidate_version}' has no metric '{metric}'. "
            f"Available: {sorted((challenger.metrics or {}).keys())}",
        )

    champion = reg.get_latest_version(name, stage=ModelStage(compare_against))
    champion_score = (champion.metrics or {}).get(metric) if champion else None
    comparison = reg.compare_versions(
        name,
        [v for v in {candidate_version, getattr(champion, "version", None)} if v],
    )

    # First model ever → promote unconditionally.
    if champion is None or champion.version == candidate_version:
        decision = _finalize(
            reg,
            name,
            candidate_version,
            ModelStage(to_stage),
            promoted=True,
            reason="No existing champion — promoting first version"
            if champion is None
            else "Candidate is already the champion",
            metric=metric,
            higher_is_better=higher_is_better,
            challenger_score=challenger_score,
            champion=champion,
            champion_score=champion_score,
            improvement=None,
            comparison=comparison,
            archive_previous=False,
        )
        return _maybe_deploy(decision, auto_deploy, deployment_spec, deployment_service, candidate_version, to_stage)

    # Champion exists but has no comparable value for this metric → the
    # challenger wins by default (there is no baseline to beat).
    if champion_score is None:
        decision = _finalize(
            reg,
            name,
            candidate_version,
            ModelStage(to_stage),
            promoted=True,
            reason=(
                f"Champion '{name}:{champion.version}' has no metric '{metric}' to "
                f"compare against — promoting challenger {metric}={challenger_score:.6g}"
            ),
            metric=metric,
            higher_is_better=higher_is_better,
            challenger_score=challenger_score,
            champion=champion,
            champion_score=champion_score,
            improvement=None,
            comparison=comparison,
            archive_previous=archive_previous,
        )
        return _maybe_deploy(decision, auto_deploy, deployment_spec, deployment_service, candidate_version, to_stage)

    if higher_is_better:
        improvement = challenger_score - champion_score
        wins = challenger_score > champion_score + min_improvement
    else:
        improvement = champion_score - challenger_score
        wins = challenger_score < champion_score - min_improvement

    if wins:
        reason = (
            f"Challenger {metric}={challenger_score:.6g} beats champion "
            f"{champion_score:.6g} by {improvement:.6g} (min_improvement={min_improvement})"
        )
        decision = _finalize(
            reg,
            name,
            candidate_version,
            ModelStage(to_stage),
            promoted=True,
            reason=reason,
            metric=metric,
            higher_is_better=higher_is_better,
            challenger_score=challenger_score,
            champion=champion,
            champion_score=champion_score,
            improvement=improvement,
            comparison=comparison,
            archive_previous=archive_previous,
        )
        return _maybe_deploy(decision, auto_deploy, deployment_spec, deployment_service, candidate_version, to_stage)

    reason = (
        f"Challenger {metric}={challenger_score:.6g} does not beat champion "
        f"{champion_score:.6g} (improvement={improvement:.6g}, required>{min_improvement})"
    )
    logger.info(reason)
    return PromotionDecision(
        promoted=False,
        reason=reason,
        metric=metric,
        model_name=name,
        challenger_version=candidate_version,
        challenger_score=challenger_score,
        champion_version=champion.version,
        champion_score=champion_score,
        improvement=improvement,
        higher_is_better=higher_is_better,
        comparison=comparison,
    )


def _finalize(
    reg: Any,
    name: str,
    version: str,
    to_stage: Any,
    *,
    promoted: bool,
    reason: str,
    metric: str,
    higher_is_better: bool,
    challenger_score: float | None,
    champion: Any,
    champion_score: float | None,
    improvement: float | None,
    comparison: dict,
    archive_previous: bool,
) -> PromotionDecision:
    from flowyml.registry.model_registry import ModelStage

    logger.info("Promoting %s:%s -> %s (%s)", name, version, to_stage, reason)
    reg.promote(name, version, to_stage)
    if archive_previous and champion is not None and champion.version != version:
        try:
            reg.promote(name, champion.version, ModelStage.ARCHIVED)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not archive previous champion %s:%s: %s", name, champion.version, exc)
    return PromotionDecision(
        promoted=promoted,
        reason=reason,
        metric=metric,
        model_name=name,
        challenger_version=version,
        challenger_score=challenger_score,
        champion_version=getattr(champion, "version", None),
        champion_score=champion_score,
        improvement=improvement,
        higher_is_better=higher_is_better,
        comparison=comparison,
    )


def _maybe_deploy(
    decision: PromotionDecision,
    auto_deploy: bool,
    deployment_spec: Any,
    deployment_service: Any,
    version: str,
    to_stage: str,
) -> PromotionDecision:
    if not (auto_deploy and decision.promoted and deployment_spec is not None):
        return decision
    from flowyml.deployment.models import ModelRef
    from flowyml.deployment.service import DeploymentService

    # Repoint the spec at the freshly promoted version for a reproducible deploy.
    deployment_spec.model = ModelRef(name=decision.model_name, version=version)
    service = deployment_service or DeploymentService()
    try:
        decision.deployment = service.deploy(deployment_spec)
        decision.reason += " — deployed new champion"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Auto-deploy after promotion failed")
        decision.reason += f" — auto-deploy failed: {exc}"
    return decision
