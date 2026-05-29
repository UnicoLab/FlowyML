---
title: "Decorators — FlowyML"
description: "API reference for FlowyML decorators: @step, @dynamic, @map_task, and more."
---

# Decorators API 🎀

Decorators are the **primary API surface** of FlowyML. By annotating a plain Python function with `@step`, `@trace_llm`, or similar decorators, you opt the function into the framework's execution, caching, lineage-tracking, and monitoring capabilities — all without modifying the function body. This section documents every decorator, its parameters, and its runtime behaviour.

## `@step`

::: flowyml.core.step.step
    options:
        show_root_heading: false

## `@trace_llm`

::: flowyml.monitoring.llm.trace_llm
    options:
        show_root_heading: false

---

## See Also

- [Step API](step.md) — full reference for the `Step` class produced by the `@step` decorator
- [Steps Guide](../core/steps.md) — conceptual guide on writing and composing steps
