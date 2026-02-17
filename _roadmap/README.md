# Roadmap Bootstrap (SPEC-1.0.0) → GitHub Milestones & Issues

This repository contains a **one-shot bootstrap tool** that materializes a project roadmap written in **SPEC-1.0.0** ([FR](SPEC-1.0.0.fr.md) | [EN](SPEC-1.0.0.en.md)) JSON into a GitHub “Jira-like” setup using:

- **GitHub Milestones** (protocol Milestones)
- **GitHub Issues** for:
  - **Epics** (issues labeled `rm:epic`)
  - **Tasks** (issues labeled `rm:task`)
- Clickable dependency links (e.g. `Depends on #123`)

---

## Scope

This tool is intended to **bootstrap** a brand new project on GitHub from a validated roadmap plan.

---

## Limitations (by design)

- **One-shot only**: the workflow is designed to run on a **pristine repository**.
- No synchronization or update of existing Issues/Milestones.
- No automatic schedule drift handling (if the plan slips, adjust on GitHub manually).
- If a run fails mid-deployment, you may end up with a partial state and must clean up manually (see “Recovery / Cleanup”).

---

## Specification (Protocol)

This tool expects a roadmap JSON compliant with **SPEC-1.0.0**:

- **Normative reference (FR):** [SPEC-1.0.0.fr.md](SPEC-1.0.0.fr.md)
- **English translation (EN):** [SPEC-1.0.0.en.md](SPEC-1.0.0.en.md)

The French version is the source of truth. The English version is provided for convenience.

---

## Files and locations

- Roadmap plan (input):  
  `/_roadmap/roadmap_plan.json`

- Materializer script:  
  `/_roadmap/materialize_plan.py`

- GitHub Action workflow (orchestrator):  
  `/.github/workflows/roadmap.yml`

- Python dependencies (isolated from the project root):  
  `/_roadmap/requirements.txt`

---

## Pristine repository requirement

The workflow will not run unless the repository is pristine.

**Pristine means:**
- **0 GitHub Issues** (open or closed)
- **0 GitHub Milestones** (open or closed)

If existing Issues and/or Milestones are detected, the workflow is **skipped on purpose** (safe behavior) and prints a recovery guide.

---

## Quick start (GitHub-first)

### 1) Copy the starter kit into your repo
Copy these paths into your target repository and commit them:
- `/.github/workflows/roadmap.yml`
- `/_roadmap/` (folder)

### 2) Write your plan
Edit:
- `/_roadmap/roadmap_plan.json`

Ensure it follows **SPEC-1.0.0** and that `metadata.version_protocole` is exactly:
- `SPEC-1.0.0`

### 3) Run the workflow
1) Go to the **Actions** tab  
2) Select **Apply Project Roadmap**  
3) Click **Run workflow**  
4) (Optional) provide inputs (see next section)

---

## Workflow inputs

### `t0` (optional)
- Format: **YYYY-MM-DD** (ISO)
- If omitted: **T0 defaults to the workflow run date**.
- The workflow always prints the final T0 used (logs + Step Summary).

### `force_apply` (boolean)
Meaning:
- If the preflight report contains **any warning**, the workflow **fails** by default.
- With `force_apply=true`, the workflow may apply the plan **despite warnings**.
- **Errors always abort**, regardless of `force_apply`.

Decision rules:
- Preflight = **0 errors, 0 warnings** → APPLY (force_apply ignored)
- Preflight = **errors ≥ 1** → FAIL (force_apply ignored)
- Preflight = **warnings ≥ 1 and errors = 0**:
  - `force_apply=false` → FAIL
  - `force_apply=true` → APPLY

---

## What gets created on GitHub

### Milestones
- One GitHub Milestone per protocol milestone
- Due dates computed using:
  - `Due date = T0 + Start_Delay + Duration`

### Labels (tool-owned)
This tool creates and uses labels prefixed with **`rm:`** to avoid collisions:
- `rm:epic`
- `rm:task`
- `rm:<epic.label>` when `epic.label` is provided

#### Label policy (type + theme)
This tool uses two type labels and optional theme labels:
- **Type labels (always present):**
  - Epics: `rm:epic`
  - Tasks: `rm:task`

- **Theme labels (from `epic.label`):**
  - When an Epic defines `label`, the tool creates/uses a theme label: `rm:<theme>`.
  - This theme label is applied to the Epic **and inherited by all member Tasks** (tasks whose `parent_link` points to that Epic).

- **Orphan Tasks (direct milestone attachment):**
  - Tasks whose `parent_link` points directly to a Milestone receive: `rm:direct`.
  - `rm:direct` uses a fixed neutral (grey) color.

Notes:
- Theme label colors are generated deterministically to stay stable across runs.
- Dependency links do not affect labels.

### Epics
- Each Epic becomes a **GitHub Issue** labeled `rm:epic` (+ optional theme label `rm:<label>`)
- Each Epic is assigned to its GitHub Milestone (native GitHub field)

### Tasks
- Each Task becomes a **GitHub Issue** labeled `rm:task`
- If the parent is an Epic and the Epic has a label, the Task inherits the Epic theme label `rm:<label>`.
- Tasks are created in **topological order** to ensure dependencies are linkable at creation time.

### Dependencies (clickable)
- In Task bodies, the tool writes:  
  `Depends on #NNN, #MMM`  
  GitHub turns `#NNN` into clickable links automatically.

---

## GitHub encoding conventions

GitHub does not provide native “Epic” objects. This tool uses the following convention:

- **Milestone (protocol)** → **GitHub Milestone**
- **Epic (protocol)** → **GitHub Issue** labeled `rm:epic`
- **Task (protocol)** → **GitHub Issue** labeled `rm:task`

### Assignees
- The protocol defines `assignee` for **Tasks** (optional).
- If present in the JSON, it is applied to the **native GitHub Issue assignees field**.
- Assignees are **never duplicated** in the issue body.
- Epics ignore assignees (protocol does not define them for Epics).

---

## Official templates (exact output)

### Milestone description
```markdown
**Protocol-ID:** M-XX
**Kind:** Milestone
**Configuration:** Actif|Gate
**Start_Delay:** <N> days (from T0)
**Duration:** <N> days
**T0:** YYYY-MM-DD
**Due date (computed):** YYYY-MM-DD

---

<description from JSON (if provided)>
```

### Epic issue body
```markdown
**Protocol-ID:** E-XX
**Kind:** Epic
**Configuration:** Standard|Discovery
**Milestone-ID:** M-XX

---

<description from JSON (if provided)>
```

### Task issue body
```markdown
**Protocol-ID:** T-XX
**Kind:** Task
**Configuration:** Indépendante|Sequentielle|Orpheline|Membre
**Estimate:** <value>
**Parent-Link:** M-XX|E-XX
**Epic-ID:** E-XX
**Epic:** #NNN

---

<description from JSON (if provided)>

### Dependencies
Depends on #NNN, #MMM
```

Template rules:
- `Epic-ID` and `Epic: #NNN` appear **only** when the task parent is an Epic.
- `### Dependencies` appears **only** when `depends_on` is non-empty.

---

## Create a Jira-like board (GitHub Project)

### Objective
Get a **Backlog / In progress / Done** board to manage the issues created by the tool.

### Steps (GitHub UI)
1) Open your repository and go to the **Projects** tab.  
2) Click **New project**.  
3) Choose the **Board** template (Kanban).  
4) Name the project (e.g. `Roadmap` or `Delivery`).

### Add issues (in bulk)
5) In the Project, use **Add item** (or “Add items”) and filter with:
   - To add all tasks: `label:rm:task`
   - To also add epics: `label:rm:epic`
   - (Optional) to target a theme: `label:rm:backend` (example)

6) Select the suggested items (you can add many at once) and confirm.

### Columns / Workflow
7) Ensure the **Status** field exists (default on a Board).  
8) Use the default columns:
   - **Backlog**
   - **In progress**
   - **Done**

You can now manage your project “like Jira” by moving cards across columns.

---

## Recovery / Cleanup

This section applies if the workflow is skipped by the safety gate (repo not pristine) or if a run failed mid-deployment.

### If the workflow is skipped (repo not pristine)
To run the bootstrap, you must return to:
- **0 Issues**
- **0 Milestones**

### If the workflow failed mid-deployment (partial state)
The tool does not attempt automatic rollback. Use manual cleanup.

#### Minimum cleanup (required to re-run safely)
1) Delete all created **GitHub Issues** (Epics and Tasks).  
2) Delete all created **GitHub Milestones**.

#### Optional cleanup (for a perfectly clean repo)
3) Delete all labels starting with `rm:`.

Then re-run the workflow.

---

## Customization

- The plan path is configured in the workflow via environment variables (single place to edit).
- Label prefix is fixed to `rm:` (by design).