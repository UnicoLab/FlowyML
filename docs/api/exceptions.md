---
title: "Exceptions — FlowyML"
description: "API reference for FlowyML exception classes and error types."
---

# Exceptions API 🚨

FlowyML defines a structured exception hierarchy so you can catch errors at the right level of granularity. All custom exceptions inherit from a common base class, making it easy to write broad `except` clauses for framework errors while still allowing fine-grained handling of specific failure modes such as missing artifacts, invalid configurations, or orchestrator timeouts.

Custom exceptions thrown by flowyml.

## Error Handling Module

::: flowyml.core.error_handling
    options:
        show_root_heading: false

---

## See Also

- [Error Handling Guide](../advanced/error-handling.md) — best practices for catching and recovering from errors in pipelines
