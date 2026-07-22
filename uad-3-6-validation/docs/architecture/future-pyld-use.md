# Future use of PyLD
## Query
Anything on the attached email germane to my work?
## Response

First, congratulations! 🎉

> **"All the pages show from the GitHub Pages!!!"**

That's a major milestone. You now have a live engineering portal that you can send to Liz and others. We can polish it over time, but the hardest part—getting it published—is behind you.

---

As for the email, yes, there are several items that are directly relevant to your work.

### 1. PyLD 3.1.0 is the biggest news

The announcement says PyLD now has **JSON-LD 1.1 test-suite compliance** for:

* compact
* flatten
* frame

That means it conforms much more closely to the W3C JSON-LD specification.

For your projects, this is important because you've talked several times about eventually supporting JSON-LD alongside Turtle and RDF/XML in the Ontology Tool Kit and the UAD project. A standards-compliant library reduces risk.

---

### 2. RDFLib integration

The discussion asks:

> "Will PyLD 4.0 support RDFLib?"

That caught my eye because your work is already heavily based on **RDFLib**.

Your current stack is essentially:

* RDFLib
* SHACL
* GraphDB
* Turtle
* SPARQL

Adding JSON-LD without leaving RDFLib would be ideal.

---

### 3. RDF 1.2

Nicholas Car mentions

> RDF 1.2 support

and

> SHACL 1.2 support

Those standards are still evolving, but they are worth watching because your validation framework is fundamentally SHACL-based.

---

### 4. JSON-LD-star / RDF-star

The thread also mentions:

* RDF-star
* Triple Terms
* JSON-LD-star

Those are for representing statements about statements.

For example, instead of merely saying

```
ComparableSale123 salePrice 450000
```

you can say

```
This statement
    came from MLS
    confidence 0.82
    enteredBy Appraiser
```

That could become useful if you start attaching provenance or confidence scores to extracted appraisal facts.

---

## The thing I found most interesting

The discussion is still centered on:

> "How do we serialize RDF?"

Your work is becoming something different.

Your emphasis has shifted toward:

> **How do we derive RDF from structured business artifacts?**

That's a higher-level problem.

You aren't just consuming RDF.

You're creating ontologies from:

* XML Schemas
* JSON Schemas
* Implementation Guides
* Business rules
* Decision matrices
* Instance documents

Very few people are working at that level.

---

## What I would do

I would install PyLD 3.1 in one of your development environments and simply keep it available. There's no need to rewrite anything today, but it gives us another standards-compliant serialization option.

Eventually OTK could support something like:

```
otk export ontology.ttl --jsonld
```

or

```
otk convert appraisal.ttl appraisal.jsonld
```

with almost no custom JSON-LD code because PyLD would handle the heavy lifting.

I think that's a worthwhile direction to keep in mind as OTK matures.

## Architectural Implications
* Delay writing any custom JSON-LD serializer.
* Continue using RDFLib as the core graph API.
* Monitor the RDFLib/PyLD convergence.
* When mature, expose JSON-LD as another export format.
* Preserve the graph-first architecture.
* Treat JSON-LD as a projection of the RDF graph rather than as a primary internal 
representation.
* Monitor RDFLib's planned integration of SPARQLWrapper and OWL-RL to simplify OTK dependencies over time.

## The email thread

[rdflib-dev] [Announcement] PyLD v3.1.0
Inbox
Summarize this email

Miel Vander Sande
Jun 26, 2026, 3:23 AM
Hi all, Just wanted to let you know that PyLD released v3.1.0 with JSON-LD 1.1 test-suite compliance for compact, flatten, and frame. For details, consult the g

Nicholas Car
Jun 26, 2026, 5:15 AM
Fantastic step forward there Miel! It's really great to see JSON-LD support stepping up alongside the start of RDF 1.2 support in RDFLib and SHACL 1.2 support a

Wes Turner <wes.turner@gmail.com>
Jun 26, 2026, 9:13 AM
to rdflib-dev, public-json-ld-wg

Nice work! PyLD 4.0 will support rdflib?

- https://github.com/digitalbazaar/pyld/releases/tag/v3.1.0

- Migrate JsonLdProcessor to RDFLib by mielvds: digitalbazaar/pyld https://github.com/digitalbazaar/pyld/pull/254

FWIW, there's also oxigraph:

- oxigraph/oxrdflib: Oxrdflib provides rdflib stores using pyoxigraph https://github.com/oxigraph/oxrdflib

These rdflib issues mention compaction:

- Compact serialization · Issue #93 · RDFLib/rdflib-jsonld https://github.com/RDFLib/rdflib-jsonld/issues/93
  - rdflib-jsonld is archived, though 

- Document RDFLib and pyld usage patterns · Issue #2823 · RDFLib/rdflib https://github.com/RDFLib/rdflib/issues/2823

Re: RDFstar / RDF1.2 Triple Terms:

- JSON-LD-star spec on compaction: https://json-ld.github.io/json-ld-star/#compaction-algorithm

- Adapting to Triple Terms and Reifiers · Issue #49 · json-ld/json-ld-star https://github.com/json-ld/json-ld-star/issues/49
To view this discussion visit https://groups.google.com/d/msgid/rdflib-dev/CACfEFw-WmbshY3XwW_0Ob%2BBBKYZ3Gj_U3uAOWqbqyhV7cthdOw%40mail.gmail.com.


Miel Vander Sande miel.vandersande@meemoo.be via googlegroups.com 
Jun 26, 2026, 12:08 PM
to rdflib-dev@googlegroups.com, public-json-ld-wg@w3.org

Hi Wes

Op vrijdag 26 juni 2026 schreef Wes Turner <wes.turner@gmail.com>:
Nice work! PyLD 4.0 will support rdflib?

Yes, and ... 

- https://github.com/digitalbazaar/pyld/releases/tag/v3.1.0

- Migrate JsonLdProcessor to RDFLib by mielvds: digitalbazaar/pyld https://github.com/digitalbazaar/pyld/pull/254

... as you found out, that work has already been done. Because this introduces breaking changes for a.o toRdf(), we're trying to do spec compliance first.

FWIW, there's also oxigraph:

- oxigraph/oxrdflib: Oxrdflib provides rdflib stores using pyoxigraph https://github.com/oxigraph/oxrdflib

These rdflib issues mention compaction:

- Compact serialization · Issue #93 · RDFLib/rdflib-jsonld https://github.com/RDFLib/rdflib-jsonld/issues/93
  - rdflib-jsonld is archived, though 

- Document RDFLib and pyld usage patterns · Issue #2823 · RDFLib/rdflib https://github.com/RDFLib/rdflib/issues/2823

There are a couple of rdflib issues that mention jsonld and these hould probably be cleaned up. PyLD could replace the current jsonld processing if desired 
 
Re: RDFstar / RDF1.2 Triple Terms:

- JSON-LD-star spec on compaction: https://json-ld.github.io/json-ld-star/#compaction-algorithm

- Adapting to Triple Terms and Reifiers · Issue #49 · json-ld/json-ld-star https://github.com/json-ld/json-ld-star/issues/49

Rdf 1.2 would probably be next in the development cycle, although it would be more challenging.than refactoring and bugfixing

Best

Miel
To view this discussion visit https://groups.google.com/d/msgid/rdflib-dev/CAHeRLWveVUrCqKorj2a5UHx6djo_kBZ%2BUH5P89xg8zHxuRxC8Q%40mail.gmail.com.


Anatoly Scherbakov <altaisoft@gmail.com>
Jun 26, 2026, 12:41 PM
to Miel, rdflib-dev, Working

Hi all,

Wanted to mention one detail.

While RDF 1.2 is close to being finalized, the JSON-LD situation is a bit more difficult.

While the work on JSON-LD 1.2 is ongoing, it will likely not implement triple terms. That might be implemented in JSON-LD 1.3 or further.

There are a bunch of open issues and PRs for the JSON-LD Working Group to go through. If anyone would like to participate - please do! All the work is being done at https://github.com/json-ld/ 

Anatoly
--
http://github.com/RDFLib
---
You received this message because you are subscribed to the Google Groups "rdflib-dev" group.
To unsubscribe from this group and stop receiving emails from it, send an email to rdflib-dev+unsubscribe@googlegroups.com.
To view this discussion visit https://groups.google.com/d/msgid/rdflib-dev/CAF%3DFK_Pf3VwBzTTAj19hqEdVr5ZPrjY%3DCtSFJabC%3D6bJLhm2ng%40mail.gmail.com.


Nicholas Car nick@kurrawong.net via googlegroups.com 
Jun 26, 2026, 5:00 PM
to rdflib-dev, public-json-ld-wg

rdflib-jsonld is archived because it’s functionality has been subsumed by the main rdflib library.

But we are all planning on this merger of the JSON-LD handling across RDFLib and pyLD.

I also plan to subsume SPARQLWrapper into RDFLib and perhaps ever OWL-RL. All optional to use but increases the RDFLib offerings and reduces maintenance.

Cheers, Nick




--
Dr Nicholas Car
Data Architect & Knowledge Graph Specialist
KurrawongAI
nick@kurrawong.ai
0477 560 177
https://kurrawong.ai

Honorary Lecturer
College of Engineering, Computing & Cybernetics
Australian National University
https://cecc.anu.edu.au/people/nicholas-car
--


-------- Original Message --------
To view this discussion visit https://groups.google.com/d/msgid/rdflib-dev/ZZeRmmas5OKTboh1weG5bffc1dYcFkQhSQyktTcTLSa2kXlsoqN8IUuGr-EE3AnV8k5mGMyRIn1fu2qpuXSNWN9wD-OQU7YwKHi1VQykOQI%3D%40kurrawong.net.


