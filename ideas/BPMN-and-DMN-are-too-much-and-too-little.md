Sidebar: MISMO has some strong BPMN, DMN,   advocates.
I might write a paper "BPMN and DMN are too much and too little when
compared to direct knowledge representation."

That title has teeth, and I think there is a substantial argument
behind it.

The **“too much and too little”** construction gives you two
different critiques rather than simply arguing that BPMN/DMN are bad.

**Too much:** they require the domain expert to translate knowledge
into the formalism's particular abstractions. 
With BPMN, knowledge becomes processes, activities, events, gateways,
flows, pools, etc. With DMN, it becomes decisions, inputs, decision
requirements, tables, expressions, and so forth. 
That translation is itself intellectual work—and potentially
introduces meaning that wasn't present in the source.

**Too little:** after doing that translation, much of the original
knowledge still isn't represented. Provenance, semantic relationships,
contextual meaning, governed identities, alternative representations,
relationships to other knowledge, and sometimes even *why* a rule exists
aren't naturally the center of either notation.

Direct knowledge representation reverses the relationship:

> Don't transform the knowledge into something the execution machinery understands.
> 
> Represent the knowledge, then build machinery capable of operating > on that representation.

And UAD gives you a remarkably concrete case study.
Consider our `0100.0007 / UAD1001` exercise.
We didn't merely create:

```text
IF AddressLineText missing
THEN Fatal
```

We've accumulated knowledge about:

```text
governed source
source constraint identity
UMDP rule identity requirement
violation condition severity
provenance
AddressLineText meaning
Logical Schema identity
applicable graph context
constraint behavior
instance representation
executable SHACL representation
eventual validation finding
```

The executable rule is only **one projection of that knowledge**.

That gives the paper a stronger thesis than “RDF is better than
BPMN/DMN.” 
I'd avoid that comparison entirely. 
Something more interesting is:

> BPMN and DMN begin by asking how knowledge can be expressed in an executable modeling formalism.
> 
> Direct knowledge representation begins by asking what is known.
> Executable behavior can then be derived as one use of that knowledge.

That connects directly to our recurring principle:

**Software is only one representation of knowledge.**

It also gives the BPMN/DMN advocates a fair position. 
They can reasonably respond that BPMN and DMN weren't intended to be universal knowledge-representation systems.
Exactly—and that may actually strengthen **“too little.”** 
They solve particular representation problems well. 
Trouble comes when they're asked to carry knowledge outside those boundaries.

I could see this becoming a strong paper after we have several dozen 
UAD constraints processed. 
Then it doesn't have to be philosophical warfare with the MISMO BPMN/DMN camp. 
We could take actual governed requirements and demonstrate, side-by-side,
**what must be added, transformed, or discarded to express them as process/decision models
versus what remains available in a direct knowledge representation**.

That would make “too much and too little” measurable rather than rhetorical.
