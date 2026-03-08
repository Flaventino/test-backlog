# SPEC-1.0.0 — Protocol for Formalizing and Instantiating Software Projects

This document defines **SPEC-1.0.0**, a protocol to formalize a project as a JSON “plan” and instantiate it using an automation tool.

> **Normative reference:** the French version is the source of truth.  
> This English version is provided for convenience.

---

## 1. The "MILESTONE" Entity (The Time Guardian)

A Milestone is the global synchronization unit. It does not produce deliverables by itself; it defines boundaries. It is the ultimate support: nothing exists on the map without being attached to it (Tutorship Rule).

### Allowed configurations
- **Active Milestone**: Contains Epics and/or Tasks. It represents a production phase.
- **Gate Milestone**: Empty of content. It represents a decision date, contract end, or external event.

### Attribute inventory
- **ID (Unique)**: Internal reference for the system (DNA).
- **Title**: Clear phase name (e.g. “Public Beta”).
- **Start_Delay (Inertia)**: Integer (days). Number of waiting days since T0 (project start date) before starting this Milestone. Allows parallelism.
- **Duration (Window)**: Integer (days). Time allocated to perform all internal content.
- **Description**: Strategic note about the phase goal (intent note). *(Optional — best practice)*
- **Due date (Computed)**: `T0 + Start_Delay + Duration`. *(Where T0 is the effective launch date, specified at deployment time.)*

---

## 2. The "EPIC" Entity (The Meaning Guardian)

An Epic is a thematic container. It organizes thinking and groups efforts without having its own notion of time. It is an optional flat sub-container (cannot contain other Epics).

### Allowed configurations
- **Standard Epic**: A set of concrete tasks targeting a feature.
- **Discovery Epic (Sandbox)**: An envelope for future research, possibly empty or containing exploratory tasks.

### Attribute inventory
- **ID (Unique)**: Internal reference.
- **Title**: Functional or thematic name.
- **Description**: The “Why” and the functional scope. *(Optional — best practice)*
- **Label**: Tag used to filter Epics on a dashboard. *(Optional)*
- **Parent_ID (Milestone_ID)**: Identifier of the Milestone it belongs to (mandatory tutorship link).

---

## 3. The "TASK" Entity (The Atom of Action)

A Task is the only unit that consumes effort and can be blocked. It carries technical dependencies.

### Allowed configurations
- **Independent Task**: Can be done anytime within its Milestone.
- **Sequential Task**: Depends on completion of one or more other tasks.
- **Orphan Task (Direct)**: Attached directly to a Milestone without an Epic. It has direct time tutorship.
- **Member Task**: Contained inside an Epic. It has double tutorship.

### Attribute inventory
- **ID (Unique)**: Keystone for dependencies.
- **Title**: Concrete action (action verb recommended).
- **Description**: Technical details, acceptance and success criteria. *(Optional — best practice)*
- **Estimate (Effort)**: Magnitude (hours or points) representing workload.
- **Depends_on**: List of task IDs that must be completed before (sequencing).
- **Parent_Link**: The Milestone ID (if orphan) or the Epic ID (if member).
- **Assignee**: *(Optional)* Who performs the action.

---

## 4. Link Map (The Nervous System)

This section describes how entities interact on the project map.

### Connection rules
- **Time flow**: The project progresses across Milestones (which may overlap).
- **Milestones → Epics**: A Milestone may contain 0..n Epics. An Epic belongs to exactly one Milestone.
- **Milestones → Tasks**: A Milestone may contain 0..n direct Tasks (Orphan tasks). Attachment to a Milestone is mandatory.
- **Epics → Tasks**: An Epic contains 0..n Tasks. A Task belongs to exactly one Epic (or none if orphan).
- **Tasks → Tasks (Dependencies)**: A Task may depend on n Tasks. Critical condition: parent tasks should ideally belong to the same Milestone or an earlier Milestone.
- **Time tutorship**: The Milestone “envelops” time. All contained Tasks and Epics inherit the Milestone due date.

---

## 5. Technical Specification of the Instantiation Object (JSON)

This protocol is not only conceptual: it enforces a strict data structure meant to materialize the project via an automation script. Any interpreter (human or AI) must produce a JSON file compliant with **SPEC-1.0.0**.

### 5.1 Flat structure schema

To ensure optimal management of cross-dependencies (the Nervous System), the structure is flat. Relationships are not defined via nesting, but exclusively via identifiers (ID).

#### INSTANTIATION MODEL (JSON)

> Note: the example below is annotated. Real JSON does not support comments.

```jsonc
{
  "metadata": {
    "projet_nom": "Project Name",
    "version_protocole": "SPEC-1.0.0",
    "description": "Global intent note about the project scope."
  },
  "milestones": [
    {
      "id": "M-01",
      "titre": "Milestone Name",
      "configuration": "Actif",
      "start_delay": 0,
      "duration": 14,
      "description": "Strategic objective of the milestone."
    }
  ],
  "epics": [
    {
      "id": "E-01",
      "parent_id": "M-01",
      "titre": "Epic Name",
      "configuration": "Standard",
      "label": "GitHub_Tag",
      "description": "The why and the functional scope."
    }
  ],
  "tasks": [
    {
      "id": "T-01",
      "parent_link": "E-01",
      "titre": "Action to perform",
      "configuration": "Sequentielle",
      "estimate": 4,
      "depends_on": ["T-00"],
      "description": "Success criteria and technical details.",
      "assignee": "GitHub_Username"
    }
  ]
}
```

### 5.2 Formalization constraints

- **Temporal agnosticism**: The JSON must not contain any absolute date. The execution script computes due dates from a pivot point **T0** *(today by default, or a date explicitly provided at deployment time)* using `start_delay` and `duration`.
- **Tutorship rule**:
  - Every Epic must have a valid `parent_id` referencing an existing Milestone.
  - Every Task must have a `parent_link` referencing either an existing Epic (Member configuration) or an existing Milestone (Orphan configuration).
- **Sequencing**: The `depends_on` field is an array of strings. If a task is “Indépendante”, the list must be empty `[]`.
- **ID convention**: Prefixes (M-, E-, T-) followed by a numeric index are recommended for readability and debugging. Not following this convention is not a blocking error if global uniqueness is ensured.
- **Optional fields**: `description` (all objects), `label` (Epic), and `assignee` (Task) are optional. They may be omitted or set to `null`.

### 5.3 Validation semantics

Non-compliances must be categorized as follows:
- **Blocking error**: violation of a critical structural or referential rule (e.g. missing required field, wrong type, invalid reference, duplicate ID). A single blocking error invalidates the JSON.
- **Warning**: violation of a recommendation or non-critical semantic inconsistency (e.g. ID prefix not respected, missing description, Gate milestone with content, dependency pointing to a later milestone).

**Handling missing descriptions:** a warning should be emitted to encourage documentation (“Consider adding a description to improve project clarity”), but this must not invalidate the JSON.

The script must collect all anomalies and produce an English report for each:
- Category (error/warning)
- Location (JSON path)
- Clear description
- Correction suggestion when possible

It must then return a boolean status (`True` if valid, `False` otherwise) after printing the report.