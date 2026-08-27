r"""The PR-title check in CI must use a pattern that actually compiles.

``.github/workflows/PRECOMMITS.yml`` passed its ``regexp`` through a
single-quoted YAML scalar, which has no backslash escapes, so every ``\\`` in
the pattern reached JavaScript as a literal backslash. The character class
``[a-z,A-Z,0-9,\\-,\\_,\\/,:]`` therefore contained a range from ``\`` (0x5C)
to ``,`` (0x2C) and ``new RegExp`` threw::

    SyntaxError: Invalid regular expression: Range out of order in character class

The action crashed before reading any title, so the job failed in five seconds
whatever the pull request was called - and the ``pre-commit run`` step after it
never executed. Nothing in CI could pass this workflow.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "PRECOMMITS.yml"
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"

pytestmark = pytest.mark.skipif(not WORKFLOW.exists(), reason="workflow not present")


def _pr_title_pattern() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["pre-commit-checks"]["steps"]
    step = next(s for s in steps if s.get("name") == "Check Pull Request Title")
    return step["with"]["regexp"]


def _commit_msg_pattern() -> str:
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text(encoding="utf-8"))
    hook = next(h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "validate-commit-msg")
    return hook["entry"]


def test_the_pr_title_pattern_compiles():
    """A pattern that does not compile fails every pull request."""
    re.compile(_pr_title_pattern())


def test_the_pr_title_pattern_matches_the_commit_message_hook():
    """One convention, one pattern.

    A title that the local ``commit-msg`` hook accepts must not be rejected by
    CI, and vice versa; the two drift apart the moment they are written twice.
    """
    assert _pr_title_pattern() == _commit_msg_pattern()


@pytest.mark.parametrize(
    "title",
    [
        "refactor: production readiness audit",
        "fix(core): restore integrations re-exports",
        "feat(ui/backend): add the security module",
        "docs: document model serving",
        "maint: sync version to 2.2.0 across all sources [skip ci]",
        "fix!: drop the deprecated endpoint",
    ],
)
def test_titles_the_project_already_uses_are_accepted(title):
    """Every one of these appears in the history of ``main``."""
    assert re.match(_pr_title_pattern(), title), f"{title!r} is rejected by the PR-title check"


@pytest.mark.parametrize(
    "title",
    [
        "chore: not one of the allowed types",
        "a title with no type at all",
        "feat:no space after the colon",
        "feat: ",
    ],
)
def test_malformed_titles_are_still_rejected(title):
    """The check has to keep checking something."""
    assert not re.match(_pr_title_pattern(), title), f"{title!r} should not pass the PR-title check"
