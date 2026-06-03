"""Enterprise Stack Registry – source implementations.

This sub-package provides pluggable *sources* from which enterprise stack
definitions can be discovered and loaded.

Each source implements the :class:`StackSource` protocol defined in
:mod:`~flowyml.stacks.enterprise.sources.base` and is instantiated by the
:func:`parse_source_uri` factory.

Supported source types
======================

==================  =====================================================
Source              Description
==================  =====================================================
``LocalStackSource``    Scans local filesystem directories for YAML files.
``GitStackSource``      Clones / fetches Git repos (GitHub, GitLab, …).
``HTTPStackSource``     Fetches a single YAML file over HTTP(S).
``RegistryIndexSource`` Resolves stacks via a ``RegistryIndex`` catalogue.
==================  =====================================================

Quick-start::

    from flowyml.stacks.enterprise.sources import parse_source_uri

    source = parse_source_uri("github://acme/stacks@v1.2.0")
    refs = source.list_stacks()
    stack = source.load_stack("aml_cpu_small")
"""

from __future__ import annotations

from flowyml.stacks.enterprise.sources.base import StackSource, parse_source_uri
from flowyml.stacks.enterprise.sources.git import GitStackSource
from flowyml.stacks.enterprise.sources.http import HTTPStackSource
from flowyml.stacks.enterprise.sources.local import LocalStackSource
from flowyml.stacks.enterprise.sources.registry_index import RegistryIndexSource

__all__ = [
    # Protocol + factory
    "StackSource",
    "parse_source_uri",
    # Concrete sources
    "GitStackSource",
    "HTTPStackSource",
    "LocalStackSource",
    "RegistryIndexSource",
]
