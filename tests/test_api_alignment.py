"""Guard the contract between the React frontend and the FastAPI backend.

Every URL the frontend builds is extracted from the source and matched against
the backend's own OpenAPI schema.  A page that calls an endpoint nobody
implemented fails silently at runtime - the UI just renders its fallback - so
the mismatch is invisible until a user notices the numbers are wrong.  That is
exactly how ``/api/execution/info`` came to display a hard-coded version string
and how the "Revoke" button on the API tokens page came to do nothing at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO_ROOT / "flowyml" / "ui" / "frontend" / "src"

#: Placeholder standing in for a `${...}` template-literal interpolation.
INTERPOLATION = "\x00"

#: Locates the opening quote of a `fetch(...)` / `fetchApi(...)` URL argument.
CALL_START_RE = re.compile(r"\b(?:fetchApi|fetch)\s*\(\s*([`'\"])(?=/api|/ws)")

#: Finds `method: 'POST'` in the options object that follows the URL.
METHOD_RE = re.compile(r"^\s*,\s*\{[^}]{0,400}?method\s*:\s*['\"`](\w+)", re.S)


def _read_string_literal(source: str, quote: str, start: int) -> tuple[str, int]:
    """Read a JS string literal, honouring nested template interpolations.

    A template literal may contain further backtick-quoted strings inside its
    ``${...}`` holes, as in ``/api/evaluations/list${qs ? `?${qs}` : ''}``. A
    naive "scan to the next backtick" would truncate that URL mid-expression
    and report a perfectly valid call as unimplemented, so interpolation depth
    is tracked explicitly.

    Returns the literal's contents and the index just past its closing quote.
    """
    out: list[str] = []
    i = start
    depth = 0  # nesting level inside ${ ... }
    while i < len(source):
        char = source[i]
        if char == "\\":
            out.append(source[i : i + 2])
            i += 2
            continue
        if quote == "`" and char == "$" and source[i + 1 : i + 2] == "{":
            depth += 1
            out.append("${")
            i += 2
            continue
        if depth and char == "}":
            depth -= 1
            out.append("}")
            i += 1
            continue
        if char == quote and depth == 0:
            return "".join(out), i + 1
        if char == "\n" and quote != "`":
            break  # unterminated non-template string
        out.append(char)
        i += 1
    return "".join(out), i


@pytest.fixture(scope="module")
def backend_routes() -> dict[str, set[str]]:
    """Map every backend path to the HTTP methods it accepts."""
    from flowyml.ui.backend.main import app

    schema = app.openapi()
    return {
        path: {m.upper() for m in operations if m in {"get", "post", "put", "patch", "delete"}}
        for path, operations in schema["paths"].items()
    }


def _iter_frontend_calls():
    """Yield ``(url, method, source_file)`` for every API call in the frontend."""
    for path in sorted(FRONTEND_SRC.rglob("*")):
        if path.suffix not in {".js", ".jsx"} or not path.is_file():
            continue
        if "node_modules" in path.parts or "dist" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        for match in CALL_START_RE.finditer(source):
            quote = match.group(1)
            url, end = _read_string_literal(source, quote, match.end())
            method_match = METHOD_RE.match(source[end: end + 500])
            method = method_match.group(1).upper() if method_match else "GET"
            yield url, method, path.relative_to(REPO_ROOT)


def _mask_interpolations(url: str) -> str:
    """Replace every balanced ``${...}`` hole with a single marker character."""
    out: list[str] = []
    i = 0
    while i < len(url):
        if url.startswith("${", i):
            depth = 1
            i += 2
            while i < len(url) and depth:
                if url[i] == "{":
                    depth += 1
                elif url[i] == "}":
                    depth -= 1
                i += 1
            out.append(INTERPOLATION)
            continue
        out.append(url[i])
        i += 1
    return "".join(out)


def _candidate_paths(url: str) -> list[str]:
    """Normalize a JS template literal into the concrete paths it can produce."""
    marked = _mask_interpolations(url)
    # Only a literal `?` outside an interpolation starts the query string.
    marked = marked.split("?", 1)[0]

    candidates = [marked]
    # An interpolation glued onto the end of a literal segment
    # (`/api/x/scorers${qs}`) is a query string assembled elsewhere.
    if marked.endswith(INTERPOLATION) and not marked.endswith("/" + INTERPOLATION):
        candidates.append(marked[:-1])

    resolved = []
    for candidate in candidates:
        trimmed = candidate.rstrip("/") or "/"
        resolved.append(trimmed)
        # FastAPI's redirect_slashes makes `/x` and `/x/` equivalent.
        if trimmed != "/":
            resolved.append(trimmed + "/")
    return resolved


def _matching_routes(candidate: str, backend_routes: dict[str, set[str]]) -> list[str]:
    """Backend paths that *candidate* could resolve to, compared segment-wise."""
    segments = candidate.strip("/").split("/")
    matches = []

    for route, _methods in backend_routes.items():
        route_segments = route.strip("/").split("/")
        if len(route_segments) != len(segments):
            continue

        for actual, expected in zip(segments, route_segments):
            if expected.startswith("{") and expected.endswith("}"):
                continue  # a path parameter accepts anything
            if actual == expected:
                continue
            if INTERPOLATION in actual:
                continue  # an interpolation may expand to this literal
            break
        else:
            matches.append(route)

    return matches


def _resolve(url: str, backend_routes: dict[str, set[str]]) -> tuple[list[str], set[str]]:
    routes: list[str] = []
    methods: set[str] = set()
    for candidate in _candidate_paths(url):
        for route in _matching_routes(candidate, backend_routes):
            routes.append(route)
            methods |= backend_routes[route]
    return routes, methods


@pytest.mark.skipif(not FRONTEND_SRC.exists(), reason="frontend sources not present")
def test_every_frontend_call_hits_an_implemented_route(backend_routes):
    """No page may call an endpoint the backend does not implement."""
    unimplemented = []
    for url, method, source in _iter_frontend_calls():
        routes, _ = _resolve(url, backend_routes)
        if not routes:
            unimplemented.append(f"{method} {url}  ({source})")

    assert not unimplemented, "Frontend calls with no backend route:\n" + "\n".join(
        f"  {entry}" for entry in unimplemented
    )


@pytest.mark.skipif(not FRONTEND_SRC.exists(), reason="frontend sources not present")
def test_every_frontend_call_uses_a_supported_method(backend_routes):
    """A route that exists but rejects the verb still breaks the page."""
    wrong_method = []
    for url, method, source in _iter_frontend_calls():
        routes, methods = _resolve(url, backend_routes)
        if routes and method not in methods:
            wrong_method.append(
                f"{method} {url}  ({source}) -> {sorted(set(routes))} accepts {sorted(methods)}",
            )

    assert not wrong_method, "Frontend calls using an unsupported method:\n" + "\n".join(
        f"  {entry}" for entry in wrong_method
    )


@pytest.mark.skipif(not FRONTEND_SRC.exists(), reason="frontend sources not present")
def test_alignment_check_actually_finds_calls():
    """Protect the two tests above from silently passing on an empty scan."""
    calls = list(_iter_frontend_calls())
    assert len(calls) > 50, f"Only found {len(calls)} frontend API calls; the extractor is broken"


def test_endpoints_the_ui_depends_on_exist(backend_routes):
    """Explicit list of routes whose absence previously produced silent failures."""
    required = {
        "/api/execution/info": "GET",
        "/api/execution/tokens": "GET",
        "/api/execution/tokens/{token_ref}": "DELETE",
        "/api/ai/context/{page_type}/{resource_id}": "GET",
        "/api/health": "GET",
        "/api/config": "GET",
    }
    missing = {
        path: verb
        for path, verb in required.items()
        if path not in backend_routes or verb not in backend_routes[path]
    }
    assert not missing, f"Required endpoints missing or wrong method: {missing}"


def _exact_route_matchers(backend_routes: dict[str, set[str]]):
    """Regexes that match a path *including* its exact trailing slash."""
    matchers = []
    for route in backend_routes:
        pattern = re.escape(route)
        pattern = re.sub(r"\\\{[^}]*\\\}", "[^/]+", pattern)
        matchers.append((re.compile("^" + pattern + "$"), route))
    return matchers


@pytest.mark.skipif(not FRONTEND_SRC.exists(), reason="frontend sources not present")
def test_no_frontend_call_depends_on_a_trailing_slash_redirect(backend_routes):
    """Calls must hit the declared path, not rely on FastAPI's 307.

    ``redirect_slashes`` papers over a mismatch at the cost of a second round
    trip for every request, and it depends on the client following redirects -
    which a POST only survives because 307 preserves the body. It also breaks
    outright behind any proxy that does not forward redirects. This was live:
    five pages issued a redirected request on every load.
    """
    matchers = _exact_route_matchers(backend_routes)

    def matches_exactly(path: str) -> bool:
        probe = path.replace(INTERPOLATION, "X")
        return any(rx.match(probe) for rx, _ in matchers)

    redirected = []
    for url, method, source in _iter_frontend_calls():
        literal = _mask_interpolations(url).split("?", 1)[0]
        if matches_exactly(literal):
            continue
        alternative = literal[:-1] if literal.endswith("/") else literal + "/"
        if matches_exactly(alternative):
            redirected.append(f"{method} {url}  ({source}) -> declared as {alternative}")

    assert not redirected, (
        "These frontend calls only work via a trailing-slash redirect:\n"
        + "\n".join(f"  {entry}" for entry in redirected)
    )
