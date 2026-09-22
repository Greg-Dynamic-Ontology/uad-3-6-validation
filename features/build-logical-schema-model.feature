Feature: Build Logical Schema Model
  As the UAD 3.6 validation engine
  I want to construct a logical representation of one or more XML Schemas
  So that validation, ontology projection, measurements, and other services
  can operate independently of XML syntax

  Rule: Namespace handling

    Scenario: Target namespace is preserved
      Given an XML Schema with a target namespace
      When the schema is loaded
      Then the Logical Schema Model records the target namespace

    Scenario: Namespace prefixes are resolved
      Given an XML Schema declaring namespace prefixes
      When the schema is loaded
      Then namespace prefixes resolve to the correct namespace IRIs

  Rule: QName resolution

    Scenario: Resolve an unprefixed QName
      Given an XML Schema containing an unprefixed QName
      When the schema is loaded
      Then the QName resolves using the schema's default rules

    Scenario: Resolve a prefixed QName
      Given an XML Schema containing a prefixed QName
      When the schema is loaded
      Then the QName resolves to the referenced namespace

    Scenario: Reject an unknown namespace prefix
      Given an XML Schema containing an unknown namespace prefix
      When the schema is loaded
      Then loading fails with an appropriate error

  Rule: Named simple types

    Scenario: Load a named simple type
      Given an XML Schema containing a named simpleType
      When the schema is loaded
      Then the Logical Schema Model contains the named simple type

    Scenario: Preserve restriction base
      Given a named simpleType derived by restriction
      When the schema is loaded
      Then the Logical Schema Model records the restriction base

    Scenario: Preserve enumeration facets
      Given a named simpleType containing enumeration facets
      When the schema is loaded
      Then the Logical Schema Model records each enumeration value

  Rule: Named complex types

    Scenario: Load a named complex type
      Given an XML Schema containing a named complexType
      When the schema is loaded
      Then the Logical Schema Model contains the named complex type

  Rule: Element declarations

    Scenario: Load a global element declaration
      Given an XML Schema containing a global element
      When the schema is loaded
      Then the Logical Schema Model contains the element declaration

  Rule: Attribute declarations

    Scenario: Load a global attribute declaration
      Given an XML Schema containing a global attribute
      When the schema is loaded
      Then the Logical Schema Model contains the attribute declaration

  Rule: Schema composition

    Scenario: Load included schemas
      Given an XML Schema including another schema
      When the schema is loaded
      Then declarations from both schemas appear in the Logical Schema Model

    Scenario: Load imported schemas
      Given an XML Schema importing another namespace
      When the schema is loaded
      Then declarations from the imported schema are available in the Logical Schema Model

  # IT-31 — Preserve governed source identities for named Logical Schema resources
  @IT-31R1
  Rule: Named schema identities remain recognizable in the Logical Schema Model
    @IT-31R1S1
    Scenario: Preserve a QName using its governed source identity
      Given an XML Schema containing a QName with a namespace and local name
      When the Logical Schema Model is serialized as RDF
      Then the QName identity is derived from its namespace and local name
      And the QName identity does not depend on the serializer traversal path
      And the QName remains recognizable by its source local name

    @IT-31R1S2
    Scenario: Reuse the same QName identity wherever the QName is referenced
      Given the same QName is referenced from more than one schema context
      When the Logical Schema Model is serialized as RDF
      Then every reference resolves to the same QName identity
      And the QName retains the same namespace and local name in every context

    @IT-31R1S3
    Scenario: Reserve generated identities for schema structures without governed source names
      Given a Logical Schema Model contains a schema structure with no governed source name
      When the Logical Schema Model is serialized as RDF
      Then the serializer may assign a deterministic generated identity
      And the generated identity does not replace a governed source identity
