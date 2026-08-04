"""Load presentation policy from an RDF experience configuration."""

from dataclasses import asdict, dataclass
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import RDF


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@dataclass(frozen=True)
class ExperienceProfile:
    """Presentation capabilities selected by the active configuration."""

    shows_overall_progress: bool
    shows_pipeline_stages: bool
    shows_technical_artifacts: bool
    shows_developer_diagnostics: bool

    def as_response(self) -> dict[str, bool]:
        return asdict(self)


DEVELOPER_EXPERIENCE = ExperienceProfile(
    shows_overall_progress=True,
    shows_pipeline_stages=True,
    shows_technical_artifacts=True,
    shows_developer_diagnostics=True,
)


def load_experience_profile(
    configuration_file: Path | None,
) -> ExperienceProfile:
    """Return the RDF-selected experience, preserving developer defaults."""
    if configuration_file is None or not configuration_file.exists():
        return DEVELOPER_EXPERIENCE

    graph = Graph()
    graph.parse(configuration_file, format="turtle")

    configuration = next(
        graph.subjects(
            predicate=RDF.type,
            object=CFG.ApplicationConfiguration,
        ),
        None,
    )
    if configuration is None:
        return DEVELOPER_EXPERIENCE

    experience = graph.value(configuration, CFG.usesExperience)
    if experience is None:
        return DEVELOPER_EXPERIENCE

    return ExperienceProfile(
        shows_overall_progress=_boolean_value(
            graph.value(experience, CFG.showsOverallProgress),
            default=True,
        ),
        shows_pipeline_stages=_boolean_value(
            graph.value(experience, CFG.showsPipelineStages),
            default=True,
        ),
        shows_technical_artifacts=_boolean_value(
            graph.value(experience, CFG.showsTechnicalArtifacts),
            default=True,
        ),
        shows_developer_diagnostics=_boolean_value(
            graph.value(experience, CFG.showsDeveloperDiagnostics),
            default=True,
        ),
    )


def _boolean_value(value: object, *, default: bool) -> bool:
    if value is None:
        return default

    converted = value.toPython() if hasattr(value, "toPython") else value
    return converted if isinstance(converted, bool) else default
