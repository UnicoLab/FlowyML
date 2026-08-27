"""Source-level guards for frontend failure modes that have already bitten.

These are lint-style checks rather than behavioural tests: they run in the
Python suite so the guarantees hold in CI even though the frontend has its own
toolchain.  Each one corresponds to a defect that reached the running UI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO_ROOT / "flowyml" / "ui" / "frontend" / "src"

pytestmark = pytest.mark.skipif(
    not FRONTEND_SRC.exists(),
    reason="frontend sources not present",
)


def _source_files():
    """Application sources only.

    Test files are excluded: they are not shipped to a browser, and they
    legitimately mention the very patterns these guards forbid when explaining
    what they exist to prevent.
    """
    for path in sorted(FRONTEND_SRC.rglob("*")):
        if path.suffix not in {".js", ".jsx"} or not path.is_file():
            continue
        if "node_modules" in path.parts or "dist" in path.parts:
            continue
        if "__tests__" in path.parts or path.name.endswith((".test.js", ".test.jsx")):
            continue
        yield path


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_dates_are_never_formatted_without_a_validity_check():
    """``format(new Date(x))`` throws when x is not a parseable date.

    date-fns raises ``RangeError: Invalid time value`` for an invalid date, so
    a single malformed timestamp in the data took down the whole page. This was
    reproduced against a running server: one run row with
    ``start_time="unknown"`` replaced the entire Dashboard with the error
    boundary. ``formatDate`` from utils/date returns "-" instead.

    A null date is just as bad in the other direction: ``new Date(null)`` is
    the Unix epoch, so an unset timestamp rendered as "Jan 1, 1970" rather than
    as missing.
    """
    offenders = []
    for path in _source_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bformat\(\s*new Date\(", line):
                offenders.append(f"{_relative(path)}:{number}: {line.strip()[:90]}")

    assert not offenders, (
        "Use formatDate() from utils/date instead of format(new Date(...)), "
        "which throws on an invalid date:\n" + "\n".join(f"  {o}" for o in offenders)
    )


def test_websocket_urls_are_built_through_the_shared_helper():
    """Hardcoding window.location.host breaks remote-execution deployments.

    In remote mode the API lives on a different origin than the page, so a
    socket opened against the page's own host connected to the wrong server and
    silently degraded to polling. ``getWebSocketUrl`` mirrors ``getBaseUrl``.
    """
    offenders = []
    for path in _source_files():
        if path.name == "api.js":
            continue  # the helper itself legitimately reads window.location
        text = path.read_text(encoding="utf-8")
        if "new WebSocket(" not in text:
            continue
        if "window.location.host" in text:
            offenders.append(_relative(path))

    assert not offenders, (
        "These files build a WebSocket URL from window.location.host instead of " f"getWebSocketUrl(): {offenders}"
    )


def test_api_calls_go_through_the_shared_fetch_wrapper():
    """A bare fetch() ignores the configured remote API base URL.

    ``fetchApi`` resolves the base URL from /api/config, which is what makes
    remote-execution mode work at all. A raw ``fetch('/api/...')`` always hits
    the page's own origin.
    """
    offenders = []
    allowed = {"api.js"}  # bootstraps the config itself, so it cannot use fetchApi
    for path in _source_files():
        if path.name in allowed:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?<!\w)fetch\(\s*[`'\"]/api/", line):
                offenders.append(f"{_relative(path)}:{number}: {line.strip()[:90]}")

    assert not offenders, "Use fetchApi() so the configured remote API base URL is honoured:\n" + "\n".join(
        f"  {o}" for o in offenders
    )


def test_routes_are_code_split():
    """The router must lazy-load pages, not import them eagerly.

    Importing all 24 pages statically produced a single 7.9 MB bundle that
    every visitor downloaded before first paint.
    """
    router = FRONTEND_SRC / "router" / "index.jsx"
    text = router.read_text(encoding="utf-8")

    eager = re.findall(r"^import \{ \w+ \} from '\.\./app/[^']+';$", text, re.M)
    assert not eager, f"Router imports pages eagerly instead of lazily: {eager}"

    lazy_count = len(re.findall(r"lazy\(\(\) => import\(", text))
    assert lazy_count >= 20, f"Expected the router to lazy-load its pages, found {lazy_count}"


def test_the_llm_runtime_is_not_in_the_initial_bundle():
    """@mlc-ai/web-llm is 5.4 MB and only needed once the assistant starts."""
    offenders = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            # A static `import ... from '@mlc-ai/web-llm'`, as opposed to a
            # dynamic `await import('@mlc-ai/web-llm')`.
            if re.match(r"^\s*import\s+.*from\s+['\"]@mlc-ai/web-llm['\"]", line):
                offenders.append(f"{_relative(path)}:{number}")

    assert not offenders, (
        "@mlc-ai/web-llm must be imported dynamically so it stays out of the "
        f"initial bundle; statically imported in: {offenders}"
    )
