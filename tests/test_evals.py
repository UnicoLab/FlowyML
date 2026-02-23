"""Tests for FlowyML Evaluation Framework.

Tests EvalDataset, evaluate(), EvalResult, EvalRun, JudgeArena,
TraceBridge, EvalAssert, and EvalStep.
"""

import pytest
from unittest.mock import patch, MagicMock

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.evals.core import EvalResult, evaluate
from flowyml.evals.dataset import EvalDataset
from flowyml.evals.run import EvalRun
from flowyml.evals.assertions import EvalAssert, AssertionResult
from flowyml.evals.pipeline import EvalStep
from flowyml.evals.bridge import TraceBridge


# ─── EvalDataset Tests ────────────────────────────────────────────────


class TestEvalDataset:
    """Test the EvalDataset asset."""

    def test_create_classical(self):
        ds = EvalDataset.create_classical(
            name="test_ds",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        assert ds.name == "test_ds"
        assert ds.data_format == "classical_ml"
        assert ds.num_examples == 5

    def test_create_genai(self):
        examples = [
            {"inputs": "What is ML?", "outputs": "Machine Learning is..."},
            {"inputs": "What is AI?", "outputs": "Artificial Intelligence..."},
        ]
        ds = EvalDataset.create_genai(name="genai_ds", examples=examples)
        assert ds.name == "genai_ds"
        assert ds.data_format == "genai"
        assert ds.num_examples == 2

    def test_auto_detect_classical(self):
        data = {"predictions": [1, 0, 1], "targets": [1, 0, 0]}
        ds = EvalDataset(name="auto_ds", data=data)
        assert ds.data_format == "classical_ml"

    def test_auto_detect_genai(self):
        data = [
            {"inputs": "hello", "outputs": "world"},
            {"inputs": "foo", "outputs": "bar"},
        ]
        ds = EvalDataset(name="auto_ds", data=data)
        assert ds.data_format == "genai"

    def test_to_scorer_args_classical(self):
        ds = EvalDataset.create_classical(
            name="test",
            predictions=[1, 0],
            targets=[1, 1],
        )
        args = ds.to_scorer_args()
        assert len(args) == 1  # classical returns a single batch
        assert "predictions" in args[0]
        assert "targets" in args[0]

    def test_split(self):
        ds = EvalDataset.create_genai(
            name="split_test",
            examples=[{"inputs": f"q{i}", "outputs": f"a{i}"} for i in range(10)],
        )
        train, test = ds.split(ratio=0.7)
        assert train.num_examples == 7
        assert test.num_examples == 3

    def test_sample(self):
        ds = EvalDataset.create_genai(
            name="sample_test",
            examples=[{"inputs": f"q{i}", "outputs": f"a{i}"} for i in range(20)],
        )
        sampled = ds.sample(n=5)
        assert sampled.num_examples == 5

    def test_versioning(self):
        ds = EvalDataset.create_genai(name="versioned", examples=[{"inputs": "q", "outputs": "a"}])
        assert ds.version is not None

    def test_tags(self):
        ds = EvalDataset.create_genai(
            name="tagged",
            examples=[{"inputs": "q", "outputs": "a"}],
            tags={"domain": "qa", "split": "test"},
        )
        assert ds.tags["domain"] == "qa"


# ─── EvalResult Tests ────────────────────────────────────────────────


class TestEvalResult:
    """Test the EvalResult data model."""

    def test_basic_result(self):
        result = EvalResult(experiment="test_exp")
        assert result.experiment == "test_exp"
        assert result.summary == {}
        assert result.passed is True  # no assertions = pass by default

    def test_to_dict(self):
        result = EvalResult(experiment="test")
        result.summary = {"accuracy": 0.95}
        d = result.to_dict()
        assert d["experiment"] == "test"
        assert d["summary"]["accuracy"] == 0.95

    def test_pass_rate(self):
        result = EvalResult()
        result.scores["accuracy"] = [
            ScorerFeedback(name="accuracy", value=0.9, passed=True),
        ]
        result.scores["f1"] = [
            ScorerFeedback(name="f1", value=0.7, passed=False),
        ]
        assert result.pass_rate == 0.5  # 1 passed, 1 failed

    def test_regressions_from(self):
        baseline = EvalResult()
        baseline.summary = {"accuracy": 0.95, "f1": 0.90}

        current = EvalResult()
        current.summary = {"accuracy": 0.85, "f1": 0.92}

        regressions = current.regressions_from(baseline, threshold=0.05)
        assert "accuracy" in regressions  # dropped by 0.10
        assert "f1" not in regressions  # improved


# ─── evaluate() Tests ────────────────────────────────────────────────


class TestEvaluateFunction:
    """Test the core evaluate() function."""

    def test_evaluate_classical(self):
        from flowyml.evals.scorers.classification import Accuracy

        ds = EvalDataset.create_classical(
            name="eval_test",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = evaluate(data=ds, scorers=[Accuracy()], store=False)
        assert isinstance(result, EvalResult)
        assert "accuracy" in result.summary
        assert result.summary["accuracy"] == pytest.approx(0.8)

    def test_evaluate_multiple_scorers(self):
        from flowyml.evals.scorers.classification import Accuracy, Precision, Recall

        ds = EvalDataset.create_classical(
            name="multi_scorer",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = evaluate(
            data=ds,
            scorers=[Accuracy(), Precision(), Recall()],
            store=False,
        )
        assert len(result.summary) == 3
        assert "accuracy" in result.summary
        assert "precision" in result.summary
        assert "recall" in result.summary

    def test_evaluate_with_experiment(self):
        ds = EvalDataset.create_classical(
            name="exp_test",
            predictions=[1, 0, 1],
            targets=[1, 0, 1],
        )
        from flowyml.evals.scorers.classification import Accuracy

        result = evaluate(
            data=ds,
            scorers=[Accuracy()],
            experiment="test_experiment",
            store=False,
        )
        assert result.experiment == "test_experiment"


# ─── EvalRun Tests ────────────────────────────────────────────────────


class TestEvalRun:
    """Test the EvalRun tracking."""

    def test_create_run(self):
        run = EvalRun(experiment="test_run")
        assert run.status == "pending"
        assert run.experiment == "test_run"

    def test_execute_run(self):
        from flowyml.evals.scorers.classification import Accuracy

        ds = EvalDataset.create_classical(
            name="run_test",
            predictions=[1, 0, 1, 1],
            targets=[1, 0, 1, 0],
        )
        run = EvalRun(experiment="run_exp")
        result = run.execute(data=ds, scorers=[Accuracy()])
        assert run.status in ("completed", "completed_with_regressions")
        assert result is not None
        assert "accuracy" in result.summary

    def test_compare_runs(self):
        from flowyml.evals.scorers.classification import Accuracy

        ds1 = EvalDataset.create_classical(name="r1", predictions=[1, 0, 1], targets=[1, 0, 1])
        ds2 = EvalDataset.create_classical(name="r2", predictions=[1, 0, 0], targets=[1, 0, 1])

        run1 = EvalRun(experiment="cmp")
        run1.execute(data=ds1, scorers=[Accuracy()])

        run2 = EvalRun(experiment="cmp")
        run2.execute(data=ds2, scorers=[Accuracy()])

        comparison = run1.compare_with(run2)
        assert "accuracy" in comparison["metrics"]

    def test_to_dict(self):
        run = EvalRun(experiment="dict_test")
        d = run.to_dict()
        assert d["experiment"] == "dict_test"
        assert d["status"] == "pending"


# ─── EvalAssert Tests ────────────────────────────────────────────────


class TestEvalAssert:
    """Test the CI/CD assertions."""

    def test_assert_min_score_pass(self):
        result = EvalResult()
        result.summary = {"accuracy": 0.95}
        result.scores["accuracy"] = [ScorerFeedback(name="accuracy", value=0.95)]

        assertions = EvalAssert(result)
        assertions.assert_min_score("accuracy", 0.9)
        assert assertions.all_passed is True

    def test_assert_min_score_fail(self):
        result = EvalResult()
        result.summary = {"accuracy": 0.8}
        result.scores["accuracy"] = [ScorerFeedback(name="accuracy", value=0.8)]

        assertions = EvalAssert(result)
        assertions.assert_min_score("accuracy", 0.9)
        assert assertions.all_passed is False
        assert len(assertions.failures) == 1

    def test_assert_max_score(self):
        result = EvalResult()
        result.summary = {"toxicity": 0.1}

        assertions = EvalAssert(result)
        assertions.assert_max_score("toxicity", 0.3)
        assert assertions.all_passed is True

    def test_assert_no_regression(self):
        baseline = EvalResult()
        baseline.summary = {"accuracy": 0.95}

        current = EvalResult()
        current.summary = {"accuracy": 0.80}

        assertions = EvalAssert(current)
        assertions.assert_no_regression(baseline, threshold=0.05)
        assert assertions.all_passed is False

    def test_assert_pass_rate(self):
        result = EvalResult()
        result.scores["a"] = [ScorerFeedback(name="a", value=0.9, passed=True)]
        result.scores["b"] = [ScorerFeedback(name="b", value=0.8, passed=True)]

        assertions = EvalAssert(result)
        assertions.assert_pass_rate(0.95)
        assert assertions.all_passed is True

    def test_chaining(self):
        result = EvalResult()
        result.summary = {"accuracy": 0.95, "f1": 0.90}
        result.scores["accuracy"] = [ScorerFeedback(name="accuracy", value=0.95)]
        result.scores["f1"] = [ScorerFeedback(name="f1", value=0.90)]

        assertions = EvalAssert(result).assert_min_score("accuracy", 0.9).assert_min_score("f1", 0.85)
        assert assertions.all_passed is True
        assert len(assertions.results) == 2

    def test_validate_raises(self):
        result = EvalResult()
        result.summary = {"accuracy": 0.5}
        result.scores["accuracy"] = [ScorerFeedback(name="accuracy", value=0.5)]

        assertions = EvalAssert(result)
        assertions.assert_min_score("accuracy", 0.9)

        with pytest.raises(AssertionError):
            assertions.validate(raise_on_failure=True)


# ─── EvalStep Tests ──────────────────────────────────────────────────


class TestEvalStep:
    """Test the pipeline step integration."""

    def test_eval_step_basic(self):
        from flowyml.evals.scorers.classification import Accuracy

        step = EvalStep(scorers=[Accuracy()], name="test_eval")
        result = step(predictions=[1, 0, 1, 1], targets=[1, 0, 1, 0])
        assert isinstance(result, EvalResult)
        assert "accuracy" in result.summary

    def test_eval_step_with_dict(self):
        from flowyml.evals.scorers.classification import Accuracy

        step = EvalStep(scorers=[Accuracy()])
        result = step(data={"predictions": [1, 0, 1], "targets": [1, 0, 1]})
        assert result.summary["accuracy"] == pytest.approx(1.0)

    def test_eval_step_fail_on_regression(self):
        from flowyml.evals.scorers.classification import Accuracy

        baseline = EvalResult()
        baseline.summary = {"accuracy": 0.99}

        step = EvalStep(
            scorers=[Accuracy()],
            fail_on_regression=True,
            baseline=baseline,
        )

        with pytest.raises(RuntimeError, match="regressions"):
            step(predictions=[1, 0, 0, 0], targets=[1, 0, 1, 1])


# ─── TraceBridge Tests ───────────────────────────────────────────────


class TestTraceBridge:
    """Test the trace-to-evaluation bridge."""

    def test_bridge_with_trace_events(self):
        from flowyml.evals.scorers.classification import Accuracy

        bridge = TraceBridge()
        events = [
            {"input_data": "What is ML?", "output_data": "Machine Learning is..."},
            {"input_data": "What is AI?", "output_data": "AI is..."},
        ]
        # This tests the event conversion path; GenAI scorers would need
        # mocking for actual LLM calls, so we just test the bridge mechanics
        result = bridge.evaluate_traces(trace_events=events, scorers=[], experiment="bridge_test")
        assert isinstance(result, EvalResult)
        assert result.metadata.get("source") == "trace_bridge"

    def test_bridge_empty_events(self):
        bridge = TraceBridge()
        result = bridge.evaluate_traces(trace_events=[], scorers=[])
        assert isinstance(result, EvalResult)

    def test_traces_to_examples(self):
        bridge = TraceBridge()
        events = [
            {"input_data": "q1", "output_data": "a1", "context": "ctx1"},
            {"prompt": "q2", "response": "a2"},
        ]
        examples = bridge._traces_to_examples(events)
        assert len(examples) == 2
        assert examples[0]["inputs"] == "q1"
        assert examples[0]["outputs"] == "a1"
        assert examples[1]["inputs"] == "q2"


# ─── JudgeArena Tests ───────────────────────────────────────────────


class TestJudgeArena:
    """Test the Judge Arena (A/B testing evaluators)."""

    def test_arena_requires_two_judges(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy

        with pytest.raises(ValueError, match="at least 2"):
            JudgeArena(judges=[Accuracy()])

    def test_arena_evaluate(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])

        ds = EvalDataset.create_classical(
            name="arena_test",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )

        result = arena.evaluate(data=ds)

        assert len(result.judges) == 2
        assert len(result.rankings) == 2
        assert result.rankings[0]["elo"] >= result.rankings[1]["elo"]

    def test_arena_with_human_labels(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])

        ds = EvalDataset.create_classical(
            name="arena_human",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )

        # Classical scorers produce batch scores, so human_labels must match
        result = arena.evaluate(data=ds, human_labels=[0.85])

        assert len(result.human_agreement) > 0
        assert result.best_judge() in result.judges


# ─── Import Tests ────────────────────────────────────────────────────


class TestImports:
    """Test that all public API imports work."""

    def test_top_level_imports(self):
        from flowyml.evals import (
            evaluate,
            evaluate_traces,
            EvalResult,
            EvalDataset,
            EvalSuite,
            EvalRun,
            EvalAssert,
            EvalStep,
            EvalSchedule,
            JudgeArena,
            JudgeArenaResult,
            TraceBridge,
            Scorer,
            ScorerFeedback,
            make_judge,
            make_scorer,
            get_scorer,
        )

        assert all(
            [
                evaluate,
                evaluate_traces,
                EvalResult,
                EvalDataset,
                EvalSuite,
                EvalRun,
                EvalAssert,
                EvalStep,
                EvalSchedule,
                JudgeArena,
                JudgeArenaResult,
                TraceBridge,
                Scorer,
                ScorerFeedback,
                make_judge,
                make_scorer,
                get_scorer,
            ],
        )

    def test_scorer_imports(self):
        from flowyml.evals import (
            Accuracy,
            Precision,
            Recall,
            F1Score,
            AUCROC,
            ConfusionMatrixScorer,
            LogLoss,
            MSE,
            RMSE,
            MAE,
            R2Score,
            MAPE,
            MaxError,
            Relevance,
            Coherence,
            Toxicity,
            Faithfulness,
            # Adapters
            DeepEvalAnswerRelevancy,
            DeepEvalHallucination,
            DeepEvalBias,
            DeepEvalToxicity,
            RagasFaithfulness,
            RagasContextPrecision,
            RagasContextRecall,
            RagasAnswerRelevancy,
            PhoenixHallucination,
            PhoenixToxicity,
            PhoenixQACorrectness,
            PhoenixSummarization,
        )

        assert all(
            [
                Accuracy,
                Precision,
                Recall,
                F1Score,
                AUCROC,
                ConfusionMatrixScorer,
                LogLoss,
                MSE,
                RMSE,
                MAE,
                R2Score,
                MAPE,
                MaxError,
                Relevance,
                Coherence,
                Toxicity,
                Faithfulness,
                DeepEvalAnswerRelevancy,
                DeepEvalHallucination,
                DeepEvalBias,
                DeepEvalToxicity,
                RagasFaithfulness,
                RagasContextPrecision,
                RagasContextRecall,
                RagasAnswerRelevancy,
                PhoenixHallucination,
                PhoenixToxicity,
                PhoenixQACorrectness,
                PhoenixSummarization,
            ],
        )

    def test_main_package_imports(self):
        from flowyml import (
            evaluate,
            evaluate_traces,
            EvalResult,
            EvalDataset,
            EvalSuite,
            EvalAssert,
            EvalSchedule,
            get_scorer,
        )

        assert all(
            [
                evaluate,
                evaluate_traces,
                EvalResult,
                EvalDataset,
                EvalSuite,
                EvalAssert,
                EvalSchedule,
                get_scorer,
            ],
        )


# ─── EvalSuite Tests ────────────────────────────────────────────────


class TestEvalSuite:
    """Test the EvalSuite reusable scorer collection."""

    def test_suite_creation(self):
        from flowyml.evals import EvalSuite, Accuracy, F1Score

        suite = EvalSuite(
            name="test_suite",
            scorers=[Accuracy(), F1Score()],
            description="Test suite",
        )
        assert suite.name == "test_suite"
        assert len(suite) == 2
        assert suite.scorer_names == ["accuracy", "f1_score"]

    def test_suite_add_remove(self):
        from flowyml.evals import EvalSuite, Accuracy, Precision

        suite = EvalSuite(name="chain_test")
        suite.add(Accuracy()).add(Precision())
        assert len(suite) == 2

        suite.remove("accuracy")
        assert len(suite) == 1
        assert suite.scorer_names == ["precision"]

    def test_suite_run(self):
        from flowyml.evals import EvalSuite, Accuracy, F1Score

        suite = EvalSuite("run_test", scorers=[Accuracy(), F1Score()])

        ds = EvalDataset.create_classical(
            name="suite_data",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = suite.run(data=ds, store=False)

        assert "accuracy" in result.summary
        assert "f1_score" in result.summary
        assert result.metadata.get("suite_name") == "run_test"

    def test_suite_empty_raises(self):
        from flowyml.evals import EvalSuite

        suite = EvalSuite("empty")
        ds = EvalDataset.create_classical("d", predictions=[1], targets=[1])
        with pytest.raises(ValueError, match="no scorers"):
            suite.run(data=ds)

    def test_suite_repr(self):
        from flowyml.evals import EvalSuite, Accuracy

        suite = EvalSuite("my_suite", scorers=[Accuracy()])
        assert "my_suite" in repr(suite)
        assert "accuracy" in repr(suite)


# ─── Arena Enhancement Tests ────────────────────────────────────────


class TestArenaEnhancements:
    """Test Arena cost_analysis, correlation_matrix, and agreement_scores."""

    def test_cost_analysis(self):
        from flowyml.evals.arena import JudgeArena, JudgeArenaResult
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])
        ds = EvalDataset.create_classical(
            name="cost_test",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = arena.evaluate(data=ds)

        costs = result.cost_analysis()
        assert "accuracy" in costs
        assert "precision" in costs
        assert costs["accuracy"]["n_scored"] >= 1
        assert "avg_cost" in costs["accuracy"]
        assert "total_latency" in costs["accuracy"]

    def test_correlation_matrix(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])
        ds = EvalDataset.create_classical(
            name="corr_test",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = arena.evaluate(data=ds)

        matrix = result.correlation_matrix()
        assert "accuracy" in matrix
        assert "precision" in matrix
        assert matrix["accuracy"]["accuracy"] == 1.0

    def test_agreement_scores(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])
        ds = EvalDataset.create_classical(
            name="agree_test",
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        result = arena.evaluate(data=ds, human_labels=[0.8])

        scores = result.agreement_scores()
        assert isinstance(scores, dict)

    def test_to_dict_includes_cost(self):
        from flowyml.evals.arena import JudgeArena
        from flowyml.evals.scorers.classification import Accuracy, Precision

        arena = JudgeArena(judges=[Accuracy(), Precision()])
        ds = EvalDataset.create_classical(
            name="dict_cost",
            predictions=[1, 0, 1],
            targets=[1, 0, 1],
        )
        result = arena.evaluate(data=ds)
        d = result.to_dict()
        assert "cost_analysis" in d


# ─── notify_if_regression Tests ─────────────────────────────────────


class TestNotifyIfRegression:
    """Test EvalResult.notify_if_regression()."""

    def test_no_regression_returns_false(self):
        baseline = EvalResult()
        baseline.summary = {"accuracy": 0.90}

        current = EvalResult()
        current.summary = {"accuracy": 0.95}

        assert current.notify_if_regression(baseline) is False

    def test_regression_returns_true(self):
        baseline = EvalResult()
        baseline.summary = {"accuracy": 0.95}

        current = EvalResult(experiment="test_exp")
        current.summary = {"accuracy": 0.80}

        # Should log the warning even if notification fails
        result = current.notify_if_regression(baseline, threshold=0.05)
        assert result is True


# ─── evaluate_traces Tests ──────────────────────────────────────────


class TestEvaluateTraces:
    """Test the top-level evaluate_traces convenience function."""

    def test_evaluate_traces_with_events(self):
        from flowyml.evals import evaluate_traces

        events = [
            {"input_data": "What is ML?", "output_data": "Machine Learning is..."},
            {"input_data": "What is AI?", "output_data": "AI is..."},
        ]
        result = evaluate_traces(trace_events=events, scorers=[])
        assert isinstance(result, EvalResult)
        assert result.metadata.get("source") == "trace_bridge"

    def test_evaluate_traces_empty(self):
        from flowyml.evals import evaluate_traces

        result = evaluate_traces(trace_events=[], scorers=[])
        assert isinstance(result, EvalResult)


# ─── Adapter Tests ──────────────────────────────────────────────────


class TestAdapterRegistry:
    """Test that adapter scorers are registered with namespaced keys."""

    def test_adapter_scorers_in_registry(self):
        from flowyml.evals.scorers import SCORER_REGISTRY

        adapter_keys = [k for k in SCORER_REGISTRY if "." in k]
        assert len(adapter_keys) == 12  # 4 deepeval + 4 ragas + 4 phoenix

    def test_get_scorer_deepeval_namespace(self):
        from flowyml.evals import get_scorer

        scorer = get_scorer("deepeval.hallucination")
        assert scorer.name == "deepeval.hallucination"
        assert scorer.scorer_type.value == "genai"

    def test_get_scorer_ragas_namespace(self):
        from flowyml.evals import get_scorer

        scorer = get_scorer("ragas.faithfulness")
        assert scorer.name == "ragas.faithfulness"
        assert scorer.scorer_type.value == "genai"

    def test_get_scorer_phoenix_namespace(self):
        from flowyml.evals import get_scorer

        scorer = get_scorer("phoenix.qa_correctness")
        assert scorer.name == "phoenix.qa_correctness"
        assert scorer.scorer_type.value == "genai"

    def test_list_scorers_includes_adapters(self):
        from flowyml.evals import list_scorers

        all_genai = list_scorers("genai")
        adapter_names = [s["name"] for s in all_genai if "." in s["name"]]
        assert "deepeval.hallucination" in adapter_names
        assert "ragas.faithfulness" in adapter_names
        assert "phoenix.toxicity" in adapter_names


class TestDeepEvalAdapter:
    """Test DeepEval adapter scorers (without real deepeval installed)."""

    def test_scorer_instantiation(self):
        from flowyml.evals import DeepEvalAnswerRelevancy, DeepEvalHallucination

        scorer = DeepEvalAnswerRelevancy(threshold=0.8)
        assert scorer.name == "deepeval.answer_relevancy"
        assert scorer.threshold == 0.8

        h = DeepEvalHallucination(model="gpt-4o", threshold=0.2)
        assert h.model == "gpt-4o"

    def test_scorer_requires_deepeval(self):
        from flowyml.evals import DeepEvalBias

        scorer = DeepEvalBias()
        # Without deepeval installed, score() should raise ImportError
        with pytest.raises(ImportError, match="deepeval"):
            scorer.score(inputs="test", outputs="response")

    def test_all_deepeval_scorers_exist(self):
        from flowyml.evals.scorers.deepeval_adapter import DEEPEVAL_SCORERS

        assert len(DEEPEVAL_SCORERS) == 4
        expected = {
            "deepeval.answer_relevancy",
            "deepeval.hallucination",
            "deepeval.bias",
            "deepeval.toxicity",
        }
        assert set(DEEPEVAL_SCORERS.keys()) == expected


class TestRagasAdapter:
    """Test RAGAS adapter scorers (without real ragas installed)."""

    def test_scorer_instantiation(self):
        from flowyml.evals import RagasFaithfulness, RagasContextRecall

        scorer = RagasFaithfulness(threshold=0.9)
        assert scorer.name == "ragas.faithfulness"
        assert scorer.threshold == 0.9

        cr = RagasContextRecall()
        assert cr.name == "ragas.context_recall"

    def test_scorer_requires_ragas(self):
        from flowyml.evals import RagasContextPrecision

        scorer = RagasContextPrecision()
        with pytest.raises(ImportError, match="ragas"):
            scorer.score(inputs="test", outputs="response", context=["ctx"])

    def test_all_ragas_scorers_exist(self):
        from flowyml.evals.scorers.ragas_adapter import RAGAS_SCORERS

        assert len(RAGAS_SCORERS) == 4
        expected = {
            "ragas.faithfulness",
            "ragas.context_precision",
            "ragas.context_recall",
            "ragas.answer_relevancy",
        }
        assert set(RAGAS_SCORERS.keys()) == expected


class TestPhoenixAdapter:
    """Test Phoenix adapter scorers (without real phoenix installed)."""

    def test_scorer_instantiation(self):
        from flowyml.evals import PhoenixToxicity, PhoenixSummarization

        scorer = PhoenixToxicity(model="openai/gpt-4o", threshold=0.1)
        assert scorer.name == "phoenix.toxicity"
        assert scorer.model == "openai/gpt-4o"

        s = PhoenixSummarization()
        assert s.name == "phoenix.summarization"

    def test_scorer_requires_phoenix(self):
        from flowyml.evals import PhoenixQACorrectness

        scorer = PhoenixQACorrectness()
        with pytest.raises(ImportError, match="arize-phoenix-evals"):
            scorer.score(inputs="test", outputs="response")

    def test_all_phoenix_scorers_exist(self):
        from flowyml.evals.scorers.phoenix_adapter import PHOENIX_SCORERS

        assert len(PHOENIX_SCORERS) == 4
        expected = {
            "phoenix.hallucination",
            "phoenix.toxicity",
            "phoenix.qa_correctness",
            "phoenix.summarization",
        }
        assert set(PHOENIX_SCORERS.keys()) == expected


class TestEvalsUtils:
    """Test shared evaluation utilities."""

    def test_safe_import_success(self):
        from flowyml.evals.utils import safe_import

        mod = safe_import("json", package="json")
        assert hasattr(mod, "dumps")

    def test_safe_import_failure(self):
        from flowyml.evals.utils import safe_import

        with pytest.raises(ImportError, match="nonexistent_pkg"):
            safe_import("nonexistent_pkg", package="nonexistent_pkg")

    def test_normalize_score(self):
        from flowyml.evals.utils import normalize_score

        assert normalize_score(0.5) == 0.5
        assert normalize_score(0.0) == 0.0
        assert normalize_score(1.0) == 1.0
        assert normalize_score(50, min_val=0, max_val=100) == 0.5
        assert normalize_score(0.8, invert=True) == pytest.approx(0.2)

    def test_format_rationale(self):
        from flowyml.evals.utils import format_rationale

        r = format_rationale("test", 0.85, source="TestProvider")
        assert "[TestProvider]" in r
        assert "0.8500" in r

        r2 = format_rationale("test", 0.9, details="extra info")
        assert "extra info" in r2
