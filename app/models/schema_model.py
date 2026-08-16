"""Neutral logical model of an XML Schema.

The classes in this module describe XML Schema components without using
RDF, OWL, or SHACL concepts. The schema loader will populate this model,
and downstream generators will consume it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True, order=True)
class QName:
    """Expanded XML qualified name."""

    namespace: str | None
    local_name: str

    def __post_init__(self) -> None:
        if not self.local_name:
            raise ValueError("QName local_name must not be empty.")

    @property
    def clark_name(self) -> str:
        """Return the QName in Clark notation."""
        if self.namespace is None:
            return self.local_name
        return f"{{{self.namespace}}}{self.local_name}"


@dataclass(frozen=True, slots=True)
class SchemaImport:
    """One XML Schema import occurrence and its packaging metadata."""

    namespace: str | None
    schema_location: str | None
    source_document: Path
    resolved_document: Path | None


@dataclass(frozen=True, slots=True)
class ComponentProcessingDisposition:
    """Deliberate processing result for one discovered XSD occurrence."""

    component_kind: str
    source_document: Path
    source_index: int
    action: str
    governing_decision: str
    processed: bool

    def __post_init__(self) -> None:
        if not self.component_kind:
            raise ValueError("component_kind must not be empty.")
        if self.source_index < 0:
            raise ValueError("source_index must not be negative.")
        if not self.action:
            raise ValueError("action must not be empty.")
        if not self.governing_decision:
            raise ValueError("governing_decision must not be empty.")


class ModelGroupKind(str, Enum):
    """Supported XML Schema model-group compositors."""

    SEQUENCE = "sequence"
    CHOICE = "choice"


class TypeDerivationKind(str, Enum):
    """Supported XML Schema type-derivation methods."""

    RESTRICTION = "restriction"
    EXTENSION = "extension"
    UNION = "union"


@dataclass(frozen=True, slots=True)
class Facet:
    """Restriction facet applied to an XML Schema simple type."""

    name: str
    value: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Facet name must not be empty.")


@dataclass(frozen=True, slots=True)
class ElementDeclaration:
    """Element declaration or element use within a content model."""

    name: QName | None = None
    type_name: QName | None = None
    ref: QName | None = None
    min_occurs: int = 1
    max_occurs: int | None = 1
    documentation: str | None = None

    def __post_init__(self) -> None:
        if self.name is None and self.ref is None:
            raise ValueError(
                "An element declaration must have either a name or a ref."
            )

        if self.name is not None and self.ref is not None:
            raise ValueError(
                "An element declaration cannot have both a name and a ref."
            )

        if self.min_occurs < 0:
            raise ValueError("min_occurs must not be negative.")

        if self.max_occurs is not None:
            if self.max_occurs < 0:
                raise ValueError("max_occurs must not be negative.")

            if self.max_occurs < self.min_occurs:
                raise ValueError(
                    "max_occurs must be greater than or equal to min_occurs."
                )


@dataclass(frozen=True, slots=True)
class AttributeDeclaration:
    """Attribute declaration or attribute reference."""

    name: QName | None = None
    type_name: QName | None = None
    ref: QName | None = None
    required: bool = False
    default_value: str | None = None
    fixed_value: str | None = None
    documentation: str | None = None
    inline_simple_type: SimpleTypeDefinition | None = None

    def __post_init__(self) -> None:
        if self.name is None and self.ref is None:
            raise ValueError(
                "An attribute declaration must have either a name or a ref."
            )

        if self.name is not None and self.ref is not None:
            raise ValueError(
                "An attribute declaration cannot have both a name and a ref."
            )

        if (
            self.default_value is not None
            and self.fixed_value is not None
        ):
            raise ValueError(
                "An attribute cannot have both default_value and fixed_value."
            )


@dataclass(frozen=True, slots=True)
class ModelGroupReference:
    """Reference to a named reusable XML Schema model group."""

    ref: QName
    min_occurs: int = 1
    max_occurs: int | None = 1

    def __post_init__(self) -> None:
        if self.min_occurs < 0:
            raise ValueError("min_occurs must not be negative.")

        if self.max_occurs is not None:
            if self.max_occurs < 0:
                raise ValueError("max_occurs must not be negative.")

            if self.max_occurs < self.min_occurs:
                raise ValueError(
                    "max_occurs must be greater than or equal to min_occurs."
                )


@dataclass(frozen=True, slots=True, init=False)
class ModelGroup:
    """Ordered sequence or choice within a complex-type content model."""

    kind: ModelGroupKind
    particles: tuple[object, ...]
    elements: tuple[ElementDeclaration, ...]
    groups: tuple["ModelGroup | ModelGroupReference", ...]
    min_occurs: int
    max_occurs: int | None

    def __init__(
        self,
        kind: ModelGroupKind,
        elements: tuple[ElementDeclaration, ...] = (),
        groups: tuple["ModelGroup | ModelGroupReference", ...] = (),
        min_occurs: int = 1,
        max_occurs: int | None = 1,
        *,
        particles: tuple[object, ...] | None = None,
    ) -> None:
        """Create a group, retaining legacy element/group construction."""

        ordered_particles = (
            elements + groups
            if particles is None
            else particles
        )

        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "particles", ordered_particles)
        object.__setattr__(
            self,
            "elements",
            tuple(
                particle
                for particle in ordered_particles
                if isinstance(particle, ElementDeclaration)
            ),
        )
        object.__setattr__(
            self,
            "groups",
            tuple(
                particle
                for particle in ordered_particles
                if isinstance(
                    particle,
                    (ModelGroup, ModelGroupReference),
                )
            ),
        )
        object.__setattr__(self, "min_occurs", min_occurs)
        object.__setattr__(self, "max_occurs", max_occurs)
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.min_occurs < 0:
            raise ValueError("min_occurs must not be negative.")

        if self.max_occurs is not None:
            if self.max_occurs < 0:
                raise ValueError("max_occurs must not be negative.")

            if self.max_occurs < self.min_occurs:
                raise ValueError(
                    "max_occurs must be greater than or equal to min_occurs."
                )


@dataclass(frozen=True, slots=True)
class SimpleTypeDefinition:
    """Named XML Schema simple-type definition."""

    name: QName | None
    base_type: QName | None = None
    derivation_kind: TypeDerivationKind | None = None
    facets: tuple[Facet, ...] = ()
    enumeration_values: tuple[str, ...] = ()
    union_members: tuple[QName | SimpleTypeDefinition, ...] = ()
    union_member_types: tuple[QName, ...] = ()
    documentation: str | None = None

    def __post_init__(self) -> None:
        """Keep the legacy named-member view synchronized."""

        if self.union_members:
            object.__setattr__(
                self,
                "union_member_types",
                tuple(
                    member
                    for member in self.union_members
                    if isinstance(member, QName)
                ),
            )
        elif self.union_member_types:
            object.__setattr__(
                self,
                "union_members",
                self.union_member_types,
            )


@dataclass(frozen=True, slots=True)
class ComplexTypeDefinition:
    """Named XML Schema complex-type definition."""

    name: QName
    base_type: QName | None = None
    derivation_kind: TypeDerivationKind | None = None
    simple_content: bool = False
    content: ModelGroup | ModelGroupReference | None = None
    attributes: tuple[AttributeDeclaration, ...] = ()
    attribute_group_refs: tuple[QName, ...] = ()
    mixed: bool = False
    documentation: str | None = None


@dataclass(frozen=True, slots=True)
class AttributeGroupDefinition:
    """Named reusable collection of attribute declarations."""

    name: QName
    attributes: tuple[AttributeDeclaration, ...] = ()
    referenced_groups: tuple[QName, ...] = ()
    documentation: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaModel:
    """Resolved logical XML Schema independent of physical packaging."""

    target_namespace: str | None = None

    #
    # Prefix -> Namespace URI
    #
    namespace_bindings: Mapping[str, str] = field(default_factory=dict)
    schema_imports: tuple[SchemaImport, ...] = ()
    component_counts: Mapping[str, int] = field(default_factory=dict)
    processing_dispositions: tuple[
        ComponentProcessingDisposition,
        ...,
    ] = ()

    elements: Mapping[QName, ElementDeclaration] = field(default_factory=dict)
    complex_types: Mapping[QName, ComplexTypeDefinition] = field(default_factory=dict)
    simple_types: Mapping[QName, SimpleTypeDefinition] = field(default_factory=dict)
    attributes: Mapping[QName, AttributeDeclaration] = field(default_factory=dict)
    attribute_groups: Mapping[QName, AttributeGroupDefinition] = field(default_factory=dict)
    model_groups: Mapping[QName, ModelGroup] = field(default_factory=dict)

    #
    # Convenience set of all namespace URIs encountered.
    #
    namespaces: frozenset[str] = field(default_factory=frozenset)
