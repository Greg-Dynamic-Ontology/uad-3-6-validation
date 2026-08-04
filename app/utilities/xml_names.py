"""Utilities for working with namespace-qualified XML names."""

from __future__ import annotations


def split_expanded_name(expanded_name: str) -> tuple[str, str]:
    """Split an ElementTree expanded name into namespace and local name."""
    if not expanded_name.startswith("{"):
        raise ValueError("The XML name must use a namespace.")

    namespace_end = expanded_name.index("}")

    namespace = expanded_name[1:namespace_end]
    local_name = expanded_name[namespace_end + 1:]

    return namespace, local_name


__all__ = ["split_expanded_name"]
