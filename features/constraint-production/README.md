# Explicit Handoffs

This feature allows for explicit handoffs between different constraint 
production strategies.
It provides a way to specify which strategy should be used for a particular 
constraint, giving more control over the constraint production process.

| Order | Feature                                | Stage                                        |
|-------|----------------------------------------|----------------------------------------------|
| IT-50 | Normalize constraint                   | Normalize source constraints                 |
| IT-51 | Governed RDF exchange                  | Exchange governed RDF                        |
| IT-52 | Bind logical schema                    | Bind constraints to the logical schema       |
| IT-53 | Resolve context                        | Resolve applicability context                |
| IT-54 | Classify validation behavior           | Classify the required validation behavior    |
| IT-55 | Bind instance RDF                      | Bind constraints to instance data            |
| IT-56 | Generate SHACL                         | Generate validation shapes                   |
| IT-57 | Project report finding                 | Turn validation results into report findings |
| IT-58 | Execute constraint production pipeline | Run and verify the complete sequence         |