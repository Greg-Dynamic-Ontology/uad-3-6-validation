
# User Management
There is a relatively stable, well-established model for user management data,
although there is no single universal schema.

The field is generally called Identity and Access Management (IAM). 
Its fundamental concepts have been stable for decades.

I would separate user management into five areas:

* Identity — Who is the user?
* Authentication — How does the system establish that identity?
* Authorization — What is the user permitted to do?
* Lifecycle — How is the account created, modified, suspended, or deleted?
* Audit — What has the user done, and when?

Importantly, these are distinct concepts, even though many software systems
unfortunately mix them together.

## A minimal conceptual data model
| **Entity**      | **Principal attributes**                        |
|-----------------|-------------------------------------------------|
| User            | ID, name, email, status                         |
| Identity        | User ID, identity provider, external identifier |
| Credential      | Authentication method, credential reference     |
| Group           | Group ID, name, description                     |
| Role            | Role ID, name, description                      |
| Permission      | Resource, action, constraints                   |
| Membership      | User ID, group ID                               |
| Role Assignment | Principal ID, role ID, scope                    |
| Session         | Session ID, user ID, expiration                 |
| Audit Event     | Actor, action, target, timestamp, outcome       |

This is a conceptual model rather than a proposed database schema.
For example, credentials should generally be managed by an identity
provider rather than stored directly in an application’s user table.

## The standards worth examining
The closest match to your question is
>SCIM — System for Cross-domain Identity Management.


* RFC 7643 — SCIM Core Schema⁠Attachment.png defines standard user and group
attributes.
* RFC 7644 — SCIM Protocol⁠Attachment.png defines operations for managing
those resources.
* NIST SP 800-63-4⁠Attachment.png covers identity proofing, authentication,
and federation.

SCIM is especially interesting because its schema is extensible without
requiring everyone to adopt the same application-specific user model.

## An ontology perspective
Given your work with RDF and knowledge graphs, I would distinguish three relationships:

A person may possess multiple digital identities.
An identity may be associated with multiple accounts.
An account may have different roles and permissions in different systems.
Those distinctions make a reusable ontology considerably more useful than a
conventional Users table.

One question: Are you thinking about user management for your own software
projects, or are you looking for a general-purpose ontology that could be
reused across applications?

The answer determines whether SCIM alone is sufficient or whether we should
examine a broader semantic model.

There is a relatively stable, well-established model for user management data,
although there is no single universal schema.

The field is generally called Identity and Access Management (IAM).
Its fundamental concepts have been stable for decades.

I would separate user management into five areas:

Identity — Who is the user?
Authentication — How does the system establish that identity?
Authorization — What is the user permitted to do?
Lifecycle — How is the account created, modified, suspended, or deleted?
Audit — What has the user done, and when?
Importantly, these are distinct concepts, even though many software systems unfortunately mix them together.

A minimal conceptual data model

| Entity | Principal attributes |
|-----------------|-------------------------------------------------|
| User | ID, name, email, status |
| Identity | User ID, identity provider, external identifier |
| Credential | Authentication method, credential reference |
| Group | Group ID, name, description |
| Role | Role ID, name, description |
| Permission | Permission ID, name, description |
| Membership | User ID, group ID |
| Role Assignment | Principal ID, role ID, scope |
| Session | Session ID, user ID, expiration |
| Audit Event | Actor, action, target, timestamp, outcome |

This is a conceptual model rather than a proposed database schema. 
For example, credentials should generally be managed by an identity
provider rather than stored directly in an application’s user
table.

The standards worth examining
The closest match to your question is SCIM — System for Cross-domain Identity Management.

RFC 7643 — SCIM Core Schema⁠Attachment.png defines standard user and group attributes.
RFC 7644 — SCIM Protocol⁠Attachment.png defines operations for managing those resources.
NIST SP 800-63-4⁠Attachment.png covers identity proofing, authentication, and federation.
SCIM is especially interesting because its schema is extensible without requiring everyone to adopt the same application-specific user model.

An ontology perspective
Given your work with RDF and knowledge graphs, I would distinguish three relationships:

A person may possess multiple digital identities.
An identity may be associated with multiple accounts.
An account may have different roles and permissions in different systems.
Those distinctions make a reusable ontology considerably more useful than a conventional Users table.

One question: Are you thinking about user management for your own software projects, or are you looking for a general-purpose ontology that could be reused across applications?

The answer determines whether SCIM alone is sufficient or whether we should examine a broader semantic model.

