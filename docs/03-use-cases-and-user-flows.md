# Use Cases and User Flows

## 1. User Roles

The system has two roles:

* **Provider**
* **Admin**

---

# 2. Provider Use Cases

## UC-P01: Log In

**Actor:** Provider

**Flow:**

```text
Open login page
→ Enter email and password
→ Backend verifies credentials
→ Redirect to Provider Dashboard
```

**Failure cases:**

* Invalid credentials
* Deactivated account
* Expired session

---

## UC-P02: Create a New Encounter

**Actor:** Provider

**Flow:**

```text
Provider Dashboard
→ Click New Encounter
→ Enter patient first name, last name, and date of birth
→ Select note template
→ Create encounter
→ Open Encounter Workspace
```

The backend reuses an existing matching patient or creates a new patient.

---

## UC-P03: Enter Clinical Information

**Actor:** Provider

The Provider can:

* Paste a transcript
* Type clinical observations
* Use live dictation

The system automatically saves the draft.

---

## UC-P04: Generate SOAP Note

**Actor:** Provider

**Flow:**

```text
Enter clinical information
→ Click Generate Note
→ Backend retrieves template
→ Backend retrieves relevant patient history
→ AI generates SOAP note
→ Note streams into the workspace
```

The generated note includes:

* Subjective
* Objective
* Assessment
* Plan
* Suggested ICD-10 code

---

## UC-P05: Edit SOAP Note

**Actor:** Provider

The Provider can:

* Edit each SOAP section manually
* Add or remove ICD-10 codes
* Use voice commands to modify the note

Example voice commands:

```text
“Add that the patient has no fever.”

“Move the knee pain into Subjective.”

“Shorten the Plan.”
```

---

## UC-P06: Use Live Dictation

**Actor:** Provider

**Flow:**

```text
Click Start Dictation
→ Allow microphone access
→ Speak clinical information
→ View partial transcript
→ View SOAP note update
→ Pause, resume, or stop
```

Final transcript segments are added to the encounter draft.

---

## UC-P07: Search ICD-10 Codes

**Actor:** Provider

**Flow:**

```text
Enter plain-English condition
→ View ranked ICD-10 results
→ Select a result
→ Add code to Assessment
```

Example:

```text
Search: right knee arthritis

Result:
M17.11 — Unilateral primary osteoarthritis, right knee
```

---

## UC-P08: Save Note

**Actor:** Provider

**Flow:**

```text
Review note
→ Click Save
→ Backend validates access
→ Create new note version
→ Write audit event
→ Show save confirmation
```

Previous note versions are never overwritten.

---

## UC-P09: View Version History

**Actor:** Provider

The Provider can view:

* Version number
* Saved-by user
* Save date and time
* Previous note content

The Provider may also compare versions if the diff feature is implemented.

---

## UC-P10: Resume Draft

**Actor:** Provider

**Flow:**

```text
Log in
→ Open draft encounter
→ Backend loads draft from RDS
→ Transcript and SOAP note are restored
→ Continue working
```

This should work after refresh or from another browser.

---

# 3. Admin Use Cases

## UC-A01: Log In

**Actor:** Admin

**Flow:**

```text
Open login page
→ Enter credentials
→ Backend verifies Admin role
→ Redirect to Admin Dashboard
```

---

## UC-A02: View All Encounters

**Actor:** Admin

The Admin can:

* View encounters across all Providers
* Filter by Provider
* Filter by date range
* Open encounter details

---

## UC-A03: Add Provider

**Actor:** Admin

**Flow:**

```text
Open Providers page
→ Click Add Provider
→ Enter provider information
→ Create account
→ Provider appears in roster
```

---

## UC-A04: Deactivate Provider

**Actor:** Admin

**Flow:**

```text
Open Providers page
→ Select Provider
→ Click Deactivate
→ Confirm action
→ Provider account becomes inactive
```

Historical encounters remain unchanged.

---

## UC-A05: Manage Templates

**Actor:** Admin

The Admin can:

* Create templates
* Edit templates
* Delete or deactivate templates

Example templates:

* Orthopedic Follow-Up
* New Patient Evaluation
* Urgent Care Visit

---

## UC-A06: Update Active Template

**Actor:** Admin

**Flow:**

```text
Open Templates page
→ Edit template instructions
→ Save changes
→ Updated template stored in RDS
→ Provider’s next generation uses new instructions
```

The Provider does not need to refresh the page.

---

# 4. Main Provider User Flow

```text
Login
  ↓
Provider Dashboard
  ↓
Create or Resume Encounter
  ↓
Enter Transcript or Start Dictation
  ↓
Generate SOAP Note
  ↓
Review and Edit
  ↓
Search or Add ICD-10 Code
  ↓
Save Note
  ↓
View Version History
```

---

# 5. Returning Patient Flow

```text
Create Encounter
  ↓
Match Patient by Name and DOB
  ↓
Backend Finds Previous Encounters
  ↓
Relevant History Retrieved
  ↓
History Added to AI Context
  ↓
SOAP Note Reflects Relevant Prior Information
```

---

# 6. Admin User Flow

```text
Admin Login
  ↓
Admin Dashboard
  ├── View Encounters
  ├── Manage Providers
  └── Manage Templates
```

---

# 7. Important Failure Flows

## Insufficient Clinical Content

```text
Provider clicks Generate
→ Backend detects insufficient information
→ No SOAP note is generated
→ Provider sees guidance message
→ Existing draft remains saved
```

## Session Expires During Save

```text
Provider clicks Save
→ Backend returns authentication error
→ Current note remains visible
→ Provider signs in again
→ Save request is retried
```

## Provider Is Deactivated

```text
Admin deactivates Provider
→ Provider sends next protected request
→ Backend blocks request
→ Draft is preserved
→ Provider sees account-status message
```

## AI Service Fails

```text
Generation request fails
→ Existing transcript and note remain visible
→ Error message is shown
→ Provider can retry
```

---

# 8. Use Case Summary

| ID     | Use Case                   | Actor    |
| ------ | -------------------------- | -------- |
| UC-P01 | Log in                     | Provider |
| UC-P02 | Create encounter           | Provider |
| UC-P03 | Enter clinical information | Provider |
| UC-P04 | Generate SOAP note         | Provider |
| UC-P05 | Edit SOAP note             | Provider |
| UC-P06 | Use live dictation         | Provider |
| UC-P07 | Search ICD-10 codes        | Provider |
| UC-P08 | Save note                  | Provider |
| UC-P09 | View version history       | Provider |
| UC-P10 | Resume draft               | Provider |
| UC-A01 | Log in                     | Admin    |
| UC-A02 | View all encounters        | Admin    |
| UC-A03 | Add Provider               | Admin    |
| UC-A04 | Deactivate Provider        | Admin    |
| UC-A05 | Manage templates           | Admin    |
| UC-A06 | Update active template     | Admin    |
