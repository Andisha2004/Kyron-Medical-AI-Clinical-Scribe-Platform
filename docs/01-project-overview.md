# Kyron Medical AI Clinical Scribe Platform

## 1. Project Overview

The Kyron Medical AI Clinical Scribe Platform is a provider-facing clinical documentation application that helps physicians and clinical staff convert raw encounter information into structured SOAP notes.

A provider may enter information in three ways:

1. Paste a raw patient encounter transcript.
2. Type freeform clinical observations.
3. Dictate clinical information using a live microphone.

The platform uses artificial intelligence to organize the provided information into the following SOAP sections:

* **Subjective**
* **Objective**
* **Assessment**
* **Plan**

The generated note may also include suggested ICD-10 diagnosis codes based on the clinical information provided.

Providers remain responsible for reviewing, editing, and approving all generated documentation before saving it.

---

## 2. Problem Statement

Clinical providers often spend significant time documenting patient encounters after visits. This administrative work can reduce the time providers have available for direct patient care and may contribute to delayed or incomplete documentation.

Traditional transcription tools may convert speech into text, but they do not always organize the information into a useful clinical format. Providers may still need to manually identify symptoms, examination findings, diagnoses, and treatment plans.

This platform addresses that problem by combining:

* Streaming speech-to-text
* Structured clinical note generation
* Conversational voice editing
* Patient history retrieval
* ICD-10 code suggestions
* Note versioning
* Persistent draft storage

The system is designed to assist the provider rather than replace clinical judgment.

---

## 3. Project Goal

The primary goal is to build a reliable end-to-end clinical documentation workflow in which a provider can:

```text
Log in
→ Create or resume an encounter
→ Enter or dictate clinical information
→ Generate a structured SOAP note
→ Review and edit the note
→ Add or review ICD-10 codes
→ Save the finalized note
→ View previous note versions
```

The application should feel polished, trustworthy, and appropriate for a professional clinical environment.

---

## 4. Primary Users

The system supports two user roles.

### 4.1 Provider

A Provider is a physician or authorized clinical staff member.

Providers can:

* Log in securely
* View only their own encounters
* Create new patient encounters
* Enter patient demographic information
* Paste encounter transcripts
* Type freeform clinical observations
* Dictate clinical information
* Generate SOAP notes
* Edit notes manually
* Edit notes using voice commands
* Search for ICD-10 codes
* Add ICD-10 codes to the Assessment section
* Save finalized notes
* View note version history
* Resume unfinished drafts across browsers or devices

### 4.2 Admin

An Admin manages application-level resources.

Admins can:

* Log in securely
* View encounters across all providers
* Filter encounters by provider and date range
* Add provider accounts
* Deactivate provider accounts
* View provider status
* Create note templates
* Edit note templates
* Delete note templates
* Control how SOAP notes are generated for different encounter types

---

## 5. Core User Workflow

The most important workflow is the provider documentation workflow.

### Step 1: Authentication

The provider signs in using an authorized account.

The backend verifies:

* The email exists
* The password is correct
* The account is active
* The user has the Provider role

### Step 2: Encounter Creation

The provider starts a new encounter by entering:

* Patient first name
* Patient last name
* Patient date of birth
* Selected note template

The system searches for an existing patient using the provided identity fields. If no matching patient exists, a new patient record is created.

### Step 3: Clinical Input

The provider may:

* Paste a transcript
* Type clinical observations
* Start live dictation
* Combine typed and dictated content

The entered information is automatically saved as an encounter draft.

### Step 4: Patient History Retrieval

For returning patients, the backend retrieves relevant prior encounter history from the database.

Previous information may include:

* Diagnoses
* Treatments
* Prior plans
* Relevant follow-up information

The backend provides relevant history to the AI generation service. Patient history is not assembled inside the frontend.

### Step 5: SOAP Note Generation

The provider selects a template and starts note generation.

The backend:

1. Validates the encounter and user permissions.
2. Retrieves the latest template from the database.
3. Retrieves relevant patient history.
4. Builds the clinical generation request.
5. Sends the request to the text-generation model.
6. Streams note content back to the frontend.

The frontend progressively displays the Subjective, Objective, Assessment, and Plan sections.

### Step 6: Note Review and Editing

The provider may edit the generated note:

* Directly in the text editor
* Through voice commands
* By adding an ICD-10 result
* By removing or correcting generated information

The provider remains in control of the final content.

### Step 7: Saving

When the provider saves the note:

* A permanent note version is created.
* The previous version is preserved.
* The saving user and timestamp are recorded.
* An audit event is written.
* The encounter status is updated.

---

## 6. Major Features

### 6.1 Authentication and Role-Based Access

The system supports Provider and Admin roles.

Authorization is enforced by the backend. Hiding a frontend button is not considered sufficient authorization.

Providers may only access encounters that belong to them. Admins may access all encounters and administrative resources.

### 6.2 Encounter Workspace

The encounter workspace is the main provider interface.

It contains:

* Patient information
* Template selection
* Transcript editor
* Clinical observations editor
* Dictation controls
* SOAP note editor
* ICD-10 search
* Voice-editing controls
* Draft save status
* Note version history
* Final save action

### 6.3 Streaming SOAP Generation

SOAP note content must appear progressively while it is generated.

The user should not wait for the entire model response before seeing content.

The system may use:

* Server-Sent Events
* A streamed HTTP response
* WebSockets where appropriate

### 6.4 Live Dictation

The provider may start a hands-free dictation session.

The system should:

* Capture microphone audio
* Send audio through a streaming speech pipeline
* Display partial transcript updates
* Confirm finalized transcript segments
* Incrementally update the SOAP draft
* Support pause, resume, and stop actions

### 6.5 Conversational Voice Editing

After a note has been generated, the provider may issue voice instructions such as:

* “Add that the patient has no fever.”
* “Move the knee pain into Subjective.”
* “Shorten the Plan.”
* “Add osteoarthritis to the Assessment.”

The system should make the smallest change necessary and preserve unrelated note content.

### 6.6 ICD-10 Search

The encounter workspace includes a standalone ICD-10 search tool.

The provider may search using plain English, such as:

```text
right knee arthritis
```

The system returns relevant ICD-10 codes and descriptions.

A selected result may be appended to the Assessment section.

The application uses an internal dataset rather than depending on an external ICD-10 API.

### 6.7 Patient History Context

When a returning patient is identified, the backend retrieves relevant previous encounters.

The AI may use previous diagnoses or treatments when they are clinically relevant to the current encounter.

Historical information must be clearly distinguished from information reported during the current visit.

### 6.8 Draft Persistence

Unfinished encounter work is stored in the database.

The following information may be restored:

* Transcript
* Clinical observations
* SOAP sections
* Selected ICD-10 codes
* Selected template
* Current draft revision

Drafts should survive:

* Browser refreshes
* Browser restarts
* Application restarts
* Login from another supported device

### 6.9 Note Versioning

A saved note is never overwritten.

Each save creates a new note version containing:

* Version number
* Subjective content
* Objective content
* Assessment content
* Plan content
* ICD-10 selections
* Saving user
* Save timestamp
* Generation metadata where applicable

### 6.10 Admin Template Management

Admins may define templates for different encounter types.

Example templates include:

* Orthopedic Follow-Up
* New Patient Evaluation
* Urgent Care Visit

Each template may define instructions for:

* Subjective
* Objective
* Assessment
* Plan
* Documentation style
* Information prioritization

The backend retrieves the latest template during every generation request so that updates take effect without requiring the provider to refresh the page.

---

## 7. Scope

### 7.1 In Scope

The first release includes:

* Provider and Admin authentication
* Role-based authorization
* Patient creation and matching
* Encounter creation
* Encounter draft persistence
* Transcript and observation input
* Streaming SOAP note generation
* Manual note editing
* Conversational voice editing
* Streaming voice dictation
* Patient history retrieval
* ICD-10 search
* Note versioning
* Audit logging
* Provider administration
* Template administration
* AWS EC2 hosting
* AWS RDS persistence
* HTTPS
* Reverse proxy configuration
* Secrets management
* Automated testing

### 7.2 Out of Scope

The first release does not include:

* Integration with a production electronic health record
* Electronic prescribing
* Insurance eligibility verification
* Claims submission
* Medical billing
* Real patient identity verification
* Real hospital deployment
* Full HIPAA certification
* Medical image analysis
* Laboratory integration
* Scheduling
* Patient-facing access
* Native mobile applications
* Full international diagnosis-code support

These features may be considered future work but are not required for the technical-screen implementation.

---

## 8. Technical Priorities

The project is intentionally large. Implementation will prioritize the following areas.

### Priority 1: Core Clinical Workflow

The following workflow must function reliably:

```text
Create encounter
→ Enter clinical information
→ Generate SOAP note
→ Edit note
→ Save note
→ Retrieve saved version
```

### Priority 2: Persistent Storage

All required persistent information must be stored in AWS RDS.

The application must not depend on:

* SQLite
* Flat files
* Process memory
* Temporary server storage

for information that must survive a server restart.

### Priority 3: Streaming

SOAP generation and speech transcription should feel responsive.

The interface should update progressively rather than showing a long loading state followed by a complete content dump.

### Priority 4: Security and Authorization

The backend must enforce:

* Authentication
* Role permissions
* Provider encounter ownership
* Active-account checks
* Protected secrets
* Private database access

### Priority 5: Infrastructure Reliability

The deployed system should use:

* AWS EC2
* nginx
* HTTPS
* AWS RDS
* Private RDS networking
* Database connection pooling
* AWS Secrets Manager or Parameter Store

### Priority 6: Voice Features

Voice editing and live dictation should be implemented after the core typed workflow is reliable.

---

## 9. Non-Happy-Path Behavior

The application should handle failures without losing provider work or generating misleading clinical content.

### 9.1 Insufficient Clinical Information

If the transcript does not contain enough clinical information, the system should not generate a fabricated SOAP note.

Example input:

```text
Hello, okay, thank you. See you later.
```

Expected response:

```text
There is not enough clinical information to generate a reliable SOAP note.
Please add symptoms, relevant history, examination findings, or treatment information.
```

### 9.2 Expired Session During Save

If the provider’s session expires while saving:

* Current note content remains visible.
* A recovery copy is preserved.
* The provider is asked to sign in again.
* The save may be retried after authentication.
* Duplicate note versions should not be created.

### 9.3 Deactivated Provider

If an Admin deactivates a Provider:

* New authenticated actions are rejected.
* The frontend displays a clear account-status message.
* Existing work is not silently deleted.
* The user cannot access other application data.

### 9.4 AI Service Failure

If an AI service is unavailable:

* Existing transcript and note content remain available.
* The user receives a clear retry message.
* The system does not save a partial result as a finalized note automatically.

---

## 10. Success Criteria

The project will be considered successful when the following conditions are met.

### Core Workflow

* A Provider can authenticate.
* A Provider can create an encounter.
* A Provider can enter clinical information.
* A SOAP note is streamed progressively.
* The note contains all four SOAP sections.
* At least one relevant ICD-10 suggestion may be included.
* The Provider can edit the result.
* The Provider can save the note.
* Saved notes remain available after application restart.

### Access Control

* Providers cannot access other providers’ encounters.
* Admins can view encounters across providers.
* Provider-only and Admin-only routes are protected by the backend.
* Deactivated accounts are blocked.

### Persistence

* Patients are stored in RDS.
* Encounters are stored in RDS.
* Drafts are stored in RDS.
* Note versions are stored in RDS.
* Templates are stored in RDS.
* Audit logs are stored in RDS.

### Streaming and Voice

* Transcript partials appear during dictation.
* Final transcript segments are preserved.
* The SOAP note evolves during dictation.
* A voice instruction can modify the note.
* The provider may interrupt or continue the voice conversation.

### Infrastructure

* The application is accessible through HTTPS.
* nginx is the public reverse proxy.
* Application services are not directly exposed on ports 80 or 443.
* RDS is not publicly accessible.
* RDS accepts traffic only from permitted infrastructure.
* Database connections use pooling.
* Secrets are not stored in the repository.

### User Experience

* The encounter workspace is clean and readable.
* The user can see whether work is saved.
* Errors are understandable.
* The system does not fabricate a note from meaningless input.
* The application feels complete along its main workflow.

---

## 11. Proposed Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* Streamed Fetch or Server-Sent Events
* WebSocket support for voice features

### Backend

* FastAPI
* Python
* Pydantic
* SQLAlchemy
* Alembic
* Async PostgreSQL driver
* JWT or secure session-based authentication
* pytest

### Database

* AWS RDS PostgreSQL

### AI Services

The architecture separates the following responsibilities:

* Text generation for structured SOAP notes
* Streaming speech-to-text for dictation
* Realtime conversational processing for voice editing

Specific providers and models are documented separately in the AI architecture document.

### Infrastructure

* AWS EC2
* nginx
* AWS RDS
* AWS Secrets Manager or Systems Manager Parameter Store
* Valid SSL certificate
* Private VPC database communication

---

## 12. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                           USERS                             │
│                                                             │
│                 Provider                  Admin              │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       NEXT.JS FRONTEND                      │
│                                                             │
│  Login                                                      │
│  Provider Dashboard                                         │
│  Encounter Workspace                                        │
│  Admin Dashboard                                             │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST / Streaming / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                      │
│                                                             │
│  Authentication                                             │
│  Encounter Management                                       │
│  Note Generation                                            │
│  Voice Processing                                           │
│  ICD-10 Search                                              │
│  Template Management                                        │
│  Versioning                                                 │
│  Audit Logging                                              │
└──────────────────┬───────────────────────┬──────────────────┘
                   │                       │
                   ▼                       ▼
┌────────────────────────────┐  ┌────────────────────────────┐
│ AWS RDS PostgreSQL         │  │ External AI Services       │
│                            │  │                            │
│ Users                      │  │ Text-generation model      │
│ Patients                   │  │ Streaming speech-to-text   │
│ Encounters                 │  │ Realtime voice assistant   │
│ Notes and Versions         │  │                            │
│ Templates                  │  └────────────────────────────┘
│ ICD-10 Codes               │
│ Audit Logs                 │
└────────────────────────────┘
```

---

## 13. Engineering Principles

The implementation follows these engineering principles.

### Provider Control

AI-generated content is always editable and requires provider review.

### Minimum Necessary AI Behavior

The AI should make only the changes requested and should not rewrite unrelated content unnecessarily.

### No Unsupported Clinical Claims

The system should not invent:

* Symptoms
* Examination findings
* Vital signs
* Diagnoses
* Test results
* Medications
* Treatments

### Backend-Enforced Security

Authorization decisions are made by the backend rather than relying on frontend visibility.

### Persistent-by-Default Design

Information that users expect to recover is stored in the database.

### Append-Only Version History

Previous saved note versions are preserved rather than overwritten.

### Clear Service Boundaries

Clinical generation, speech recognition, voice editing, persistence, and authorization are implemented as separate responsibilities.

### Graceful Failure

Failures should preserve work and provide useful recovery instructions.

---

## 14. Future Enhancements

Potential future improvements include:

* Provider-specific writing-style adaptation
* Clinical red-flag detection
* Visual differences between note versions
* Structured PDF exports
* EHR integration using healthcare interoperability standards
* Organization-level access control
* Refresh-token rotation
* Advanced patient matching
* Expanded ICD-10 coverage
* Clinical terminology normalization
* Human review analytics
* Model-performance monitoring
* More detailed audit reporting

---

## 15. Related Documentation

Additional design documents are maintained in the `docs` directory:

```text
docs/
├── 01-project-overview.md
├── 02-requirements.md
├── 03-use-cases-and-user-flows.md
├── 04-frontend-design.md
├── 05-system-architecture.md
├── 06-database-design.md
├── 07-api-design.md
├── 08-ai-and-voice-architecture.md
├── 09-security-and-infrastructure.md
├── 10-testing-strategy.md
└── 11-implementation-plan.md
```
