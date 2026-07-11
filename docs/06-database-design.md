# Database Design

## Overview

The Kyron Medical AI Clinical Scribe Platform uses **PostgreSQL** hosted on **AWS RDS** as its primary relational database.

The database is designed to:

* minimize duplicated data
* preserve note history
* support draft persistence
* enforce relationships using foreign keys
* separate business entities into independent tables

---

# Entity Relationship Diagram

<img width="1536" height="1024" alt="ChatGPT Image Jul 11, 2026, 06_08_48 PM" src="https://github.com/user-attachments/assets/e9ec145f-2ccd-4af6-bac9-8fb2d58162d7" />


---

# Database Design Goals

The schema was designed with the following goals:

* Normalize related data
* Preserve historical information
* Support future scalability
* Keep frequently queried data indexed
* Separate authentication from clinical data

---

# Main Entities

## Users

Stores authentication and authorization information.

Responsibilities:

* Login credentials
* User role
* Account status

One user can be associated with one provider profile.

---

## Provider Profiles

Stores provider-specific information.

Examples:

* Name
* Specialty

Separating provider information from authentication allows the authentication model to remain simple while supporting future expansion.

---

## Patients

Stores patient demographic information.

Each patient may have multiple encounters over time.

A patient is identified using:

* First name
* Last name
* Date of birth

---

## Encounters

Represents a single clinical visit.

Each encounter belongs to:

* one patient
* one provider
* one note template

Each encounter can have:

* one active draft
* one clinical note
* multiple note versions

---

## Encounter Drafts

Stores the current in-progress work.

Drafts allow providers to:

* refresh the page
* continue work later
* resume work from another device

without losing information.

---

## Notes

Represents the logical clinical note associated with an encounter.

A note itself never changes.

Instead, every save creates a new version.

---

## Note Versions

Stores every saved version of a SOAP note.

Each version includes:

* Subjective
* Objective
* Assessment
* Plan
* ICD-10 selections
* Save timestamp
* Saving provider

This design provides complete version history while preventing accidental data loss.

---

## Templates

Stores note-generation templates.

Templates define how SOAP notes should be organized for different encounter types.

Example templates:

* Orthopedic Follow-Up
* New Patient Visit
* Urgent Care

---

## Template Sections

Stores section-specific prompt instructions for:

* Subjective
* Objective
* Assessment
* Plan

Separating template sections makes templates easier to update and extend.

---

## ICD-10 Codes

Stores searchable diagnosis codes.

The application searches this table locally instead of depending on an external API.

---

## Audit Logs

Stores important application events.

Examples include:

* User login
* Encounter creation
* Note save
* Template update
* Provider deactivation

Audit logs improve traceability and debugging.

---

# Relationships

The database follows these primary relationships.

```text
User
   │
   └── Provider Profile

Provider
   │
   └── Encounters

Patient
   │
   └── Encounters

Encounter
   ├── Draft
   ├── Note
   └── Template

Note
   └── Note Versions
```

---

# Versioning Strategy

Instead of updating a saved note directly, each save creates a new row in the **Note Versions** table.

Benefits include:

* Complete history
* Easy rollback
* Auditability
* No accidental overwrites

---

# Draft Strategy

Drafts are stored separately from finalized note versions.

This allows providers to:

* automatically save progress
* resume unfinished work
* avoid creating unnecessary note versions while editing

---

# Security Considerations

The database is protected by:

* Private AWS RDS networking
* Foreign key constraints
* Indexed primary keys
* Backend authorization
* AWS Secrets Manager for credentials

The frontend never connects directly to the database.

---

# Future Improvements

Potential future enhancements include:

* Soft deletes
* Full-text search
* Encounter tags
* Multi-organization support
* Provider preferences
* Patient attachments
* Optimized search indexes
