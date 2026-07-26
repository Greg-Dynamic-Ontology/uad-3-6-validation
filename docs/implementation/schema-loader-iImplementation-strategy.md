# Schema Loader Implementation Strategy
The `SchemaLoader` constructs a neutral `SchemaModel` from one or more XML Schema documents.

The public API is:
```python
schema = SchemaLoader().load(path)
```
The load() method acts as an orchestrator. 
XML Schema components are loaded in incremental passes using private helper methods.

Example:
```python
def load(self, path: Path) -> SchemaModel:
    schema = SchemaModel(...)

    self._load_namespaces(...)
    self._load_simple_types(...)
    self._load_complex_types(...)
    self._load_elements(...)
    self._load_attributes(...)
    self._load_groups(...)
    self._resolve_references(...)

    return schema
```

Each helper is responsible for a single XML Schema component.

This organization keeps the implementation readable, supports test-driven development, and allows new XML Schema 
features to be added independently.
---
## One thing that changed during implementation
We introduced a dedicated parser context.

Instead of helpers like:
```python
_load_simple_types(root, schema)
```
We created this pattern:
```python
@dataclass
class SchemaLoaderContext:
    path: Path
    tree: ET.ElementTree
    root: ET.Element
    schema: SchemaModel
```
Then every helper simply receives the context:
```python
self._load_simple_types(ctx)
self._load_complex_types(ctx)
```
This has several advantages:
- The method signatures stay short.
- We don't end up passing five or six parameters everywhere.
- If we later add a state (for example, imported schemas, include resolution, diagnostics, 
or source locations), we add it in one place.
- It fits naturally with your goal of processing both the Combined and Individual schema 
distributions into the same logical model.