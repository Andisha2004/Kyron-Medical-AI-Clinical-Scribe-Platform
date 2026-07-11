# Software Requirements Specification

## Kyron Medical AI Clinical Scribe Platform

## 1. Purpose

This document defines the functional and nonfunctional requirements for the Kyron Medical AI Clinical Scribe Platform.

The requirements are written so that each one can be:

* Implemented
* Tested
* Demonstrated
* Traced to a project feature

Each requirement has:

* A unique identifier
* A priority
* A description
* Acceptance criteria

---

## 2. Requirement Priority Levels

The project uses the following priority levels.

### Must Have

A requirement that is necessary for the core product or explicitly required by the technical challenge.

### Should Have

A requirement that significantly improves the product but may be simplified if time is limited.

### Could Have

A useful enhancement that may be implemented after the core system is stable.

### Out of Scope

A feature that is intentionally excluded from the first release.

---

## 3. User Roles

The system supports two roles.

### Provider

A medical provider or authorized clinical staff member who creates and manages clinical encounters.

### Admin

An administrative user who manages providers, templates, and system-wide encounter access.

---

# 4. Functional Requirements

## 4.1 Authentication and Authorization

### FR-AUTH-01: User Login

**Priority:** Must Have

The system shall allow a user to log in using an email address and password.

#### Acceptance Criteria

* The user can submit an email and password.
* Valid credentials create an authenticated session.
* Invalid credentials return a clear error.
* The password is not returned to the frontend.
* The user is redirected to the correct dashboard based on role.

---

### FR-AUTH-02: Password Security

**Priority:** Must Have

The system shall store passwords using a secure password-hashing algorithm.

#### Acceptance Criteria

* Plaintext passwords are never stored.
* Password hashes are created using Argon2, bcrypt, or an equivalent secure algorithm.
* Password verification occurs only in the backend.

---

### FR-AUTH-03: Role Recognition

**Priority:** Must Have

The system shall recognize whether the authenticated user is a Provider or Admin.

#### Acceptance Criteria

* Provider users are directed to the Provider dashboard.
* Admin users are directed to the Admin dashboard.
* Role information is verified by the backend.
* The frontend does not determine authorization by itself.

---

### FR-AUTH-04: Provider Data Isolation

**Priority:** Must Have

A Provider shall only be able to access encounters assigned to that Provider.

#### Acceptance Criteria

* A Provider cannot retrieve another Provider’s encounter.
* A Provider cannot edit another Provider’s encounter.
* A Provider cannot save a note for another Provider’s encounter.
* Unauthorized access attempts return HTTP 403 or HTTP 404.

---

### FR-AUTH-05: Admin Access

**Priority:** Must Have

An Admin shall be able to view encounters belonging to all Providers.

#### Acceptance Criteria

* The Admin can view a system-wide encounter list.
* The Admin can filter encounters by Provider.
* The Admin can filter encounters by date range.
* Provider-only restrictions do not block an authorized Admin.

---

### FR-AUTH-06: Account Deactivation

**Priority:** Must Have

An Admin shall be able to deactivate a Provider account.

#### Acceptance Criteria

* A deactivated Provider cannot log in.
* A currently authenticated deactivated Provider is blocked on the next protected request.
* Existing data is preserved.
* Open draft content is not silently deleted.

---

### FR-AUTH-07: Demo Accounts

**Priority:** Must Have

The system shall include at least three Provider accounts and one Admin account for demonstration.

#### Acceptance Criteria

* Demo accounts are created through a seed script.
* Demo credentials are not hardcoded in frontend application logic.
* All four accounts can be used during the walkthrough.

---

### FR-AUTH-08: Logout

**Priority:** Should Have

The system shall allow an authenticated user to log out.

#### Acceptance Criteria

* The session is invalidated or removed.
* The user is returned to the login page.
* Protected pages are no longer accessible.

---

## 4.2 Patient Management

### FR-PAT-01: Create Patient

**Priority:** Must Have

The system shall allow a Provider to create a patient using:

* First name
* Last name
* Date of birth

#### Acceptance Criteria

* All three fields are required.
* The date of birth must be a valid date.
* The patient is stored in the database.
* The created patient receives a unique identifier.

---

### FR-PAT-02: Match Existing Patient

**Priority:** Must Have

The system shall search for an existing patient using first name, last name, and date of birth.

#### Acceptance Criteria

* Matching is performed by the backend.
* A matching patient is reused rather than duplicated.
* Name values are normalized before comparison.
* The Provider is informed when prior patient history exists.

---

### FR-PAT-03: Patient Encounter History

**Priority:** Must Have

The system shall retrieve previous saved encounters for a returning patient.

#### Acceptance Criteria

* Previous encounters are retrieved from the database.
* History retrieval occurs in the backend.
* The frontend does not manually assemble prior notes into an AI prompt.
* The returned history belongs to the correct patient.

---

### FR-PAT-04: Relevant History Selection

**Priority:** Should Have

The system should select clinically relevant history before note generation.

#### Acceptance Criteria

* The system limits the number of prior notes included.
* Relevant diagnoses and treatments are prioritized.
* Current and historical information are clearly distinguished.
* The generation prompt does not include unlimited patient history.

---

## 4.3 Encounter Management

### FR-ENC-01: Create Encounter

**Priority:** Must Have

A Provider shall be able to create a new encounter.

#### Acceptance Criteria

* The encounter is linked to one patient.
* The encounter is linked to the authenticated Provider.
* The encounter has a creation timestamp.
* The initial encounter status is Draft.
* The Provider is redirected to the encounter workspace.

---

### FR-ENC-02: Select Note Template

**Priority:** Must Have

A Provider shall select a note template for an encounter.

#### Acceptance Criteria

* Active templates are displayed.
* The selected template identifier is stored with the encounter or draft.
* The backend retrieves the latest template before generation.
* Deleted or inactive templates cannot be selected for new encounters.

---

### FR-ENC-03: Enter Transcript

**Priority:** Must Have

A Provider shall be able to paste or type a raw encounter transcript.

#### Acceptance Criteria

* The transcript appears in an editable text area.
* The Provider can modify the transcript.
* Changes are included in draft persistence.
* Long transcripts do not break the workspace layout.

---

### FR-ENC-04: Enter Clinical Observations

**Priority:** Must Have

A Provider shall be able to type freeform clinical observations.

#### Acceptance Criteria

* Observations are editable.
* Observations are stored separately from the raw transcript.
* Observations are available to note generation.
* Observations are restored with the draft.

---

### FR-ENC-05: View Provider Encounters

**Priority:** Must Have

A Provider shall be able to view a list of their encounters.

#### Acceptance Criteria

* Only encounters belonging to the authenticated Provider are shown.
* Each row includes patient name, date, status, and last update time.
* Draft and completed encounters are distinguishable.
* The Provider can open an encounter.

---

### FR-ENC-06: View Encounter Details

**Priority:** Must Have

A Provider shall be able to open an encounter workspace.

#### Acceptance Criteria

* Patient information is displayed.
* Transcript and observation fields are displayed.
* Current SOAP content is displayed.
* Draft status is displayed.
* Unauthorized Providers cannot open the workspace.

---

## 4.4 Draft Persistence

### FR-DRAFT-01: Automatic Draft Saving

**Priority:** Must Have

The system shall automatically save in-progress encounter data.

#### Acceptance Criteria

The following data is persisted:

* Transcript
* Clinical observations
* Subjective section
* Objective section
* Assessment section
* Plan section
* Selected ICD-10 codes
* Selected template
* Draft revision
* Last update time

---

### FR-DRAFT-02: Debounced Saving

**Priority:** Should Have

Drafts should be saved after a short period of inactivity rather than after every keystroke.

#### Acceptance Criteria

* Typing remains responsive.
* Repeated edits do not create excessive database requests.
* A visible save state is shown.
* The latest content is eventually persisted.

---

### FR-DRAFT-03: Restore After Refresh

**Priority:** Must Have

The system shall restore an unfinished draft after a page refresh.

#### Acceptance Criteria

* The transcript is restored.
* The SOAP note is restored.
* Selected ICD-10 codes are restored.
* The selected template is restored.
* No manual recovery step is required.

---

### FR-DRAFT-04: Restore Across Devices

**Priority:** Must Have

The system shall restore an unfinished draft when the same Provider signs in from another supported browser or device.

#### Acceptance Criteria

* Draft data comes from the database.
* The system does not rely only on browser local storage.
* The latest saved revision is shown.
* The Provider can continue working.

---

### FR-DRAFT-05: Draft Revision Control

**Priority:** Should Have

The system should maintain a draft revision number to detect stale updates.

#### Acceptance Criteria

* Each successful draft save increments the revision.
* A stale save does not silently overwrite a newer draft.
* The client receives the current revision.
* Conflicts produce a recoverable response.

---

### FR-DRAFT-06: Save Status Indicator

**Priority:** Should Have

The workspace shall display the current persistence state.

#### Acceptance Criteria

The interface may display:

* Saving
* Draft saved
* Unsaved changes
* Save failed

---

## 4.5 SOAP Note Generation

### FR-NOTE-01: Generate SOAP Note

**Priority:** Must Have

The system shall generate a structured SOAP note from transcript and observation content.

#### Acceptance Criteria

The output includes:

* Subjective
* Objective
* Assessment
* Plan

---

### FR-NOTE-02: Streaming Generation

**Priority:** Must Have

The system shall progressively display generated note content.

#### Acceptance Criteria

* Content appears before the entire model response is complete.
* The page does not reload.
* The user sees note sections evolve.
* The interface does not wait for a full response before rendering begins.

---

### FR-NOTE-03: Structured Output

**Priority:** Must Have

The AI generation service shall return structured note content.

#### Acceptance Criteria

* Each SOAP section is represented separately.
* The backend validates the generated structure.
* Invalid model output is handled gracefully.
* The frontend does not depend on unreliable Markdown parsing.

---

### FR-NOTE-04: Template-Aware Generation

**Priority:** Must Have

The selected note template shall affect SOAP note generation.

#### Acceptance Criteria

* Template instructions are retrieved from the database.
* Different templates produce visibly different note organization or emphasis.
* The latest saved template is used for each generation request.
* A page refresh is not required after an Admin updates a template.

---

### FR-NOTE-05: Patient History Injection

**Priority:** Must Have

The backend shall include relevant prior patient history during note generation.

#### Acceptance Criteria

* History retrieval occurs through a backend service or function.
* Returning-patient generation differs from first-time-patient generation where clinically relevant.
* Historical information is not presented as newly reported information.
* Unrelated history is excluded where possible.

---

### FR-NOTE-06: ICD-10 Suggestion

**Priority:** Must Have

The generated Assessment shall include at least one suggested ICD-10 code when clinically supported.

#### Acceptance Criteria

* A code and description are provided.
* The suggestion is related to the encounter content.
* The UI clearly treats the code as a suggestion.
* The Provider can edit or remove the suggestion.

---

### FR-NOTE-07: No Unsupported Clinical Information

**Priority:** Must Have

The AI shall not intentionally invent unsupported clinical facts.

#### Acceptance Criteria

The system prompt prohibits fabrication of:

* Symptoms
* Vital signs
* Examination findings
* Diagnoses
* Laboratory results
* Imaging results
* Medications
* Treatments

If information is missing, the system may omit it or state that it was not provided.

---

### FR-NOTE-08: Preserve Clinical Negations

**Priority:** Must Have

The system shall preserve meaningful negative findings.

#### Acceptance Criteria

Statements such as the following are retained accurately:

* Denies fever
* No chest pain
* No shortness of breath
* No recent trauma

---

### FR-NOTE-09: Manual Note Editing

**Priority:** Must Have

The Provider shall be able to edit all SOAP sections directly.

#### Acceptance Criteria

* Every section is editable.
* Manual edits update local state immediately.
* Manual edits are included in draft persistence.
* Manual edits are included in the next saved version.

---

### FR-NOTE-10: Generation Failure Recovery

**Priority:** Must Have

If note generation fails, existing work shall remain available.

#### Acceptance Criteria

* Transcript content remains visible.
* Existing note content remains visible.
* The Provider receives a clear error.
* The Provider may retry.
* A failed generation is not automatically saved as final.

---

## 4.6 Meaningless or Insufficient Input

### FR-INPUT-01: Detect Insufficient Clinical Content

**Priority:** Must Have

The system shall detect input that lacks enough clinical information for a reliable SOAP note.

#### Acceptance Criteria

* The system does not fabricate a complete note.
* A clear explanatory message is displayed.
* The user is asked to add symptoms, history, findings, or treatment information.
* Existing input is preserved.

---

### FR-INPUT-02: Empty Input Validation

**Priority:** Must Have

The system shall prevent generation when both transcript and observations are empty.

#### Acceptance Criteria

* The Generate button is disabled or the request is rejected.
* A clear validation message appears.
* No AI request is sent.

---

## 4.7 ICD-10 Search

### FR-ICD-01: Internal ICD-10 Dataset

**Priority:** Must Have

The system shall use an internal ICD-10 dataset containing at least 200 to 300 codes.

#### Acceptance Criteria

* Codes are stored or seeded within the application database.
* The system does not depend on an external ICD-10 API.
* Each entry includes a code and description.
* The dataset survives server restart.

---

### FR-ICD-02: Plain-English Search

**Priority:** Must Have

A Provider shall be able to search ICD-10 codes using plain English.

#### Acceptance Criteria

Example queries may include:

* Knee arthritis
* Sore throat
* High blood pressure
* Lower-back pain

Relevant results are returned.

---

### FR-ICD-03: Ranked Results

**Priority:** Must Have

The system shall return the most relevant ICD-10 results first.

#### Acceptance Criteria

* Results include a relevance score or ordered rank internally.
* Exact or close semantic matches appear near the top.
* At least the top five results may be returned.
* Empty queries do not perform unnecessary searches.

---

### FR-ICD-04: Add Code to Assessment

**Priority:** Must Have

A Provider shall be able to append a selected ICD-10 code to the Assessment section.

#### Acceptance Criteria

* Clicking a result updates the Assessment.
* The code and description are included.
* The selection is saved in the encounter draft.
* Duplicate additions are prevented or clearly handled.

---

### FR-ICD-05: Remove Selected Code

**Priority:** Should Have

A Provider should be able to remove an added ICD-10 code.

#### Acceptance Criteria

* The code is removed from the Assessment or selected-code list.
* The draft is updated.
* Other note content remains unchanged.

---

## 4.8 Note Saving and Versioning

### FR-VERS-01: Save Finalized Note

**Priority:** Must Have

A Provider shall be able to save the reviewed SOAP note.

#### Acceptance Criteria

* The note is stored in the database.
* All four SOAP sections are stored.
* Selected ICD-10 codes are stored.
* The saving Provider is recorded.
* The save timestamp is recorded.

---

### FR-VERS-02: Create New Version

**Priority:** Must Have

Every save after a note has already been saved shall create a new version.

#### Acceptance Criteria

* Version numbers increase sequentially.
* The previous version remains unchanged.
* A new row is inserted for the new version.
* Saving does not overwrite the previous version.

---

### FR-VERS-03: Version History

**Priority:** Must Have

A Provider shall be able to view the full version history of a note.

#### Acceptance Criteria

Each version displays:

* Version number
* Saving user
* Save timestamp
* Note content or access to note content

---

### FR-VERS-04: Version Ownership

**Priority:** Must Have

Only authorized users shall be able to view note versions.

#### Acceptance Criteria

* Providers may view versions for their own encounters.
* Admins may view versions across Providers.
* Unauthorized users receive an access error.

---

### FR-VERS-05: Version Diff

**Priority:** Could Have

The system may display the differences between two note versions.

#### Acceptance Criteria

* Added text is distinguishable.
* Removed text is distinguishable.
* Unchanged text remains readable.
* The diff does not modify stored versions.

---

### FR-VERS-06: Idempotent Save

**Priority:** Should Have

Repeated submission of the same save request should not create accidental duplicate versions.

#### Acceptance Criteria

* Save requests may include an idempotency key.
* Retried requests return the original result.
* Network retries do not create duplicate versions.

---

## 4.9 Live Voice Dictation

### FR-DICT-01: Start Dictation

**Priority:** Must Have

A Provider shall be able to start a live dictation session.

#### Acceptance Criteria

* The browser requests microphone permission.
* Audio streaming begins after permission is granted.
* A visible listening indicator appears.
* Failure to access the microphone is handled clearly.

---

### FR-DICT-02: Streaming Speech-to-Text

**Priority:** Must Have

The system shall use a streaming speech pipeline.

#### Acceptance Criteria

* Audio is sent while the Provider is speaking.
* Partial transcript updates appear in real time.
* The system does not wait for the full recording to finish.
* Final transcript segments are distinguishable from temporary partials.

---

### FR-DICT-03: Live Transcript Display

**Priority:** Must Have

The encounter transcript shall update while dictation is active.

#### Acceptance Criteria

* Partial words or phrases appear during speech.
* Finalized segments are preserved.
* Existing transcript content is not removed.
* Transcript updates remain editable.

---

### FR-DICT-04: Live SOAP Updates

**Priority:** Must Have

The SOAP note shall update while dictation continues.

#### Acceptance Criteria

* Final transcript segments trigger note updates.
* SOAP sections visibly evolve.
* The system does not regenerate the note on every partial word.
* Unrelated note content is preserved.

---

### FR-DICT-05: Pause Dictation

**Priority:** Must Have

The Provider shall be able to pause dictation.

#### Acceptance Criteria

* Audio transmission stops or is ignored.
* Existing transcript remains visible.
* Existing SOAP content remains visible.
* The Provider can later resume.

---

### FR-DICT-06: Resume Dictation

**Priority:** Must Have

The Provider shall be able to resume a paused dictation session.

#### Acceptance Criteria

* New speech is appended to the existing context.
* Previous transcript content is retained.
* Previous SOAP content is retained.
* The session continues without creating a new encounter.

---

### FR-DICT-07: Stop Dictation

**Priority:** Must Have

The Provider shall be able to stop dictation.

#### Acceptance Criteria

* Audio streaming ends.
* Final transcript segments are processed.
* Draft content remains editable.
* The current draft is saved.

---

### FR-DICT-08: Dictation Revision Synchronization

**Priority:** Should Have

The system should prevent stale AI updates from overwriting newer manual edits.

#### Acceptance Criteria

* AI update requests include a base revision.
* Responses are checked against the current revision.
* Stale responses are rejected or safely rebased.
* Manual Provider edits take priority.

---

## 4.10 Conversational Voice Editing

### FR-VOICE-01: Start Voice Editing Session

**Priority:** Must Have

A Provider shall be able to start a conversational note-editing session.

#### Acceptance Criteria

* Microphone access is available.
* The current note state is available to the editing service.
* A visible voice-session status is displayed.
* The Provider can stop the session.

---

### FR-VOICE-02: Natural-Language Edit Commands

**Priority:** Must Have

The system shall accept natural-language editing instructions.

#### Acceptance Criteria

The system supports commands such as:

* Add information
* Remove information
* Replace information
* Move information between sections
* Shorten a section
* Clarify a section

---

### FR-VOICE-03: Structured Edit Operations

**Priority:** Must Have

Voice instructions shall be converted into structured edit operations.

#### Acceptance Criteria

The edit operation identifies:

* Operation type
* Target section
* Target text where applicable
* Replacement or added text
* Source section where applicable

---

### FR-VOICE-04: Minimal Change Behavior

**Priority:** Must Have

Voice editing shall preserve unrelated note content.

#### Acceptance Criteria

* Only the requested section or text is changed.
* Other SOAP sections remain unchanged.
* The Provider can review the applied change.
* The edit is included in draft persistence.

---

### FR-VOICE-05: Immediate Workspace Update

**Priority:** Must Have

Accepted voice edits shall update the note workspace immediately.

#### Acceptance Criteria

* The visible note changes without a page refresh.
* A confirmation message is shown or spoken.
* The updated note becomes editable immediately.
* The draft is automatically saved.

---

### FR-VOICE-06: Continuous Conversation

**Priority:** Must Have

The Provider shall be able to make multiple edits within one voice session.

#### Acceptance Criteria

* The session retains recent conversational context.
* Follow-up commands can refer to the previous command.
* The current note state is refreshed after each edit.
* The Provider does not need to restart the session for every command.

---

### FR-VOICE-07: Interruption

**Priority:** Must Have

The Provider shall be able to interrupt the voice assistant.

#### Acceptance Criteria

* Assistant audio stops when Provider speech begins.
* The new instruction is processed.
* The session remains active.
* Previous accepted edits are preserved.

---

### FR-VOICE-08: Voice Edit Audit Event

**Priority:** Should Have

Applied voice edits should be recorded in the audit log.

#### Acceptance Criteria

* The action type is recorded.
* The encounter identifier is recorded.
* The acting Provider is recorded.
* Clinical text may be minimized or excluded from logs where appropriate.

---

## 4.11 Admin Provider Management

### FR-ADMIN-01: View Providers

**Priority:** Must Have

An Admin shall be able to view the Provider roster.

#### Acceptance Criteria

Each Provider row displays:

* Name
* Email
* Active status
* Creation date
* Specialty where available

---

### FR-ADMIN-02: Add Provider

**Priority:** Must Have

An Admin shall be able to create a Provider account.

#### Acceptance Criteria

* Email uniqueness is enforced.
* Required fields are validated.
* A securely hashed password is stored.
* The new Provider can log in if active.
* An audit event is created.

---

### FR-ADMIN-03: Deactivate Provider

**Priority:** Must Have

An Admin shall be able to deactivate a Provider.

#### Acceptance Criteria

* The Provider is marked inactive.
* Historical encounters remain unchanged.
* The Provider cannot perform protected actions.
* An audit event is created.

---

### FR-ADMIN-04: Reactivate Provider

**Priority:** Could Have

An Admin may be able to reactivate a previously deactivated Provider.

#### Acceptance Criteria

* The account becomes active.
* Existing data remains linked.
* The Provider can log in again.
* The action is audited.

---

## 4.12 Admin Encounter Management

### FR-ADMIN-ENC-01: View All Encounters

**Priority:** Must Have

An Admin shall be able to view all encounters.

#### Acceptance Criteria

Each encounter row displays:

* Provider
* Patient
* Encounter date
* Status
* Template
* Last update time

---

### FR-ADMIN-ENC-02: Filter by Provider

**Priority:** Must Have

An Admin shall be able to filter encounters by Provider.

#### Acceptance Criteria

* A Provider filter is available.
* Only matching encounters are shown.
* Clearing the filter restores the full list.

---

### FR-ADMIN-ENC-03: Filter by Date Range

**Priority:** Must Have

An Admin shall be able to filter encounters by date range.

#### Acceptance Criteria

* Start and end dates are supported.
* Invalid ranges produce validation errors.
* Results are filtered by encounter date.
* Provider and date filters can be combined.

---

## 4.13 Template Management

### FR-TEMP-01: View Templates

**Priority:** Must Have

An Admin shall be able to view all note templates.

#### Acceptance Criteria

Each template displays:

* Name
* Description
* Active status
* Last update time

---

### FR-TEMP-02: Create Template

**Priority:** Must Have

An Admin shall be able to create a note template.

#### Acceptance Criteria

A template may include:

* Name
* Description
* General system instructions
* Subjective instructions
* Objective instructions
* Assessment instructions
* Plan instructions

---

### FR-TEMP-03: Edit Template

**Priority:** Must Have

An Admin shall be able to edit an existing template.

#### Acceptance Criteria

* Changes are stored in the database.
* The update timestamp changes.
* An audit event is created.
* The next generation request uses the updated version.

---

### FR-TEMP-04: Delete Template

**Priority:** Must Have

An Admin shall be able to delete or deactivate a template.

#### Acceptance Criteria

* The template is no longer available for new selections.
* Existing encounters remain valid.
* The action does not corrupt historical notes.
* The action is audited.

---

### FR-TEMP-05: Immediate Template Effect

**Priority:** Must Have

Template changes shall take effect for the next generation request without a Provider page refresh.

#### Acceptance Criteria

* The backend retrieves the current template at generation time.
* The frontend does not rely on an old template prompt.
* A demonstration can show changed output after an Admin edit.

---

## 4.14 Audit Logging

### FR-AUDIT-01: Record Important Actions

**Priority:** Must Have

The system shall record important application actions.

#### Acceptance Criteria

At minimum, audit events are created for:

* Login
* Encounter creation
* Note generation
* Note save
* Template creation
* Template update
* Template deletion
* Provider creation
* Provider deactivation

---

### FR-AUDIT-02: Audit Event Metadata

**Priority:** Must Have

Each audit event shall include sufficient metadata.

#### Acceptance Criteria

Each event includes:

* Event identifier
* Actor user identifier where available
* Action type
* Entity type
* Entity identifier where available
* Timestamp
* Additional non-sensitive metadata where appropriate

---

### FR-AUDIT-03: Persistent Audit Storage

**Priority:** Must Have

Audit logs shall be stored in AWS RDS.

#### Acceptance Criteria

* Logs survive application restart.
* Logs are not stored only in process memory.
* Logs are not stored only in local files.
* Audit data can be queried by the backend.

---

# 5. Nonfunctional Requirements

## 5.1 Security Requirements

### NFR-SEC-01: HTTPS

**Priority:** Must Have

The deployed application shall be accessible over HTTPS using a valid SSL certificate.

#### Acceptance Criteria

* The browser shows a valid secure connection.
* A self-signed certificate is not used.
* HTTP traffic redirects to HTTPS where appropriate.

---

### NFR-SEC-02: Reverse Proxy

**Priority:** Must Have

The application shall use nginx or an equivalent reverse proxy.

#### Acceptance Criteria

* nginx receives public traffic.
* Backend processes are not directly exposed on ports 80 or 443.
* API and WebSocket traffic are proxied correctly.

---

### NFR-SEC-03: Private Database

**Priority:** Must Have

The RDS instance shall not be publicly accessible.

#### Acceptance Criteria

* RDS public access is disabled.
* The database security group does not allow unrestricted internet access.
* Database traffic is accepted only from approved infrastructure.
* The configuration can be shown in the AWS console.

---

### NFR-SEC-04: Secret Management

**Priority:** Must Have

Production secrets shall be stored using AWS Secrets Manager or AWS Systems Manager Parameter Store.

#### Acceptance Criteria

The following are not hardcoded:

* Database password
* Database URL
* AI API keys
* JWT secret
* Voice-service credentials

---

### NFR-SEC-05: No Committed Secrets

**Priority:** Must Have

The public GitHub repository shall not contain credentials or production `.env` files.

#### Acceptance Criteria

* `.env` files are included in `.gitignore`.
* A safe `.env.example` may be included.
* Git history does not contain exposed keys.
* Secret scanning finds no production credentials.

---

### NFR-SEC-06: Secure Cookies or Tokens

**Priority:** Must Have

Authentication credentials shall be handled securely.

#### Acceptance Criteria

If cookies are used, they should use:

* HttpOnly
* Secure in production
* Appropriate SameSite setting
* Limited expiration

---

### NFR-SEC-07: Sensitive Log Reduction

**Priority:** Should Have

Application logs should avoid unnecessary storage of clinical transcript or note content.

#### Acceptance Criteria

* Full transcripts are not written to standard logs by default.
* Authentication tokens are never logged.
* API keys are never logged.
* Error logs include enough context without exposing sensitive content.

---

## 5.2 Database Requirements

### NFR-DB-01: AWS RDS

**Priority:** Must Have

All required persistent application data shall be stored in AWS RDS PostgreSQL or MySQL.

#### Acceptance Criteria

Persistent data includes:

* Users
* Provider profiles
* Patients
* Encounters
* Drafts
* Clinical notes
* Note versions
* Templates
* ICD-10 codes
* Audit logs

---

### NFR-DB-02: Normalized Schema

**Priority:** Must Have

The database schema shall be normalized and defensible.

#### Acceptance Criteria

* Patients are stored separately from encounters.
* Notes are stored separately from note versions.
* Users are stored separately from role-specific profile data where appropriate.
* Repeated data is minimized.
* Relationships use foreign keys.

---

### NFR-DB-03: Database Migrations

**Priority:** Must Have

Schema changes shall be managed through database migrations.

#### Acceptance Criteria

* Migration files are committed.
* A new environment can create the schema using migrations.
* Manual production-only schema changes are avoided.

---

### NFR-DB-04: Connection Pooling

**Priority:** Must Have

The application shall use database connection pooling.

#### Acceptance Criteria

* The application does not create an unmanaged new connection for every request.
* Pool size is configured.
* Stale connections are detected or recycled.
* Pooling behavior can be explained during the walkthrough.

---

### NFR-DB-05: Indexing

**Priority:** Must Have

Frequently queried columns shall be indexed.

#### Acceptance Criteria

Indexes should support queries involving:

* User email
* Provider identifier
* Patient name and date of birth
* Encounter date
* Encounter status
* Note identifier and version number
* Template identifier

---

### NFR-DB-06: Transactional Note Saving

**Priority:** Must Have

Creating a note version and related audit data shall use a database transaction.

#### Acceptance Criteria

* Partial saves do not leave inconsistent data.
* Failed operations roll back.
* Version numbers remain consistent.
* Duplicate version numbers are prevented.

---

## 5.3 Performance Requirements

### NFR-PERF-01: Progressive Rendering

**Priority:** Must Have

The first generated note content should appear before the entire note is complete.

#### Acceptance Criteria

* The interface begins updating during model generation.
* The user does not see only a spinner followed by a complete note.
* Streaming events are processed incrementally.

---

### NFR-PERF-02: Responsive Dictation

**Priority:** Must Have

Partial dictation text should appear with low perceived delay.

#### Acceptance Criteria

* Audio is streamed in small chunks.
* Partial transcription appears while speaking.
* The UI remains responsive during transcription.

---

### NFR-PERF-03: Debounced SOAP Updates

**Priority:** Should Have

Live SOAP generation should avoid requesting a model update for every partial word.

#### Acceptance Criteria

* Finalized transcript segments are used for note updates.
* Updates are debounced or batched.
* The note does not constantly rewrite itself.
* API cost and unnecessary generation are reduced.

---

### NFR-PERF-04: Pagination

**Priority:** Should Have

Large Provider or Admin encounter lists should support pagination.

#### Acceptance Criteria

* The backend limits the number of rows returned.
* The frontend supports navigating result pages.
* Filtering works with pagination.

---

## 5.4 Reliability Requirements

### NFR-REL-01: Work Preservation

**Priority:** Must Have

Provider work shall not be lost during normal recoverable failures.

#### Acceptance Criteria

Work remains available after:

* Page refresh
* Temporary AI failure
* Temporary network interruption
* Session expiration
* Browser restart after successful auto-save

---

### NFR-REL-02: Session Expiration Recovery

**Priority:** Must Have

If authentication expires during a save, the current note shall remain available.

#### Acceptance Criteria

* The save returns an authentication error.
* Current form content remains in the browser.
* A recovery copy may be stored locally.
* The Provider can authenticate and retry.

---

### NFR-REL-03: AI Timeout Handling

**Priority:** Must Have

External AI calls shall have timeout and error handling.

#### Acceptance Criteria

* Requests do not hang indefinitely.
* Timeout errors are converted into user-friendly messages.
* Partial work remains visible.
* Retry behavior is available where safe.

---

### NFR-REL-04: Application Restart

**Priority:** Must Have

Persistent application data shall survive backend and EC2 application-process restart.

#### Acceptance Criteria

* Saved notes remain available.
* Drafts remain available.
* Templates remain available.
* Users remain available.
* Audit logs remain available.

---

### NFR-REL-05: Health Endpoint

**Priority:** Should Have

The backend should expose a health-check endpoint.

#### Acceptance Criteria

The endpoint reports:

* Application availability
* Database connectivity status where appropriate
* No sensitive credentials

---

## 5.5 Usability Requirements

### NFR-UX-01: Clinical Visual Design

**Priority:** Must Have

The application shall use a clean and professional clinical interface.

#### Acceptance Criteria

* The layout is readable.
* The design avoids distracting decorative elements.
* Important actions are easy to find.
* SOAP sections are visually distinct.
* Dense information remains organized.

---

### NFR-UX-02: Visible System Status

**Priority:** Must Have

The application shall communicate current system activity.

#### Acceptance Criteria

The interface displays relevant states such as:

* Listening
* Paused
* Generating
* Saving
* Saved
* Failed
* Session expired

---

### NFR-UX-03: Actionable Error Messages

**Priority:** Must Have

Errors shall explain what happened and what the user can do.

#### Acceptance Criteria

Avoid messages such as:

```text
Internal Server Error
```

Prefer messages such as:

```text
The note could not be generated. Your transcript is still saved. Please try again.
```

---

### NFR-UX-04: Editable AI Output

**Priority:** Must Have

Generated content shall never be locked from Provider editing.

#### Acceptance Criteria

* All SOAP sections are editable.
* Suggested diagnoses and codes can be changed.
* The Provider approves final content through saving.

---

### NFR-UX-05: Confirmation for Destructive Actions

**Priority:** Should Have

Destructive Admin actions should require confirmation.

#### Acceptance Criteria

Confirmation is requested before:

* Deactivating a Provider
* Deleting or deactivating a template

---

## 5.6 Maintainability Requirements

### NFR-MAINT-01: Layered Backend Design

**Priority:** Should Have

The backend should separate API, service, repository, and database responsibilities.

#### Acceptance Criteria

* API routes do not contain all business logic.
* Database queries are isolated in repository or data-access modules.
* AI logic is isolated in service modules.
* Components are independently testable.

---

### NFR-MAINT-02: Typed Request and Response Models

**Priority:** Must Have

Backend API requests and responses shall use validated schemas.

#### Acceptance Criteria

* Request fields are validated.
* Invalid types return clear errors.
* AI output is validated.
* API documentation reflects request and response shapes.

---

### NFR-MAINT-03: Environment-Based Configuration

**Priority:** Must Have

Environment-specific values shall be configured outside application source code.

#### Acceptance Criteria

Configuration includes:

* Database host and credentials
* Model names
* API keys
* Allowed origins
* Cookie security settings
* Log level

---

### NFR-MAINT-04: Documentation

**Priority:** Must Have

The repository shall include technical documentation.

#### Acceptance Criteria

Documentation includes:

* Project overview
* Requirements
* Architecture
* Database design
* API design
* AI and voice design
* Deployment instructions
* Testing strategy
* Engineering tradeoffs

---

## 5.7 Testing Requirements

### NFR-TEST-01: Unit Tests

**Priority:** Must Have

The backend shall include unit tests for important business logic.

#### Acceptance Criteria

Tests cover:

* Password verification
* Role checks
* Note patch validation
* ICD search behavior
* Insufficient-content handling
* Version-number calculation

---

### NFR-TEST-02: API Integration Tests

**Priority:** Must Have

The application shall include integration tests for major APIs.

#### Acceptance Criteria

Tests cover:

* Login
* Encounter creation
* Provider ownership
* Draft saving
* Note generation with mocked AI
* Note saving
* Version history
* Template updates

---

### NFR-TEST-03: Provider Isolation Tests

**Priority:** Must Have

Tests shall verify that one Provider cannot access another Provider’s data.

#### Acceptance Criteria

Test attempts include:

* Reading another encounter
* Updating another draft
* Saving another note
* Viewing another version history

Each attempt is rejected.

---

### NFR-TEST-04: Voice Test Recordings

**Priority:** Must Have

The repository shall include multiple synthetic voice recordings for representative clinical workflows.

#### Acceptance Criteria

Example recordings cover:

* Orthopedic follow-up
* Respiratory complaint
* Voice addition
* Voice movement between sections
* Voice shortening
* Interruption

---

### NFR-TEST-05: End-to-End Workflow Test

**Priority:** Must Have

At least one end-to-end test shall cover the core Provider workflow.

#### Acceptance Criteria

The test performs:

```text
Login
→ Create patient and encounter
→ Enter transcript
→ Generate note
→ Edit note
→ Save note
→ Reload note
→ Confirm persistence
```

---

### NFR-TEST-06: Non-Happy-Path Tests

**Priority:** Must Have

The test suite shall cover at least two substantive failure scenarios.

#### Acceptance Criteria

At minimum:

* Meaningless transcript handling
* Expired session during save

Additional scenarios may include:

* Deactivated Provider
* AI timeout
* Microphone denial
* Database conflict

---

# 6. Pioneer Feature Requirements

## FR-PIONEER-01: Version Diff

**Priority:** Could Have

The system may show differences between note versions.

---

## FR-PIONEER-02: Clinical Red-Flag Detection

**Priority:** Could Have

The system may flag potentially urgent clinical phrases for Provider review.

This feature must not provide a final diagnosis or replace medical judgment.

---

## FR-PIONEER-03: Provider Writing Style

**Priority:** Could Have

The system may adapt formatting preferences based on previously approved notes.

This feature must not copy unsupported clinical content from previous encounters.

---

# 7. Explicitly Out-of-Scope Requirements

The following are not required for the first implementation:

```text
OUT-01: Production EHR integration
OUT-02: Electronic prescribing
OUT-03: Insurance eligibility verification
OUT-04: Medical billing and claims submission
OUT-05: Patient portal
OUT-06: Native mobile applications
OUT-07: Full HIPAA certification
OUT-08: Real patient identity verification
OUT-09: Full international diagnosis-code support
OUT-10: Medical image processing
OUT-11: Appointment scheduling
OUT-12: Multi-hospital tenant management
```

---

# 8. Requirement Traceability Matrix

This matrix connects major features to requirements and expected tests.

| Feature            | Requirements               | Primary Verification                  |
| ------------------ | -------------------------- | ------------------------------------- |
| Login              | FR-AUTH-01 to FR-AUTH-03   | API and UI test                       |
| Provider isolation | FR-AUTH-04                 | Authorization integration test        |
| Admin access       | FR-AUTH-05                 | Admin API test                        |
| Encounter creation | FR-ENC-01                  | End-to-end test                       |
| Draft persistence  | FR-DRAFT-01 to FR-DRAFT-04 | Refresh and cross-browser test        |
| SOAP generation    | FR-NOTE-01 to FR-NOTE-03   | Streaming integration test            |
| Template behavior  | FR-NOTE-04, FR-TEMP-05     | Admin/provider demo                   |
| Patient history    | FR-PAT-03, FR-NOTE-05      | Returning-patient test                |
| ICD-10 search      | FR-ICD-01 to FR-ICD-04     | Search-ranking test                   |
| Note versioning    | FR-VERS-01 to FR-VERS-04   | Database integration test             |
| Dictation          | FR-DICT-01 to FR-DICT-07   | Voice recording test                  |
| Voice editing      | FR-VOICE-01 to FR-VOICE-07 | Voice command test                    |
| Admin Providers    | FR-ADMIN-01 to FR-ADMIN-03 | Admin workflow test                   |
| Templates          | FR-TEMP-01 to FR-TEMP-05   | CRUD and immediate-update test        |
| Audit logging      | FR-AUDIT-01 to FR-AUDIT-03 | Database verification                 |
| HTTPS and nginx    | NFR-SEC-01, NFR-SEC-02     | Deployment verification               |
| Private RDS        | NFR-SEC-03                 | AWS console verification              |
| Secrets            | NFR-SEC-04, NFR-SEC-05     | Repository and AWS inspection         |
| Connection pooling | NFR-DB-04                  | Code review and runtime configuration |
| Non-happy paths    | FR-INPUT-01, NFR-REL-02    | Walkthrough demonstration             |

---

# 9. Definition of Done

A requirement is considered complete only when:

* The code is implemented.
* The behavior is testable.
* The relevant automated test passes where practical.
* The interface handles success and failure states.
* Required data is persisted correctly.
* Authorization is enforced by the backend.
* The feature is documented.
* The feature can be demonstrated in the final walkthrough.

---

# 10. Minimum Viable Submission

If time becomes limited, the minimum reliable submission must include:

```text
Authentication
Provider and Admin roles
Provider encounter isolation
Patient and encounter creation
Draft persistence in RDS
Streaming SOAP note generation
Manual note editing
ICD-10 suggestion or search
Note saving
Append-only note version history
At least one working voice-edit workflow
At least one working live-dictation workflow
Template management
HTTPS
nginx
Private RDS
Secrets management
Connection pooling
Two substantive non-happy paths
Core automated tests
```

Features marked Could Have should only be implemented after these requirements are stable.
