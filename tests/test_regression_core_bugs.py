"""Regression tests for core bugs surfaced by the examples audit.

Each test pins a specific bug so it cannot silently regress:

1. ``flowyml.integrations`` must re-export the "always available" session symbols.
2. ``VersionedPipeline.display_comparison`` must not reference a non-existent
   ``current_version`` attribute.
3. ``create_from_template`` must not pollute the global step registry (so it can
   be called twice / alongside user steps of the same name).
4. ``Scorer.to_dict`` must work for adapter scorers even if ``_config`` is unset,
   and adapter ``__init__``s must call ``super().__init__``.
"""

from __future__ import annotations

import pytest


# --------------------------------------------------------------------------- #
# Bug 1: integrations re-exports                                               #
# --------------------------------------------------------------------------- #
def test_integrations_session_symbols_importable():
    from flowyml.integrations import (
        GenAISession,
        SessionEvaluator,
        SessionEventStream,
        SessionTracer,
        Turn,
        session_trace,
    )

    for sym in (session_trace, GenAISession, Turn, SessionTracer, SessionEvaluator, SessionEventStream):
        assert sym is not None

    import flowyml.integrations as integ

    for name in (
        "session_trace",
        "GenAISession",
        "Turn",
        "SessionTracer",
        "SessionEvaluator",
        "SessionEventStream",
    ):
        assert name in integ.__all__


# --------------------------------------------------------------------------- #
# Bug 2: VersionedPipeline.display_comparison                                  #
# --------------------------------------------------------------------------- #
def test_versioned_pipeline_display_comparison(tmp_path):
    from flowyml.core.step import step
    from flowyml.core.versioning import VersionedPipeline

    def _loader():
        return 1

    load = step(name="reg_load", outputs=["x"], register=False)(_loader)

    vp = VersionedPipeline("reg_pipeline", version="v1.0.0", versions_dir=str(tmp_path))
    vp.add_step(load)
    vp.save_version()

    vp.version = "v1.1.0"
    extra = step(name="reg_extra", inputs=["x"], register=False)(_loader)
    vp.add_step(extra)
    vp.save_version()

    # Previously raised AttributeError via __getattr__ delegation.
    vp.display_comparison("v1.0.0")


# --------------------------------------------------------------------------- #
# Bug 3: create_from_template must not register steps globally                 #
# --------------------------------------------------------------------------- #
def test_create_from_template_is_repeatable():
    from flowyml.core.step import clear_step_registry, get_registered_steps
    from flowyml.core.templates import create_from_template

    clear_step_registry()

    def load():
        return [1, 2, 3]

    def train(dataset):
        return "model"

    # Instantiating twice used to raise "Step 'load_data' is already registered".
    p1 = create_from_template("ml_training", data_loader=load, trainer=train)
    p2 = create_from_template("ml_training", data_loader=load, trainer=train)

    assert p1 is not p2
    assert {s.name for s in p1.steps} >= {"load_data", "train"}
    # Template-internal steps must not leak into the global registry.
    assert get_registered_steps() == []


def test_user_step_can_share_template_step_name():
    from flowyml.core.step import clear_step_registry, step
    from flowyml.core.templates import create_from_template

    clear_step_registry()

    # A user registers a step named "load_data"...
    @step(name="load_data", outputs=["dataset"])
    def load_data():
        return [1, 2, 3]

    def train(dataset):
        return "model"

    # ...the template must still instantiate without a name clash.
    pipeline = create_from_template("ml_training", data_loader=lambda: [1], trainer=train)
    assert pipeline is not None


# --------------------------------------------------------------------------- #
# Bug 4: Scorer.to_dict for adapter scorers                                    #
# --------------------------------------------------------------------------- #
def test_deepeval_scorer_to_dict_has_config():
    from flowyml.evals.scorers.deepeval_adapter import DeepEvalAnswerRelevancy

    scorer = DeepEvalAnswerRelevancy()
    data = scorer.to_dict()
    assert data["config"] == {"model": "gpt-4o-mini"}
    assert scorer._config == {"model": "gpt-4o-mini"}


@pytest.mark.parametrize(
    ("import_path", "cls_name"),
    [
        ("flowyml.evals.scorers.deepeval_adapter", "DeepEvalHallucination"),
        ("flowyml.evals.scorers.ragas_adapter", "RagasFaithfulness"),
        ("flowyml.evals.scorers.phoenix_adapter", "PhoenixToxicity"),
    ],
)
def test_adapter_scorers_set_config(import_path, cls_name):
    import importlib

    module = importlib.import_module(import_path)
    scorer = getattr(module, cls_name)()
    # _config exists because __init__ now calls super().__init__.
    assert isinstance(scorer._config, dict)
    # to_dict never raises AttributeError.
    assert "config" in scorer.to_dict()
