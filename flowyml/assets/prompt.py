"""Prompt Asset - Represents LLM prompt templates with versioning and lineage."""

from datetime import datetime
from typing import Any

from flowyml.assets.base import Asset


class Prompt(Asset):
    r"""Prompt asset for LLM and GenAI workflows.

    Tracks prompt templates, variables, model configuration, and enables
    lineage between prompts and the generated outputs they produce.

    Supported patterns:
        - Simple string prompts
        - Templated prompts with ``{variable}`` substitution
        - Chat-style message lists (system/user/assistant roles)
        - Prompt chains (multiple prompts linked via lineage)

    Example:
        >>> # Simple prompt
        >>> prompt = Prompt(
        ...     name="summarize",
        ...     template="Summarize the following text:\n\n{text}",
        ... )
        >>> rendered = prompt.render(text="Hello world")

        >>> # Chat-style prompt
        >>> prompt = Prompt.create(
        ...     template=[
        ...         {"role": "system", "content": "You are a helpful assistant."},
        ...         {"role": "user", "content": "Explain {topic} in simple terms."},
        ...     ],
        ...     name="explain",
        ...     model="gpt-4",
        ...     temperature=0.7,
        ... )

        >>> # With factory method
        >>> prompt = Prompt.create(
        ...     template="Classify this review: {review}",
        ...     name="classifier",
        ...     model="gpt-3.5-turbo",
        ...     max_tokens=50,
        ... )
    """

    def __init__(
        self,
        name: str,
        template: str | list[dict[str, str]] | None = None,
        version: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
    ):
        """Initialize Prompt.

        Args:
            name: Prompt name (used as an identifier / version key).
            template: The prompt template. Either a plain string with
                ``{variable}`` placeholders, or a list of chat messages
                (each a dict with ``role`` and ``content`` keys).
            version: Version string (default ``v1.0.0``).
            model: Target LLM model name (e.g. ``"gpt-4"``).
            temperature: Sampling temperature for generation.
            max_tokens: Maximum tokens for generation.
            parent: Parent asset for lineage tracking.
            tags: Key-value tags for categorisation.
            properties: Additional metadata properties.
        """
        final_properties = properties.copy() if properties else {}

        # Store prompt-specific metadata
        if model:
            final_properties["model"] = model
        if temperature is not None:
            final_properties["temperature"] = temperature
        if max_tokens is not None:
            final_properties["max_tokens"] = max_tokens

        # Detect template format
        if isinstance(template, list):
            final_properties["format"] = "chat"
            final_properties["num_messages"] = len(template)
            roles = [m.get("role", "unknown") for m in template if isinstance(m, dict)]
            final_properties["roles"] = roles
        elif isinstance(template, str):
            final_properties["format"] = "text"
            # Extract variables from template
            import re

            variables = re.findall(r"\{(\w+)\}", template)
            if variables:
                final_properties["variables"] = variables
                final_properties["num_variables"] = len(variables)

        super().__init__(
            name=name,
            version=version,
            data=template,
            parent=parent,
            tags=tags,
            properties=final_properties,
        )

        self.template = template
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Render the prompt template by substituting variables.

        Args:
            **kwargs: Variable values for ``{variable}`` placeholders.

        Returns:
            Rendered prompt string or chat message list.

        Raises:
            ValueError: If the template is not set.
        """
        if self.template is None:
            raise ValueError("Cannot render a Prompt without a template")

        if isinstance(self.template, str):
            return self.template.format(**kwargs)

        # Chat-style: render each message content
        rendered_messages: list[dict[str, str]] = []
        for msg in self.template:
            rendered_msg = msg.copy()
            if "content" in rendered_msg:
                rendered_msg["content"] = rendered_msg["content"].format(**kwargs)
            rendered_messages.append(rendered_msg)
        return rendered_messages

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def variables(self) -> list[str]:
        """Variable names extracted from the template."""
        return self.metadata.properties.get("variables", [])

    @property
    def prompt_format(self) -> str:
        """Template format (``text`` or ``chat``)."""
        return self.metadata.properties.get("format", "text")

    @property
    def model_config(self) -> dict[str, Any]:
        """Model configuration dict (model, temperature, max_tokens)."""
        cfg: dict[str, Any] = {}
        if self.model:
            cfg["model"] = self.model
        if self.temperature is not None:
            cfg["temperature"] = self.temperature
        if self.max_tokens is not None:
            cfg["max_tokens"] = self.max_tokens
        return cfg

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        template: str | list[dict[str, str]],
        name: str | None = None,
        version: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "Prompt":
        """Factory method to create a Prompt.

        Args:
            template: Prompt template (string or chat messages).
            name: Prompt name (auto-generated if not provided).
            version: Version string.
            model: Target LLM model name.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.
            parent: Parent asset for lineage.
            tags: Tags dictionary.
            **kwargs: Stored as additional properties.

        Returns:
            New ``Prompt`` instance.
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"prompt_{timestamp}"

        return cls(
            name=name,
            template=template,
            version=version,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            parent=parent,
            tags=tags,
            properties=kwargs if kwargs else None,
        )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert Prompt to a serialisable dictionary."""
        result = super().to_dict()
        result["template"] = self.template
        result["model_config"] = self.model_config
        return result

    def __repr__(self) -> str:
        parts = [f"Prompt(name='{self.name}'"]
        if self.model:
            parts.append(f"model='{self.model}'")
        parts.append(f"format='{self.prompt_format}'")
        if self.variables:
            parts.append(f"vars={self.variables}")
        return ", ".join(parts) + ")"
