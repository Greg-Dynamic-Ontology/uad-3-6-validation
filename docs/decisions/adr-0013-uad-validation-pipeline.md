# ADR-0013: UAD Validation Pipeline

Status: Accepted

Date: 2026-07-21

1. Project the XML instance document into a canonical RDF instance graph.
2. Express the Fannie Mae and Freddie Mac business rules as SHACL shapes over the RDF 
instance graph.
3. Build the measurement and reporting infrastructure on top of the deterministic validation 
results.

That third step is more important than it sounds. 
The reports are not merely "pretty output." 
They are the product.

```
            UAD XML
               │
               ▼
      RDF Instance Graph
               │
               ▼
        SHACL Validation
               │
      ┌────────┴────────┐
      ▼                 ▼
 Validation Findings  Measurements
      │                 │
      └────────┬────────┘
               ▼
      Reports & Dashboards
               │
               ▼
     Historical Analytics
               │
               ▼
        AI Assistance
               │
               ▼
      Improved Validation Rules
```
## Step 1 is nearly a solved problem.

You've already done much of the hard conceptual work:

- deterministic IRI minting
- ontology
- XLink mapping
- RDF projection strategy
- meaning-first architecture

The remaining effort is implementation.

---
## Step 2 Where much of the project's unique intellectual property resides.
Anyone can validate XML.

Far fewer organizations can faithfully encode the GSE business rules into executable SHACL.

That becomes a durable asset.

---
## Step 3 is where customers perceive value.
A lender probably doesn't care that a shape failed.

They care about:

- Can I deliver this appraisal?
- What must be fixed?
- How serious is the problem?
- How long will it take to repair?
- Are we improving over time?
- Which vendors are producing the cleanest files?

Those are reporting questions.

---

## Step 4 Build the Validation Observatory
```
Validation Engine
        ↓
Measurement Engine
        ↓
Reporting Engine
        ↓
Validation Observatory
```

That is where the metadata from thousands or millions of validation runs becomes a 
strategic asset.

So the long-term roadmap becomes:
1. XML → RDF
2. RDF → SHACL validation
3. Validation → reports and measurements
4. Measurements → observatory and analytics
5. Observatory → optional AI assistance

> Every stage in the pipeline produces a durable artifact that becomes the input to the next 
> stage. 
> XML is projected into RDF → RDF is evaluated by SHACL → SHACL produces findings and measurements. 
> Measurements become reports and historical analytics. 
> Historical analytics may eventually support AI-assisted capabilities. 
> At every stage, the authoritative results remain deterministically derived from the 
> original appraisal document.