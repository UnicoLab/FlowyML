"""Shared pytest fixtures for test isolation.

Clears global singletons (step registry, stack registry, stack manager,
plugin config) before each test to prevent cross-test contamination when
steps/stacks are registered by different test functions or when config
files left by parallel xdist workers leak into other tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _clear_global_registries():
    """Auto-clear global registries before and after every test.

    This prevents:
    - 'Step X is already registered' errors across tests
    - Stale active-stack state leaking executor=None into unrelated tests
    - Filesystem-based stack/flowyml.yaml config leaking between xdist workers
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
