from app.models.schema_model import (
    AttributeDeclaration,
    ComplexTypeDefinition,
    ElementDeclaration,
    Facet,
    ModelGroup,
    ModelGroupKind,
    QName,
    SchemaModel,
    SimpleTypeDefinition,
)


def test_qname_has_clark_notation() -> None:
    qname = QName(
        namespace="https://www.example.com/schema",
        local_name="AddressType",
    )

    assert qname.clark_name == (
        "{https://www.example.com/schema}AddressType"
    )


def test_qname_without_namespace_uses_local_name() -> None:
    qname = QName(namespace=None, local_name="string")

    assert qname.clark_name == "string"


def test_element_declaration_defaults_to_exactly_once() -> None:
    element = ElementDeclaration(
        name=QName(
            namespace="https://www.example.com/schema",
            local_name="Address",
        ),
        type_name=QName(
            namespace="https://www.example.com/schema",
            local_name="AddressType",
        ),
    )

    assert element.min_occurs == 1
    assert element.max_occurs == 1
    assert element.ref is None


def test_unbounded_element_uses_none_for_max_occurs() -> None:
    element = ElementDeclaration(
        name=QName(
            namespace="https://www.example.com/schema",
            local_name="Comment",
        ),
        type_name=QName(
            namespace="http://www.w3.org/2001/XMLSchema",
            local_name="string",
        ),
        min_occurs=0,
        max_occurs=None,
    )

    assert element.min_occurs == 0
    assert element.max_occurs is None


def test_model_group_preserves_choice_structure() -> None:
    email = ElementDeclaration(
        name=QName(None, "Email"),
        type_name=QName(
            "http://www.w3.org/2001/XMLSchema",
            "string",
        ),
    )
    telephone = ElementDeclaration(
        name=QName(None, "Telephone"),
        type_name=QName(
            "http://www.w3.org/2001/XMLSchema",
            "string",
        ),
    )

    group = ModelGroup(
        kind=ModelGroupKind.CHOICE,
        elements=(email, telephone),
    )

    assert group.kind is ModelGroupKind.CHOICE
    assert group.elements == (email, telephone)


def test_simple_type_can_represent_restrictions() -> None:
    type_name = QName(
        "https://www.example.com/schema",
        "PositiveAmountType",
    )

    simple_type = SimpleTypeDefinition(
        name=type_name,
        base_type=QName(
            "http://www.w3.org/2001/XMLSchema",
            "decimal",
        ),
        facets=(
            Facet(name="minInclusive", value="0"),
            Facet(name="fractionDigits", value="2"),
        ),
    )

    assert simple_type.name == type_name
    assert simple_type.facets == (
        Facet(name="minInclusive", value="0"),
        Facet(name="fractionDigits", value="2"),
    )


def test_simple_type_can_represent_enumerations() -> None:
    simple_type = SimpleTypeDefinition(
        name=QName(
            "https://www.example.com/schema",
            "PropertyTypeEnum",
        ),
        base_type=QName(
            "http://www.w3.org/2001/XMLSchema",
            "string",
        ),
        enumeration_values=(
            "Detached",
            "Attached",
            "Condominium",
        ),
    )

    assert simple_type.enumeration_values == (
        "Detached",
        "Attached",
        "Condominium",
    )


def test_simple_type_can_represent_a_union() -> None:
    simple_type = SimpleTypeDefinition(
        name=QName(
            "https://www.example.com/schema",
            "DateOrUnknownType",
        ),
        union_member_types=(
            QName(
                "http://www.w3.org/2001/XMLSchema",
                "date",
            ),
            QName(
                "https://www.example.com/schema",
                "UnknownType",
            ),
        ),
    )

    assert len(simple_type.union_member_types) == 2


def test_complex_type_contains_content_and_attributes() -> None:
    street = ElementDeclaration(
        name=QName(None, "Street"),
        type_name=QName(
            "http://www.w3.org/2001/XMLSchema",
            "string",
        ),
    )

    identifier = AttributeDeclaration(
        name=QName(None, "id"),
        type_name=QName(
            "http://www.w3.org/2001/XMLSchema",
            "string",
        ),
        required=True,
    )

    complex_type = ComplexTypeDefinition(
        name=QName(
            "https://www.example.com/schema",
            "AddressType",
        ),
        content=ModelGroup(
            kind=ModelGroupKind.SEQUENCE,
            elements=(street,),
        ),
        attributes=(identifier,),
    )

    assert complex_type.content is not None
    assert complex_type.content.elements == (street,)
    assert complex_type.attributes == (identifier,)


def test_schema_model_indexes_global_components_by_qname() -> None:
    element_name = QName(
        "https://www.example.com/schema",
        "Address",
    )
    complex_type_name = QName(
        "https://www.example.com/schema",
        "AddressType",
    )

    element = ElementDeclaration(
        name=element_name,
        type_name=complex_type_name,
    )
    complex_type = ComplexTypeDefinition(name=complex_type_name)

    schema = SchemaModel(
        elements={element_name: element},
        complex_types={complex_type_name: complex_type},
    )

    assert schema.elements[element_name] == element
    assert schema.complex_types[complex_type_name] == complex_type
    assert schema.simple_types == {}
    assert schema.attributes == {}