# SPEC-1.0.0 — Protocol for the Formalization and Instantiation of Software Projects

This document defines the **SPEC-1.0.0** protocol for formalizing a project in the form of a JSON file (“plan”), and then instantiating it via an automation tool.

> **Normative reference:** the French version is the authoritative one.
> An English translation is provided in `SPEC-1.0.0.en.md`.

---

## Scope and relationship to the implementation

### Purpose of this protocol

This document defines the **SPEC-1.0.0** protocol, the purpose of which is to formalize a software project in the form of a structured JSON file (called a "plan").

### Ecosystem

This protocol is part of a coherent kit comprising:
- **SPEC-1.0.0** (this document): definition of the JSON format describing Milestones, Epics, Tasks and their dependencies
- **roadmap.yml** (the Orchestrator): YAML file for a manual GitHub Action orchestrating the materialization of the roadmap
- **materialize_plan.py** (the Skilled and Specialized Worker): Script for materialization into GitHub Issues
- **README.md**: User documentation

### Ultimate goal

The JSON plan resulting from the instantiation of this protocol is intended to be **deployed** (materialized) onto a project management platform (e.g., GitHub Issues) via an **automation tool** (GitHub Action + script).

### What this protocol defines

- ✅ The **structure of the JSON file** (fields, types, hierarchy)
- ✅ The **validity rules** (integrity constraints, semantic consistency)
- ✅ The **naming conventions** and recommended best practices

### What this protocol does NOT define

Implementation details of the materialization process (workflow orchestration, algorithms, API error handling, configuration).

**For these aspects, refer to the README.**

### Reading notes

Mentions of "validation," "script," or "tool" in this document describe the expected behavior of a compliant tool (e.g., "IDs must be unique") such as the one proposed in the kit mentioned above. They do not prescribe the internal implementation.

---

## 1. The "MILESTONE" Individual (The Guardian of Time)

The Milestone is the unit of global synchronization. It produces nothing by itself; it demarcates. It is the ultimate guardian: nothing exists on the map without being attached to it (Guardianship Rule).

### Possible configurations

- **The Active Milestone**: Contains Epics and/or Tasks. It represents a production phase.

- **The Control Milestone (Gate)**: Empty of content. It represents a decision date, a contract end, or an external event.

  **Strict constraint:** A milestone with a "Gate" configuration MUST NOT contain any Epic or any Task (neither directly nor indirectly via Epics attached to it). The presence of content violates the very definition of a Gate and constitutes a data error.

  **Usage examples:**
  - Client review (decision milestone without production)
  - Fixed contractual date (delivery, contract end)
  - External synchronization point (waiting for third-party validation)

### Inventory of characteristics

- **ID (Unique)**: Internal reference for the system (DNA).
- **Title**: Clear name of the phase (e.g., "Public Beta").
- **Start_Delay (Inertia)**: Integer (days). Number of days to wait, from T0 (project start date), before the start of this Milestone. Allows parallelism.
- **Duration (Window)**: Integer (days). Time allocated to complete all internal content.
- **Description**: Strategic note on the objective of the phase (Statement of Intent). (Optional — best practice)
- **Due Date (Calculated)**: `T0 + Start_Delay + Duration`. *(Where T0 is the effective start date, specified at deployment.)*

---

## . The "EPIC" Individual (The Guardian of Meaning)

The Epic is a thematic container. It serves to organize thought and group efforts without its own notion of time. It is an optional sub-container with a flat structure (cannot contain other Epics).

### Possible configurations

- **The Standard Epic**: A set of concrete tasks aimed at a feature.
- **The "Sandbox" Epic (Discovery)**: An envelope for future research, which can be empty or contain exploratory tasks (Monitoring/Research).

### Inventory of characteristics

- **ID (Unique)**: Internal reference.
- **Title**: Functional or thematic name.
- **Description**: The "Why" and scope of this functionality. (Optional — best practice)
- **Label**: Tag allowing filtering of Epics on a dashboard. (Optional)
- **Parent_ID (Milestone_ID)**: Identifier of the Milestone to which it is attached (Mandatory Guardianship link).

---

## 3. The "TASK" Individual (The Atom of Action)

The Task is the only unit that "consumes" effort and that can be "blocked." It carries technical dependencies.

### Possible configurations

- **The Independent Task**: Can be done anytime during its Milestone.
- **The Sequential Task**: Depends on the completion of one or more other tasks.
- **The Orphan Task (Direct)**: Attached to a Milestone without going through an Epic. It has direct temporal guardianship.
- **The Member Task**: Enclosed within an Epic. It has dual guardianship.

### Inventory of characteristics

- **ID (Unique)**: The keystone for dependencies.
- **Title**: Concrete action (action verb recommended).
- **Description**: Technical details, acceptance criteria, and success criteria. *(Optional — best practice)*
- **Estimate (Effort)**: Magnitude (in hours or points) representing the workload.
- **Depends_on**: List of Task IDs that must be completed before (Sequencing).
- **Parent_Link**: The ID of the Milestone (if orphan) or the Epic (if member).
- **Assignee**: *(Optional)* GitHub username of the person assigned to this task.
  - **Type**: String
  - **Format**: Valid GitHub username (alphanumeric and hyphens, no spaces, no `@` prefix)
  - **Valid examples**: `"alice"`, `"john-doe"`, `"dev-team-lead"`
  - **Invalid examples**: `"@alice"`, `"john doe"`, `""`

### Consistency constraints

A task's `configuration` field MUST be consistent with the type of its `parent_link`:

- If `configuration = "Orphan"` → `parent_link` MUST point to a Milestone
- If `configuration = "Member"` → `parent_link` MUST point to an Epic

**Rationale:** These configurations describe the structural nature of the task (direct attachment to time vs. thematic attachment). An inconsistency reveals a misunderstanding of the model and must be corrected.

**Validity rule:** A document violating this constraint is considered invalid (structural error).

---

## 4. The Map of Links (The Nervous System)

Here is how these individuals interact on the A0 map, forming the project's nervous system:

### Connection rules

- **Temporal Flow**: The project unfolds over Milestones (which can overlap).
- **Milestones → Epics Link**: A Milestone can contain 0 to n Epics. An Epic belongs to a single Milestone.
- **Milestones → Tasks Link**: A Milestone can contain 0 to n Tasks directly (Orphan Tasks). Attachment to the Milestone is strictly mandatory.
- **Epics → Tasks Link**: An Epic contains 0 to n Tasks. A Task belongs to a single Epic (or none if orphan).
- **Tasks → Tasks Link (Dependencies)**: A Task can depend on n Tasks. Critical condition: the "parent" tasks should ideally belong to the same Milestone or an earlier Milestone.
- **Temporal Link**: The Milestone "encompasses" the time. All Tasks and Epics contained within it inherit the Milestone's due date.

### Limits of temporal validation

The SPEC-1.0.0 protocol does not define individual start/end dates for tasks. Each task inherits the time range of its milestone (`[T0 + start_delay, T0 + start_delay + duration]`).

**Validation D1 (inter-milestone dependencies):**
The materialization script detects temporal inconsistencies between milestones (a task depending on another whose milestone starts later). However, this validation cannot guarantee the exact execution order down to the day, notably:
- Within the same milestone (all tasks share the same range)
- Between overlapping milestones (parallelism allowed)

**Team Responsibility:**
The team remains responsible for the detailed scheduling of tasks according to the dependencies documented in the GitHub issues (clickable links in the bodies).

**Best Practice:**
Organize your milestones sequentially or ensure that the milestones of dependency tasks start before or simultaneously with the milestones of dependent tasks.

---

## 5. Technical Specification of the Instantiation Object (JSON)

This protocol is not limited to a conceptual definition; it imposes a strict data structure intended for the materialization of the project via an automation script. Any interpreter (human or AI) must produce a file in JSON format respecting the version **SPEC-1.0.0** described below.

### 5.1 Flat structure schema

To ensure optimal management of cross-dependencies (the Nervous System), the structure is "flat." Relationships are not defined by nesting, but by the exclusive use of identifiers (IDs).

#### Instantiation Model (JSON)

> Note: the example below is annotated. **Real JSON** does not support comments.

```jsonc
{
  "metadata": {
    "project_name": "Project Name",
    "protocol_version": "SPEC-1.0.0", /* Must be exactly this string, case-sensitive */
    "description": "Global statement of intent on the project scope.", /* Optional */
    "estimate_unit": "days", /* Mandatory: "days" | "hours" | "story_points" */
    "velocity": 10 /* Required only if estimate_unit = "story_points" (points/day) */
  },
  "milestones": [
    {
      "id": "M-01", /* Must be globally unique; prefix recommended */
      "titre": "Milestone Name",
      "configuration": "Active", /* Allowed values: "Active" or "Gate" */
      "start_delay": 0, /* Positive integer or zero (days) */
      "duration": 14, /* Positive integer or zero (days) */
      "description": "Strategic objective of the milestone." /* Optional - best practice */
    }
  ],
  "epics": [
    {
      "id": "E-01", /* Must be globally unique; prefix recommended */
      "parent_id": "M-01", /* Must reference an existing milestone */
      "titre": "Epic Name",
      "configuration": "Standard", /* Allowed values: "Standard" or "Discovery" */
      "label": "GitHub_Tag", /* Optional */
      "description": "The Why and functional scope." /* Optional - best practice */
    }
  ],
  "tasks": [
    {
      "id": "T-01", /* Must be globally unique; prefix recommended */
      "parent_link": "E-01", /* Must reference an existing milestone or epic */
      "titre": "Action to perform",
      "configuration": "Sequential", /* Allowed values: "Independent", "Sequential", "Orphan", "Member" */
      "estimate": 4, /* Positive number or zero (hours/points) */
      "depends_on": ["T-00"], /* List of existing task IDs; empty if independent */
      "description": "Success criteria and technical details.", /* Optional - best practice */
      "assignee": "GitHub_Username" /* Optional */
    }
  ]
}
```

### 5.2 Formalization constraints

- **Temporal Agnosticism**: The JSON must not contain any absolute dates. The execution script will calculate deadlines from a T0 point (current date by default, or a date explicitly provided at deployment) by applying the `start_delay` and `duration` variables.

- **T0 Timezone**: All dates are interpreted in UTC (Coordinated Universal Time). The script compares T0 to the current date in UTC to validate that there is no back-planning. This convention ensures consistent behavior regardless of the team members' geographical location.

- **Guardianship Rule**:
  - Any Epic must have a valid `parent_id` pointing to an existing Milestone.
  - Any Task must have a `parent_link` pointing either to an existing Epic (Member Configuration) or to an existing Milestone (Orphan Configuration).

- **Sequencing**: The `depends_on` field is a list of strings (Array). If a task is "Independent", the list must be empty `[]`.

- **ID Codification**: It is recommended to use explicit prefixes (`M-`, `E-`, `T-`) followed by a numerical index to facilitate human reading and debugging of the nervous system. Non-compliance with this convention is not a blocking error if global uniqueness is ensured.

- **Optional fields**: The `description` fields (for all objects), `label` (for Epic), and `assignee` (for Task) are optional. They can be omitted or set to `null`.

### 5.3 Semantics of validations

Non-conformities must be categorized as follows:

- **Blocking error**: violation of a critical structural or referential rule (e.g., missing mandatory field, incorrect type, non-existent reference, duplicate ID). A single blocking error invalidates the JSON.

- **Warning**: violation of a recommendation or non-critical semantic inconsistency (e.g., ID prefix not respected, missing description, "Gate" milestone with content, dependency on a later milestone).

- **Handling missing description**: a warning should be issued to encourage documentation ("Consider adding a description to improve project clarity"), but this does not invalidate the JSON.

The script must collect all anomalies and produce a report in English specifying for each:

- Category (`error`/`warning`)
- Location (JSON path)
- Clear description
- Correction suggestion if possible

It will then return a boolean status (`True` if valid, `False` otherwise) after displaying the report.

---

## 6. Glossary and definitions

Resolving a task's milestone
Each task belongs to a milestone, which defines its time window for completion.

**Resolution rule:**
The milestone to which a task belongs is determined by its `parent_link` field:

- If `parent_link` points to a **Milestone** → the task belongs directly to that Milestone
Example: *Task `T-01` with `parent_link: "M-01"` → belongs to Milestone M-01*

- If `parent_link` points to an **Epic** → the task belongs to the Milestone of the Epic
*Resolution: `task_milestone = epic[parent_link].parent_id`*
*Example: Task `T-02` with `parent_link: "E-05"`, and Epic `E-05` with `parent_id: "M-02"` → belongs to Milestone `M-02`*

**Technical notation** (used in validation rules):
We call the result of this resolution the **"effective milestone"**. This is not a new type of milestone, but simply the milestone to which the task *ultimately* belongs after resolving the parent link.