# Competency Index Discover
I think you've just identified something that deserves to become a central theme of the Harvest section.

When we first discussed Harvest OTDD, I was subconsciously thinking:

> "The competencies already exist, so discovery is over."

Today proved that's false.

There are **two kinds of discovery**.

### Greenfield Discovery

Discovering **what the semantics should be**.

Example:

> Should there be a Reconciliation concept?

---

### Harvest Discovery

Discovering **what the existing standard actually says**.

That sounds trivial until you start doing it.

Today alone we discovered:

* XLink relationship competencies.
* Datapoints as valid XLink endpoints.
* The distinction between relationship competencies and instance-projection competencies.
* That UAD, not base MISMO, is the authoritative source for this project.
* That the competency inventory is itself a first-class engineering artifact.

None of those were inventions.

They were discoveries.

---

I think that deserves a statement in the OTDD publication.

Something like:

> **Harvest Semantic Engineering is not the absence of discovery. It is the systematic discovery of semantics already present within authoritative source artifacts.**

I like that because it explains why Harvest projects still require engineering judgment.

---

### The Competency Index becomes the engineering notebook for discovery.

Initially it contains:

```
Known Competencies
```

As engineering proceeds it accumulates:

* ontology mappings
* SHACL
* examples
* verification
* implementation status
* use cases

Eventually it becomes a complete traceability matrix.

---

### I think there is a chapter hiding here.

Not

> Competency Index

but

> **The Evolution of a Competency Inventory**

Because what we've watched over the last two days is fascinating.

It evolved from:

```
Checklist
```

to

```
Backlog
```

to

```
Traceability Matrix
```

to

```
Engineering Planning Artifact
```

That evolution wasn't planned.

It emerged because each new engineering question naturally found its home there.

---

### One prediction

I think six months from now, someone reading the book won't remember the details of `DATA_SOURCE_IsDataSourceFor_PROPERTY`.

But they'll remember the Competency Index.

Because it answers the question:

> **"How do I organize the engineering of hundreds of semantic requirements without getting lost?"**

That's a methodology contribution, not a UAD contribution.

---

And there's one more thing I find satisfying.

When we started today, we were asking:

> "What should we work on next?"

By the end of the day, the Competency Index itself had begun answering that question.

Whenever an artifact starts telling the engineer what to do next instead of merely recording what has already been done, it has become an active part of the engineering process. That's a hallmark of a well-designed engineering artifact, and I think it's exactly why this document deserves a prominent place in the OTDD methodology rather than being treated as just another project document.
