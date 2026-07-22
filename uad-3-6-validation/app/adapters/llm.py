from app.models.validation import Finding


class AdvisoryLlmClient:
    """Placeholder for Ollama/RAG integration. Never owns deterministic validation."""

    def explain_finding(self, finding: Finding | None, finding_id: str) -> str:
        if finding is None:
            return f"No stored finding was found for {finding_id}. Explanation is unavailable."
        source = finding.source.source_section if finding.source else "the governing rule"
        return (
            f"Finding {finding.finding_id} is based on {source}. "
            f"Observed value: {finding.observed_value or 'not applicable'}. "
            f"Expected condition: {finding.expected_condition or 'see source rule'}."
        )

    def review_revision_history(self, text: str, related_finding_ids: list[str]) -> list[str]:
        comments: list[str] = []
        if not text.strip():
            comments.append("Revision History Detail is empty or blank.")
        if related_finding_ids and not any(fid in text for fid in related_finding_ids):
            comments.append("Revision History Detail does not explicitly reference the related finding identifiers.")
        if not comments:
            comments.append("Revision History Detail is present. Advisory review did not identify an obvious omission.")
        return comments


llm_client = AdvisoryLlmClient()
