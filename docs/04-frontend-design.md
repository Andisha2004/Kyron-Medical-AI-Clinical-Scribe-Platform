# Frontend Design

## Technology Stack

* Next.js
* React
* TypeScript
* Tailwind CSS

---

# Application Structure

```text
/login

/provider
├── Dashboard
├── New Encounter
├── Encounter Workspace
└── Encounter History

/admin
├── Dashboard
├── Encounters
├── Providers
└── Templates
```

---

# Pages

## Login

Purpose:

* Authenticate users
* Redirect users based on role

Components:

* Email
* Password
* Sign In button

---

## Provider Dashboard

Purpose:

* View encounters
* Resume drafts
* Create new encounter

Components:

* New Encounter button
* Draft encounters
* Completed encounters

---

## Encounter Workspace

Purpose:

Main workspace where Providers create and edit clinical notes.

Sections:

* Patient Information
* Transcript
* Clinical Observations
* SOAP Note Editor
* ICD-10 Search
* Voice Controls
* Version History
* Save Button

---

## Admin Dashboard

Purpose:

Administrative overview of the platform.

Sections:

* Encounters
* Providers
* Templates

---

## Provider Management

Features:

* View Providers
* Add Provider
* Deactivate Provider

---

## Template Management

Features:

* View Templates
* Create Template
* Edit Template
* Delete Template

---

# Layout

```text
+------------------------------------------------------+
| Header                                               |
+------------------------------------------------------+
| Sidebar | Main Content                               |
|         |                                            |
|         |                                            |
|         |                                            |
+------------------------------------------------------+
```

---

# Encounter Workspace Layout

```text
+---------------------------------------------------------------+
| Patient Information                                           |
+----------------------------+----------------------------------+
| Transcript                 | SOAP Note                        |
|                            |                                  |
| Clinical Observations      | Subjective                       |
|                            | Objective                        |
| Dictation Controls         | Assessment                       |
|                            | Plan                             |
+----------------------------+----------------------------------+
| ICD-10 Search | Version History | Save Note                   |
+---------------------------------------------------------------+
```

---

# Navigation Flow

```text
Login
    ↓
Dashboard
    ↓
Encounter Workspace
    ↓
Generate Note
    ↓
Review & Edit
    ↓
Save
```

---

# Design Principles

* Clean and professional
* Minimal visual distractions
* Easy to navigate
* Responsive layout
* Fast interactions
* Clinical-focused interface
* Clear status indicators (Generating, Saving, Saved)

---

# Reusable Components

* Header
* Sidebar
* Button
* Card
* Table
* Modal
* Input
* TextArea
* Dropdown
* Loading Indicator
* Toast Notification

---

# Future Improvements

* Dark mode
* Keyboard shortcuts
* Split-screen resizing
* Accessibility improvements
* Mobile responsiveness
