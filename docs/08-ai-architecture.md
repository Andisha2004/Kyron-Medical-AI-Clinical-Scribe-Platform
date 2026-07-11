# AI Architecture

## Overview

The AI layer is responsible for transforming raw clinical information into structured, editable clinical documentation.

The system separates AI functionality into three independent services:

* SOAP Note Generation
* Live Voice Dictation
* Conversational Voice Editing

Keeping these services independent makes the application easier to maintain and allows individual models to be replaced without affecting the rest of the system.

---

# AI Architecture

```text
                    Clinical Information
                            │
            ┌───────────────┴───────────────┐
            │                               │
      Patient History                Note Template
            │                               │
            └───────────────┬───────────────┘
                            │
                     Prompt Builder
                            │
                    SOAP Generation
                            │
                    Structured SOAP
                            │
                     Editable Note
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
   Voice Editing                     Manual Editing
```

---

# SOAP Note Generation

Inputs:

* Transcript
* Clinical observations
* Patient history
* Selected template

Output:

* Subjective
* Objective
* Assessment
* Plan
* Suggested ICD-10 code(s)

The backend builds the prompt and sends it to the text-generation model.

---

# Live Voice Dictation

Workflow:

```text
Microphone
      ↓
Speech-to-Text
      ↓
Live Transcript
      ↓
Encounter Draft
```

The transcript updates continuously while the provider is speaking.

---

# Conversational Voice Editing

Instead of generating a completely new note, the AI modifies only the requested section.

Example commands:

* Add that the patient has no fever.
* Move the knee pain into Subjective.
* Shorten the Plan.

The updated note is immediately shown in the workspace.

---

# Prompt Pipeline

```text
Patient History
        +
Template Instructions
        +
Transcript
        +
Clinical Observations
        ↓
Prompt Builder
        ↓
AI Model
        ↓
SOAP Note
```

The frontend never constructs prompts.

Prompt construction is handled entirely by the backend.

---

# AI Design Principles

* Providers always review AI output.
* AI suggestions remain editable.
* AI should not invent unsupported clinical information.
* Previous note versions are preserved.
* Voice editing should make minimal changes.
* Patient history should provide context, not overwrite current information.

---

# Future Improvements

Potential future enhancements include:

* Provider-specific writing style
* Better retrieval for patient history
* Medical terminology normalization
* Confidence scoring
* Multi-model routing
* Automatic quality evaluation
