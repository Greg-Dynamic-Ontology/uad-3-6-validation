Yes. Let’s structure it as an independent Python package now, with UAD as its
first consumer.

Keep your feature file where you moved it:

```text
utilities/
└── graphdb-utilities/
    ├── pyproject.toml
    ├── README.md
    ├── src/
    │   └── owb_graphdb/
    │       ├── __init__.py
    │       ├── provisioning.py
    │       ├── configuration.py
    │       ├── client.py
    │       ├── validation.py
    │       └── errors.py
    ├── features/
    │   └── gdb-1.feature
    └── tests/
        ├── conftest.py
        ├── unit/
        ├── integration/
        │   └── test_gdb_1_r1_s1_create_repository_with_shacl.py
        └── fixtures/
            ├── repository-config.ttl
            ├── shapes.ttl
            ├── conforming-data.ttl
            └── nonconforming-data.ttl
```

**Package names:**

- Installable distribution: `owb-graphdb`
- Python import: `owb_graphdb`
- Public entry point: `setup_repository(...)`

For example, UAD and other OWB projects would use:

```python
from owb_graphdb import setup_repository
```

**Responsibilities:**

| Module | Responsibility |
|---|---|
| `provisioning.py` | Coordinate repository creation and readiness checks |
| `configuration.py` | Represent supplied configuration, shape version, and validation scope |
| `client.py` | Communicate with GraphDB |
| `validation.py` | Install shapes and verify SHACL enforcement |
| `errors.py` | Provide meaningful errors applications can handle |

The fixture vocabulary will be generic. UAD’s customer vocabulary, customer shapes, account rules, and credentials belong outside this package. The package must never import UAD code.

The package should have its own dependencies and test configuration in `pyproject.toml`, so it can later move into a separate Git repository without reorganizing its contents. We will create modules as their scenarios require them.

**Next step:** define the small public provisioning interface, then supply the GDB-1R1S1 integration test. That test will exercise the installed package against GraphDB and remain red until repository provisioning is implemented.

**Files changed: None.**