"""Shared pytest fixtures for test isolation.

Clears global singletons (step registry, stack registry, stack manager,
plugin config) before each test to prevent cross-test contamination when
steps/stacks are registered by different test functions or when config
files left by parallel xdist workers leak into other tests.
"""

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_cache_dir_per_worker(request):
    """Give every xdist worker its own step cache directory.

    ``_reset_all`` deletes the cache directory between tests. With the default
    relative ``.flowyml/cache`` every worker shares one directory, so one
    worker's delete raced another worker's create:
    ``Path.mkdir(parents=True, exist_ok=True)`` re-raises ``FileExistsError``
    when the directory disappears between its failed ``mkdir`` and its
    ``is_dir()`` recheck. That produced an intermittent failure in whichever
    test happened to be constructing a cache at the time.

    Isolating per worker also keeps the suite from deleting a developer's real
    ``.flowyml/cache``.
    """
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    with tempfile.TemporaryDirectory(prefix=f"flowyml-cache-{worker_id}-") as cache_dir:
        previous = os.environ.get("FLOWYML_CACHE_DIR")
        os.environ["FLOWYML_CACHE_DIR"] = cache_dir
        try:
            yield cache_dir
        finally:
            if previous is None:
                os.environ.pop("FLOWYML_CACHE_DIR", None)
            else:
                os.environ["FLOWYML_CACHE_DIR"] = previous


@pytest.fixture(autouse=True)
def _clear_global_registries():
    """Auto-clear global registries before and after every test.

    This prevents:
    - 'Step X is already registered' errors across tests
    - Stale active-stack state leaking executor=None into unrelated tests
    - Filesystem-based stack/flowyml.yaml config leaking between xdist workers
    - Cached step outputs from previous tests contaminating current tests
    - A memoised metadata-store engine bound to a previous test's temp database
    """
    _reset_all()
    yield
    _reset_all()


def _reset_all():
    """Reset all global singletons to a clean state."""
    from flowyml.core.step import clear_step_registry

    # 1. Clear step registry
    clear_step_registry()

    # 2. Reset the StackRegistry global singleton
    try:
        import flowyml.stacks.registry as stack_reg

        stack_reg._global_registry = None
    except Exception:
        pass

    # 3. Reset the StackManager singleton (reads flowyml.yaml on init)
    try:
        from flowyml.plugins.stack_config import StackManager

        StackManager.reset()
    except Exception:
        pass

    # 4. Reset the PluginConfig global (reads flowyml.yaml on init)
    try:
        import flowyml.plugins.config as plugin_cfg

        plugin_cfg._config = None
    except Exception:
        pass

    # 5. Reset the UI backend's cached metadata store.
    # dependencies.get_store() memoises a SQLAlchemy engine for the process,
    # which is right in production (one connection pool) but means a store
    # built against one test's temporary config would serve every later test,
    # letting rows written by one test appear in another's queries.
    try:
        import flowyml.ui.backend.dependencies as ui_deps

        ui_deps._store = None
    except Exception:
        pass

    # 6. Clear the cache store to prevent stale cached step outputs
    # from leaking between tests (e.g., evaluate_model returning 0.95
    # in one test being served from cache in another test expecting 0.85)
    try:
        from flowyml.utils.config import get_config
        import shutil

        cache_dir = get_config().cache_dir
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
    except Exception:
        pass
