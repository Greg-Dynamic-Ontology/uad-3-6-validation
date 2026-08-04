"""Models representing a loaded UAD appraisal."""

from __future__ import annotations


class LoadedAppraisal:
    """A UAD XML appraisal already loaded by the application."""

    def __init__(
        self,
        *,
        source_name: str,
        xml_bytes: bytes,
    ) -> None:
        self.source_name = source_name
        self.xml_bytes = xml_bytes
