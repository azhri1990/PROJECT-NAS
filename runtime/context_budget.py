"""Deterministic context budgeting for local-model prompts."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CONTEXT_CHARS = 12000
MAX_CONTEXT_CHARS = 16000


@dataclass(frozen=True)
class ContextBudget:
    max_chars: int = DEFAULT_CONTEXT_CHARS

    def __post_init__(self) -> None:
        if not isinstance(self.max_chars, int) or isinstance(self.max_chars, bool):
            raise ValueError("max_chars must be an integer")
        if not 1 <= self.max_chars <= MAX_CONTEXT_CHARS:
            raise ValueError(f"max_chars must be between 1 and {MAX_CONTEXT_CHARS}")


def compose_context(system: str, memory: str, user: str, *, budget: ContextBudget | None = None) -> tuple[str, bool]:
    """Compose deterministic context, preserving user text and bounding total size."""
    if not all(isinstance(value, str) for value in (system, memory, user)):
        raise ValueError("context components must be strings")
    limit = (budget or ContextBudget()).max_chars
    sections = (system.strip(), memory.strip(), user.strip())
    labels = ("SYSTEM", "MEMORY", "USER")
    parts: list[str] = []
    used = 0
    truncated = False
    for label, section in zip(labels, sections):
        if not section:
            continue
        prefix = f"[{label}]\n"
        separator = "\n\n" if parts else ""
        available = limit - used - len(separator) - len(prefix)
        if available <= 0:
            truncated = True
            break
        clipped = section[:available]
        if clipped != section:
            truncated = True
        parts.append(separator + prefix + clipped)
        used += len(separator) + len(prefix) + len(clipped)
        if truncated:
            break
    return "".join(parts), truncated
