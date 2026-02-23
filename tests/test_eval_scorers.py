"""Tests for FlowyML Evaluation Scorers.

Tests the Scorer protocol, all 17 built-in scorers (7 classification,
6 regression, 4 GenAI), and the scorer registry.
"""

import pytest
from unittest.mock import patch, MagicMock

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType


# ─── ScorerFeedback Tests ─────────────────────────────────────────────


class TestScorerFeedback:
    """Test the ScorerFeedback data model."""

    def test_create_basic(self):
        fb = ScorerFeedback(name="accuracy", value=0.95)
        assert fb.name == "accuracy"
        assert fb.value == 0.95
        assert fb.passed is None
        assert fb.rationale is None

    def test_create_with_all_fields(self):
        fb = ScorerFeedback(
            name="toxicity",
            value=0.1,
            passed=True,
            rationale="Content is clean",
            metadata={"model": "gpt-4"},
        )
        assert fb.passed is True
        assert fb.rationale == "Content is clean"
        assert fb.metadata["model"] == "gpt-4"

    def test_to_dict(self):
        fb = ScorerFeedback(name="f1", value=0.88, passed=True)
        d = fb.to_dict()
        assert d["name"] == "f1"
        assert d["value"] == 0.88
        assert d["passed"] is True

    def test_numeric_check(self):
        fb = ScorerFeedback(name="acc", value=0.9)
        assert isinstance(fb.value, (int, float))

        fb2 = ScorerFeedback(name="label", value="high")
        assert not isinstance(fb2.value, (int, float))


# ─── Classification Scorer Tests ──────────────────────────────────────


class TestClassificationScorers:
    """Test all 7 classification scorers."""

    def test_accuracy_basic(self):
        from flowyml.evals.scorers.classification import Accuracy

        scorer = Accuracy()
        assert scorer.name == "accuracy"
        assert scorer.scorer_type == ScorerType.CLASSIFICATION

        result = scorer.score(
            predictions=[1, 0, 1, 1, 0],
            targets=[1, 0, 1, 0, 0],
        )
        assert isinstance(result, ScorerFeedback)
        assert result.value == 0.8  # 4/5 correct
        assert result.name == "accuracy"

    def test_accuracy_with_threshold(self):
        from flowyml.evals.scorers.classification import Accuracy

        scorer = Accuracy(threshold=0.9)
        result = scorer.score(predictions=[1, 0, 1, 1, 0], targets=[1, 0, 1, 0, 0])
        assert result.passed is False  # 0.8 < 0.9

        scorer2 = Accuracy(threshold=0.7)
        result2 = scorer2.score(predictions=[1, 0, 1, 1, 0], targets=[1, 0, 1, 0, 0])
        assert result2.passed is True  # 0.8 >= 0.7

    def test_precision(self):
        from flowyml.evals.scorers.classification import Precision

        scorer = Precision()
        result = scorer.score(predictions=[1, 1, 1, 0, 0], targets=[1, 0, 1, 0, 0])
        assert isinstance(result.value, float)
        assert 0 <= result.value <= 1

    def test_recall(self):
        from flowyml.evals.scorers.classification import Recall

        scorer = Recall()
        result = scorer.score(predictions=[1, 1, 1, 0, 0], targets=[1, 0, 1, 0, 0])
        assert isinstance(result.value, float)
        assert 0 <= result.value <= 1

    def test_f1_score(self):
        from flowyml.evals.scorers.classification import F1Score

        scorer = F1Score()
        result = scorer.score(predictions=[1, 1, 1, 0, 0], targets=[1, 0, 1, 0, 0])
        assert isinstance(result.value, float)
        assert 0 <= result.value <= 1
        assert result.name == "f1_score"

    def test_logloss(self):
        from flowyml.evals.scorers.classification import LogLoss

        scorer = LogLoss()
        result = scorer.score(predictions=[0.9, 0.1, 0.8, 0.3], targets=[1, 0, 1, 0])
        assert isinstance(result.value, float)
        assert result.value > 0

    def test_confusion_matrix(self):
        from flowyml.evals.scorers.classification import ConfusionMatrixScorer

        scorer = ConfusionMatrixScorer()
        result = scorer.score(
            predictions=[1, 0, 1, 1, 0, 0, 1, 0],
            targets=[1, 0, 0, 1, 0, 1, 1, 0],
        )
        assert isinstance(result.value, (int, float))  # Returns accuracy as value
        assert "matrix" in result.metadata  # Matrix stored in metadata

    def test_score_batch(self):
        from flowyml.evals.scorers.classification import Accuracy

        scorer = Accuracy()
        batch = [
            {"predictions": [1, 0, 1], "targets": [1, 0, 1]},
            {"predictions": [1, 0, 0], "targets": [1, 0, 1]},
        ]
        results = scorer.score_batch(batch)
        assert len(results) == 2
        assert results[0].value == 1.0  # perfect
        assert results[1].value < 1.0  # imperfect


# ─── Regression Scorer Tests ─────────────────────────────────────────


class TestRegressionScorers:
    """Test all 6 regression scorers."""

    def test_mse(self):
        from flowyml.evals.scorers.regression import MSE

        scorer = MSE()
        result = scorer.score(predictions=[3, -0.5, 2, 7], targets=[2.5, 0.0, 2, 8])
        assert isinstance(result.value, float)
        assert result.value >= 0

    def test_rmse(self):
        from flowyml.evals.scorers.regression import RMSE

        scorer = RMSE()
        result = scorer.score(predictions=[3, -0.5, 2, 7], targets=[2.5, 0.0, 2, 8])
        assert isinstance(result.value, float)
        assert result.value >= 0

    def test_mae(self):
        from flowyml.evals.scorers.regression import MAE

        scorer = MAE()
        result = scorer.score(predictions=[3, -0.5, 2, 7], targets=[2.5, 0.0, 2, 8])
        assert isinstance(result.value, float)
        assert result.value >= 0

    def test_r2_score(self):
        from flowyml.evals.scorers.regression import R2Score

        scorer = R2Score()
        result = scorer.score(predictions=[3, 2, 5, 7], targets=[3, 2, 5, 7])
        assert isinstance(result.value, float)
        assert result.value == pytest.approx(1.0)

    def test_mape(self):
        from flowyml.evals.scorers.regression import MAPE

        scorer = MAPE()
        result = scorer.score(predictions=[10, 20, 30], targets=[10, 20, 30])
        assert isinstance(result.value, float)
        assert result.value == pytest.approx(0.0)

    def test_max_error(self):
        from flowyml.evals.scorers.regression import MaxError

        scorer = MaxError()
        result = scorer.score(predictions=[3, 2, 7], targets=[3, 2, 5])
        assert isinstance(result.value, float)
        assert result.value == pytest.approx(2.0)

    def test_regression_lower_is_better(self):
        """Regression scorers should set lower_is_better metadata."""
        from flowyml.evals.scorers.regression import MSE

        scorer = MSE()
        result = scorer.score(predictions=[3, 2], targets=[2, 2])
        assert result.metadata.get("lower_is_better") is True


# ─── Scorer Registry Tests ───────────────────────────────────────────


class TestScorerRegistry:
    """Test the scorer registry and auto-discovery."""

    def test_get_scorer_by_name(self):
        from flowyml.evals.scorers import get_scorer

        scorer = get_scorer("accuracy")
        assert scorer is not None
        assert scorer.name == "accuracy"

    def test_get_scorer_lowercase(self):
        from flowyml.evals.scorers import get_scorer

        scorer = get_scorer("accuracy")
        assert scorer is not None
        assert scorer.name == "accuracy"

    def test_get_scorer_not_found(self):
        from flowyml.evals.scorers import get_scorer

        with pytest.raises(ValueError):
            get_scorer("nonexistent_scorer_xyz")

    def test_list_scorers(self):
        from flowyml.evals.scorers import list_scorers

        all_scorers = list_scorers()
        assert len(all_scorers) >= 17  # at least our 17 built-in

    def test_list_scorers_by_type(self):
        from flowyml.evals.scorers import list_scorers

        classification = list_scorers("classification")
        assert all(s["type"] == "classification" for s in classification)
        assert len(classification) == 7

    def test_register_custom_scorer(self):
        from flowyml.evals.scorers import register_scorer, get_scorer

        class MyScorer(Scorer):
            name = "my_custom_test_scorer"
            scorer_type = ScorerType.CUSTOM

            def score(self, **kwargs):
                return ScorerFeedback(name=self.name, value=1.0)

        register_scorer("my_custom_test_scorer", MyScorer)
        retrieved = get_scorer("my_custom_test_scorer")
        assert retrieved.name == "my_custom_test_scorer"


# ─── Custom Scorer Factory Tests ─────────────────────────────────────


class TestCustomScorerFactories:
    """Test make_scorer() and make_judge()."""

    def test_make_scorer(self):
        from flowyml.evals.scorers.custom import make_scorer

        def my_metric(predictions, targets):
            correct = sum(p == t for p, t in zip(predictions, targets))
            return correct / len(predictions)

        scorer = make_scorer("custom_accuracy", my_metric)
        result = scorer.score(predictions=[1, 0, 1], targets=[1, 0, 1])
        assert result.value == 1.0
        assert result.name == "custom_accuracy"

    def test_make_scorer_from_genai_fn(self):
        from flowyml.evals.scorers.custom import make_scorer

        def quality_check(inputs, outputs, **kwargs):
            return 0.8 if len(str(outputs)) > 10 else 0.3

        scorer = make_scorer("quality", quality_check)
        result = scorer.score(inputs="hello", outputs="This is a long response")
        assert result.value == 0.8

    def test_make_judge_creates_scorer(self):
        from flowyml.evals.scorers.custom import make_judge

        judge = make_judge(
            name="test_judge",
            instructions="Evaluate quality",
            model="gpt-4",
        )
        assert judge.name == "test_judge"
        assert judge.scorer_type == ScorerType.GENAI
