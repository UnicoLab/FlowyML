"""Serving-runtime image builders (FastAPI, Triton, TensorFlow Serving)."""

from __future__ import annotations

from flowyml.deployment.runtimes.base import (
    BuildContext,
    ServingImageBuilder,
    get_serving_builder,
    register_serving_builder,
)

# Import concrete builders so they self-register on package import.
from flowyml.deployment.runtimes.fastapi import FastAPIServingBuilder
from flowyml.deployment.runtimes.tensorflow_serving import TensorFlowServingBuilder
from flowyml.deployment.runtimes.triton import TritonServingBuilder

__all__ = [
    "BuildContext",
    "ServingImageBuilder",
    "get_serving_builder",
    "register_serving_builder",
    "FastAPIServingBuilder",
    "TritonServingBuilder",
    "TensorFlowServingBuilder",
]
