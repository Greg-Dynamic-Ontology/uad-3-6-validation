"""Assign one processing disposition to every discovered component."""

from app.models.schema_model import ComponentProcessingDisposition
from app.services.schema_loader.schema_closure import (
    SchemaComponentInventory,
)
from app.services.schema_loader.wildcard_policy import (
    apply_wildcard_policy,
)


REPRESENTATION_DECISIONS = {
    "annotation": "IT-5R2S2",
    "attribute": "IT-5R2S1",
    "attributeGroup": "IT-5R2S1",
    "choice": "IT-5R3S1",
    "complexType": "IT-5R2S1",
    "documentation": "IT-5R2S2",
    "element": "IT-5R2S1",
    "enumeration": "IT-5R4S1",
    "extension": "IT-5R3S2",
    "fractionDigits": "IT-5R4S1",
    "group": "IT-5R3S1",
    "include": "IT-5R7S2",
    "import": "IT-5R5S1",
    "maxInclusive": "IT-5R4S1",
    "maxLength": "IT-5R4S1",
    "minInclusive": "IT-5R4S1",
    "minLength": "IT-5R4S1",
    "pattern": "IT-5R4S1",
    "restriction": "IT-5R3S2",
    "sequence": "IT-5R3S1",
    "simpleContent": "IT-5R3S2",
    "simpleType": "IT-5R2S1",
    "union": "IT-5R3S2",
}


def apply_component_processing_policy(
    inventory: SchemaComponentInventory,
) -> tuple[ComponentProcessingDisposition, ...]:
    """Return exactly one deliberate disposition per occurrence."""

    wildcard_dispositions = {
        (
            disposition.source_document,
            disposition.source_index,
        ): disposition
        for disposition in apply_wildcard_policy(inventory)
    }
    dispositions: list[ComponentProcessingDisposition] = []

    for occurrence in inventory.occurrences:
        occurrence_id = (
            occurrence.source_document,
            occurrence.source_index,
        )
        wildcard_disposition = wildcard_dispositions.get(occurrence_id)
        if wildcard_disposition is not None:
            dispositions.append(wildcard_disposition)
            continue

        governing_decision = REPRESENTATION_DECISIONS.get(
            occurrence.component_kind
        )
        if governing_decision is None:
            dispositions.append(
                ComponentProcessingDisposition(
                    component_kind=occurrence.component_kind,
                    source_document=occurrence.source_document,
                    source_index=occurrence.source_index,
                    action="not_processed",
                    governing_decision="IT-5R6S2",
                    processed=False,
                )
            )
            continue

        dispositions.append(
            ComponentProcessingDisposition(
                component_kind=occurrence.component_kind,
                source_document=occurrence.source_document,
                source_index=occurrence.source_index,
                action="represent",
                governing_decision=governing_decision,
                processed=True,
            )
        )

    return tuple(dispositions)
