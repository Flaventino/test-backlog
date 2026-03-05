#!/usr/bin/env python3
# ///   A B S T R A C T   ///
"""
GitHub Project Materializer (SPEC-1.0.0) — Topological Deployment Script

Instantiates milestones, epics, and tasks on GitHub from a validated JSON plan,
while respecting task dependencies using a topological sort (Kahn's algorithm).

Dependencies (Python 3.11+ recommended):
    pip install "pydantic>=2.0" PyGithub rich

Environment:
    export GITHUB_TOKEN="ghp_..."   # required (or pass --token)

Usage:
    python deploy_github_project.py path/to/project.json --repo OWNER/REPO
    python deploy_github_project.py plan.json --repo OWNER/REPO --t0 2026-02-07

Notes:
- This script creates:
  * GitHub Milestones for protocol milestones.
  * GitHub Issues for epics (labeled "epic" + optional epic label).
  * GitHub Issues for tasks (labeled "task" + epic label if applicable).
- Task issues are created in topological order so dependency links can be injected
  at creation time ("Depends on #12, #15").
- Protocol "ID" values are recorded in issue bodies as "Protocol-ID: <ID>".
"""


# ///   I M P O R T S   ///
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict, deque
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from github import Github
from github.GithubException import GithubException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    ValidationError,
    model_validator,
)
from rich.console import Console
from rich.table import Table

# DRY imports from the reference module (strictly identical structures)
from validator import (  # type: ignore
    IssueType,
    Severity,
    ValidationIssue,
    ValidationReport,
    _read_json_file,
)


# ///   G L O B A L S   &   C O N S T A N T S   ///
CONSOLE = Console()


# ///   C L A S S E S   ///

# === DATA MODELS (B-SPECIFIC; MUST NOT BE REPLACED BY validator MODELS) ===
class Metadata(BaseModel):
    """Pydantic model for project metadata."""

    model_config = ConfigDict(extra="forbid", strict=True)

    projet_nom: str
    version_protocole: str  # constrained below by Literal-like check
    description: str | None = None

    @model_validator(mode="after")
    def _check_protocol_version(self) -> "Metadata":
        if self.version_protocole != "SPEC-1.0.0":
            raise ValueError("version_protocole must be exactly 'SPEC-1.0.0'.")
        return self


class Milestone(BaseModel):
    """Pydantic model for milestones."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    titre: str
    configuration: str
    start_delay: StrictInt = Field(ge=0)
    duration: StrictInt = Field(ge=0)
    description: str | None = None

    @model_validator(mode="after")
    def _check_configuration(self) -> "Milestone":
        if self.configuration not in {"Actif", "Gate"}:
            raise ValueError("Milestone.configuration must be 'Actif' or 'Gate'.")
        return self


class Epic(BaseModel):
    """Pydantic model for epics."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    parent_id: str
    titre: str
    configuration: str
    label: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _check_configuration(self) -> "Epic":
        if self.configuration not in {"Standard", "Discovery"}:
            raise ValueError("Epic.configuration must be 'Standard' or 'Discovery'.")
        return self


class Task(BaseModel):
    """Pydantic model for tasks."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    parent_link: str
    titre: str
    configuration: str
    estimate: StrictInt | StrictFloat = Field(ge=0)
    depends_on: list[str]
    description: str | None = None
    assignee: str | None = None

    @model_validator(mode="after")
    def _check_task_is_really_independent(self) -> "Task":
        """Protocol rule: Independent tasks must have an empty depends_on."""
        if self.configuration == "Indépendante" and self.depends_on:
            txt = "For configuration 'Indépendante', 'depends_on' must empty."
            raise ValueError(txt)
        return self

    @model_validator(mode="after")
    def _check_configuration(self) -> "Task":
        allowed = {"Indépendante", "Sequentielle", "Orpheline", "Membre"}
        if self.configuration not in allowed:
            raise ValueError(
                "Task.configuration must be one of: "
                "'Indépendante', 'Sequentielle', 'Orpheline', 'Membre'."
            )
        return self


class Project(BaseModel):
    """Root Pydantic model for the protocol JSON document."""

    model_config = ConfigDict(extra="forbid", strict=True)

    metadata: Metadata
    milestones: list[Milestone]
    epics: list[Epic]
    tasks: list[Task]


# ///   F U N C T I O N S   ///

# === REPORTING (STRICTLY IMMUTABLE) ===
def print_validation_report(report: ValidationReport) -> None:
    """Print a validation report in a readable table.

    Args:
        report: The validation report to print.
    """
    if not report.issues:
        CONSOLE.print("[green]No validation issues found.[/green]")
        return

    table = Table(title="Validation Report", show_lines=True)
    table.add_column("Severity", style="bold")
    table.add_column("Type")
    table.add_column("Location")
    table.add_column("Message")
    table.add_column("Suggestion")

    for issue in report.issues:
        sev_style = "red" if issue.severity == Severity.ERROR else "yellow"
        table.add_row(
            f"[{sev_style}]{issue.severity.value}[/{sev_style}]",
            issue.issue_type.value,
            issue.location,
            issue.message,
            issue.suggestion or "",
        )

    CONSOLE.print(table)


# === TOPOLOGICAL SORT (KAHN) ===
def _topological_sort_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks ordered so that dependencies always come first.

    Uses Kahn's algorithm. Raises an error if a cycle is detected.

    Args:
        tasks: The task list.

    Returns:
        Tasks in topological order.

    Raises:
        ValueError: If a cyclic dependency is detected.
    """
    task_by_id = {t.id: t for t in tasks}

    # Edge direction: dep -> task (dep must be created before task).
    adjacency: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {t.id: 0 for t in tasks}

    for t in tasks:
        for dep in t.depends_on:
            if dep == t.id:
                raise ValueError(f"Self-dependency detected for task '{t.id}'.")
            if dep not in task_by_id:
                # Referential errors are handled elsewhere; ignore here to avoid KeyError.
                continue
            if t.id not in adjacency[dep]:
                adjacency[dep].add(t.id)
                indegree[t.id] += 1

    queue: deque[str] = deque(sorted([tid for tid, d in indegree.items() if d == 0]))
    ordered_ids: list[str] = []

    while queue:
        current = queue.popleft()
        ordered_ids.append(current)
        for child in sorted(adjacency.get(current, set())):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if len(ordered_ids) != len(tasks):
        # Identify remaining nodes for better diagnostics.
        remaining = sorted([tid for tid, d in indegree.items() if d > 0])
        raise ValueError(
            "Cyclic dependency detected in tasks. "
            f"Blocked task IDs (non-zero indegree): {remaining}"
        )

    return [task_by_id[tid] for tid in ordered_ids]


def topological_sort_tasks(tasks: list[Task]) -> list[Task]:
    """Compatibility wrapper (public name preserved)."""
    return _topological_sort_tasks(tasks)


# === SEMANTIC VALIDATION BEYOND PYDANTIC (B-SPECIFIC; STRICTLY IMMUTABLE) ===
def validate_project_semantics(project: Project) -> ValidationReport:
    """Validate semantic constraints and recommendations.

    This does not replace Pydantic parsing; it complements it with:
    - Global uniqueness checks across milestones/epics/tasks.
    - Referential integrity checks (parent IDs, dependencies).
    - Protocol recommendations (missing descriptions, Gate containing content).
    - Cycle detection in task dependency graph.

    Args:
        project: Parsed project model.

    Returns:
        A ValidationReport containing all found anomalies.
    """
    issues: list[ValidationIssue] = []

    milestone_ids = [m.id for m in project.milestones]
    epic_ids = [e.id for e in project.epics]
    task_ids = [t.id for t in project.tasks]

    # --- Uniqueness (global)
    all_ids = milestone_ids + epic_ids + task_ids
    duplicates = {x for x in all_ids if all_ids.count(x) > 1}
    for dup in sorted(duplicates):
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                issue_type=IssueType.UNIQUENESS,
                location="(global)",
                message=f"Duplicate ID found: '{dup}'. IDs must be globally unique.",
                suggestion="Rename one of the objects so all IDs are unique.",
            )
        )

    milestone_id_set = set(milestone_ids)
    epic_id_set = set(epic_ids)
    task_id_set = set(task_ids)

    # --- Referential: Epic.parent_id exists
    for idx, epic in enumerate(project.epics):
        if epic.parent_id not in milestone_id_set:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    issue_type=IssueType.REFERENTIAL,
                    location=f"epics[{idx}].parent_id",
                    message=(
                        f"Epic '{epic.id}' references unknown milestone "
                        f"'{epic.parent_id}'."
                    ),
                    suggestion="Fix epic.parent_id to point to an existing milestone.",
                )
            )

    # --- Referential: Task.parent_link exists (milestone or epic)
    for idx, task in enumerate(project.tasks):
        if task.parent_link not in milestone_id_set and task.parent_link not in epic_id_set:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    issue_type=IssueType.REFERENTIAL,
                    location=f"tasks[{idx}].parent_link",
                    message=(
                        f"Task '{task.id}' references unknown parent_link "
                        f"'{task.parent_link}' (must be a milestone or an epic)."
                    ),
                    suggestion="Fix task.parent_link to point to an existing milestone/epic.",
                )
            )

    # --- Referential: dependencies exist and are tasks
    for idx, task in enumerate(project.tasks):
        for dep in task.depends_on:
            if dep not in task_id_set:
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        issue_type=IssueType.REFERENTIAL,
                        location=f"tasks[{idx}].depends_on",
                        message=f"Task '{task.id}' depends on unknown task '{dep}'.",
                        suggestion="Fix depends_on so it only references existing tasks.",
                    )
                )

    # --- Recommendations: missing descriptions
    def _warn_missing_description(obj_desc: str | None, location: str) -> None:
        if obj_desc is None or not str(obj_desc).strip():
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    issue_type=IssueType.RECOMMENDATION,
                    location=location,
                    message="Missing description.",
                    suggestion="Consider adding a description to improve project clarity.",
                )
            )

    _warn_missing_description(project.metadata.description, "metadata.description")
    for i, m in enumerate(project.milestones):
        _warn_missing_description(m.description, f"milestones[{i}].description")
    for i, e in enumerate(project.epics):
        _warn_missing_description(e.description, f"epics[{i}].description")
    for i, t in enumerate(project.tasks):
        _warn_missing_description(t.description, f"tasks[{i}].description")

    # --- Gate milestones should ideally be empty (warning if not)
    epics_by_milestone = defaultdict(list)
    for epic in project.epics:
        epics_by_milestone[epic.parent_id].append(epic)

    # We'll compute each task's milestone later; for now gather by milestone.
    epic_by_id = {e.id: e for e in project.epics}

    def task_milestone_id(task: Task) -> str | None:
        if task.parent_link in milestone_id_set:
            return task.parent_link
        epic = epic_by_id.get(task.parent_link)
        return epic.parent_id if epic else None

    tasks_by_milestone = defaultdict(list)
    for task in project.tasks:
        mid = task_milestone_id(task)
        if mid is not None:
            tasks_by_milestone[mid].append(task)

    for i, m in enumerate(project.milestones):
        if m.configuration == "Gate":
            has_content = bool(epics_by_milestone.get(m.id) or tasks_by_milestone.get(m.id))
            if has_content:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        issue_type=IssueType.PROTOCOL_RULE,
                        location=f"milestones[{i}]",
                        message=(
                            "Milestone configured as 'Gate' should typically be empty, "
                            "but content was found."
                        ),
                        suggestion="Move epics/tasks to an 'Actif' milestone or change configuration.",
                    )
                )

    # --- Configuration vs parent_link (warning)
    for i, t in enumerate(project.tasks):
        if t.parent_link in epic_id_set and t.configuration != "Membre":
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    issue_type=IssueType.PROTOCOL_RULE,
                    location=f"tasks[{i}].configuration",
                    message=(
                        f"Task '{t.id}' is linked to an epic ('{t.parent_link}') "
                        "but configuration is not 'Membre'."
                    ),
                    suggestion="Set configuration to 'Membre' or link directly to a milestone.",
                )
            )
        if t.parent_link in milestone_id_set and t.configuration != "Orpheline":
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    issue_type=IssueType.PROTOCOL_RULE,
                    location=f"tasks[{i}].configuration",
                    message=(
                        f"Task '{t.id}' is linked directly to a milestone ('{t.parent_link}') "
                        "but configuration is not 'Orpheline'."
                    ),
                    suggestion="Set configuration to 'Orpheline' or link to an epic.",
                )
            )

    # --- Dependency temporal recommendation: dependency should not be in a later milestone
    milestone_index = {m.id: idx for idx, m in enumerate(project.milestones)}
    task_by_id = {t.id: t for t in project.tasks}

    def _task_m_index(tid: str) -> int | None:
        t = task_by_id.get(tid)
        if t is None:
            return None
        mid = task_milestone_id(t)
        if mid is None:
            return None
        return milestone_index.get(mid)

    for i, t in enumerate(project.tasks):
        t_idx = _task_m_index(t.id)
        if t_idx is None:
            continue
        for dep in t.depends_on:
            d_idx = _task_m_index(dep)
            if d_idx is None:
                continue
            if d_idx > t_idx:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        issue_type=IssueType.RECOMMENDATION,
                        location=f"tasks[{i}].depends_on",
                        message=(
                            f"Task '{t.id}' depends on '{dep}', which appears to be "
                            "in a later milestone."
                        ),
                        suggestion="Consider moving the dependency earlier or revising milestones.",
                    )
                )

    # --- Cycle detection
    try:
        _ = topological_sort_tasks(project.tasks)
    except ValueError as exc:
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                issue_type=IssueType.STRUCTURAL,
                location="tasks[*].depends_on",
                message=str(exc),
                suggestion="Remove cyclic dependencies so the task graph becomes a DAG.",
            )
        )

    return ValidationReport(issues=issues)


# === GITHUB API HELPERS (PYGITHUB) WITH RETRIES AND RATE-LIMIT HANDLING ===
def _is_rate_limit_error(exc: GithubException) -> bool:
    msg = (exc.data or {}).get("message", "")
    return exc.status == 403 and "rate limit" in str(msg).lower()


def _rate_limit_sleep_seconds(exc: GithubException) -> int | None:
    reset = None
    if exc.headers:
        reset = exc.headers.get("X-RateLimit-Reset")
    if not reset:
        return None
    try:
        reset_ts = int(reset)
    except ValueError:
        return None

    now_ts = int(time.time())
    return max(1, reset_ts - now_ts + 2)


def call_with_retries(
    fn: Callable[[], Any],
    *,
    max_retries: int,
    base_backoff_s: float,
) -> Any:
    """Execute a GitHub API call with retries and rate-limit handling.

    Args:
        fn: A no-arg callable performing the API operation.
        max_retries: Maximum retries before failing.
        base_backoff_s: Base backoff in seconds for transient errors.

    Returns:
        The callable result.

    Raises:
        GithubException: When the call ultimately fails.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except GithubException as exc:
            attempt += 1
            if _is_rate_limit_error(exc):
                sleep_s = _rate_limit_sleep_seconds(exc)
                if sleep_s is None:
                    sleep_s = int(base_backoff_s * (2 ** min(attempt, 6)))
                CONSOLE.print(f"[yellow]Rate limit hit. Sleeping {sleep_s}s...[/yellow]")
                time.sleep(sleep_s)
                if attempt <= max_retries:
                    continue
                raise

            # Retry common transient statuses.
            if exc.status in {500, 502, 503, 504} and attempt <= max_retries:
                sleep_s = base_backoff_s * (2 ** min(attempt, 6))
                CONSOLE.print(
                    f"[yellow]Transient GitHub error {exc.status}. "
                    f"Retrying in {sleep_s:.1f}s...[/yellow]"
                )
                time.sleep(sleep_s)
                continue
            raise


# === MATERIALIZATION LOGIC ===
def parse_t0(value: str | None) -> date:
    """Parse the pivot date (T0).

    Args:
        value: ISO date string YYYY-MM-DD, or None.

    Returns:
        The parsed date, or today's date if value is None.

    Raises:
        ValueError: If parsing fails.
    """
    if value is None:
        return date.today()
    return date.fromisoformat(value)


def milestone_due_on(t0: date, milestone: Milestone) -> datetime:
    """Compute GitHub milestone due_on datetime (UTC).

    Per mission requirement:
        due_date = T0 + start_delay + duration

    Args:
        t0: Pivot date.
        milestone: Milestone model.

    Returns:
        A timezone-aware datetime in UTC.
    """
    due_d = t0 + timedelta(days=int(milestone.start_delay + milestone.duration))
    return datetime.combine(due_d, dt_time(23, 59), tzinfo=timezone.utc)


def build_issue_body_header(protocol_id: str, kind: str) -> str:
    """Build a standardized header to embed protocol identity.

    Args:
        protocol_id: Protocol object ID (M-xx, E-xx, T-xx).
        kind: Human readable kind label.

    Returns:
        A markdown string.
    """
    return f"**Kind:** {kind}\n" f"**Protocol-ID:** {protocol_id}\n"


def render_epic_body(epic: Epic) -> str:
    """Render an epic issue body.

    Args:
        epic: Epic model.

    Returns:
        Markdown body.
    """
    desc = epic.description.strip() if epic.description else ""
    body = [
        build_issue_body_header(epic.id, "Epic"),
        f"**Configuration:** {epic.configuration}\n",
        f"**Milestone-ID:** {epic.parent_id}\n",
    ]
    if desc:
        body.append("\n---\n")
        body.append(desc)
    return "".join(body).strip() + "\n"


def render_task_body(task: Task, parent_refs: list[int]) -> str:
    """Render a task issue body, injecting dependency links.

    Args:
        task: Task model.
        parent_refs: GitHub issue numbers of parent tasks (dependencies).

    Returns:
        Markdown body with "Depends on #X" injection.
    """
    desc = task.description.strip() if task.description else ""
    body_lines: list[str] = [
        build_issue_body_header(task.id, "Task"),
        f"**Configuration:** {task.configuration}\n",
        f"**Estimate:** {task.estimate}\n",
        f"**Parent-Link:** {task.parent_link}\n",
    ]

    if parent_refs:
        deps_md = ", ".join(f"#{n}" for n in parent_refs)
        body_lines.append(f"\n### Dependencies\nDepends on {deps_md}\n")

    if desc:
        body_lines.append("\n---\n")
        body_lines.append(desc)

    return "".join(body_lines).strip() + "\n"


def ensure_labels(
    repo: Any,
    label_names: set[str],
    *,
    dry_run: bool,
    max_retries: int,
    base_backoff_s: float,
) -> None:
    """Ensure a set of labels exist in the repository.

    Args:
        repo: PyGithub repository object.
        label_names: Label names to ensure.
        dry_run: If True, do not call the API.
        max_retries: Retry limit.
        base_backoff_s: Base backoff seconds.
    """
    existing = {
        lab.name
        for lab in call_with_retries(
            lambda: list(repo.get_labels()),
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
    }

    missing = sorted(label_names - existing)
    if not missing:
        return

    for name in missing:
        if dry_run:
            CONSOLE.print(f"[cyan]DRY RUN[/cyan] Create label '{name}'")
            continue

        # Simple deterministic color based on hash to avoid arbitrary choices.
        color = f"{(abs(hash(name)) % 0xFFFFFF):06x}"
        call_with_retries(
            lambda n=name, c=color: repo.create_label(name=n, color=c),
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        CONSOLE.print(f"[green]Created label[/green] '{name}'")


def upsert_milestones(
    repo: Any,
    t0: date,
    milestones: list[Milestone],
    *,
    dry_run: bool,
    max_retries: int,
    base_backoff_s: float,
) -> dict[str, Any]:
    """Create or update GitHub milestones, returning a lookup by protocol ID.

    Uses milestone title as the idempotency key.

    Args:
        repo: PyGithub repository object.
        t0: Pivot date.
        milestones: Protocol milestones.
        dry_run: If True, do not call the API.
        max_retries: Retry limit.
        base_backoff_s: Base backoff seconds.

    Returns:
        Dict mapping protocol milestone ID -> PyGithub milestone object (or stub dict if dry_run).
    """
    existing_by_title: dict[str, Any] = {}
    if not dry_run:
        existing_ms = call_with_retries(
            lambda: list(repo.get_milestones(state="all")),
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        existing_by_title = {m.title: m for m in existing_ms}

    lookup: dict[str, Any] = {}

    for m in milestones:
        due_on = milestone_due_on(t0, m)
        desc = m.description or ""

        if dry_run:
            CONSOLE.print(
                "[cyan]DRY RUN[/cyan] Upsert milestone "
                f"'{m.titre}' (Protocol-ID: {m.id}, due: {due_on.date().isoformat()})"
            )
            lookup[m.id] = {"title": m.titre}
            continue

        if m.titre in existing_by_title:
            gh_m = existing_by_title[m.titre]
            call_with_retries(
                lambda: gh_m.edit(title=m.titre, description=desc, due_on=due_on),
                max_retries=max_retries,
                base_backoff_s=base_backoff_s,
            )
            CONSOLE.print(
                f"[green]Updated milestone[/green] '{m.titre}' "
                f"(Protocol-ID: {m.id}, due: {due_on.date().isoformat()})"
            )
            lookup[m.id] = gh_m
            continue

        gh_m = call_with_retries(
            lambda: repo.create_milestone(title=m.titre, description=desc, due_on=due_on),
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        CONSOLE.print(
            f"[green]Created milestone[/green] '{m.titre}' "
            f"(Protocol-ID: {m.id}, due: {due_on.date().isoformat()})"
        )
        lookup[m.id] = gh_m

    return lookup


def compute_task_milestone_id(
    task: Task,
    milestone_ids: set[str],
    epic_by_id: dict[str, Epic],
) -> str:
    """Resolve the milestone ID for a task.

    Args:
        task: Task model.
        milestone_ids: Set of milestone IDs.
        epic_by_id: Epic lookup.

    Returns:
        The protocol milestone ID.

    Raises:
        ValueError: If the milestone cannot be resolved.
    """
    if task.parent_link in milestone_ids:
        return task.parent_link

    epic = epic_by_id.get(task.parent_link)
    if epic is None:
        raise ValueError(
            f"Unable to resolve milestone for task '{task.id}': "
            f"unknown parent_link '{task.parent_link}'."
        )
    return epic.parent_id


def create_issue(
    repo: Any,
    *,
    title: str,
    body: str,
    labels: list[str],
    milestone: Any | None,
    assignee: str | None,
    dry_run: bool,
    max_retries: int,
    base_backoff_s: float,
) -> Any:
    """Create a GitHub issue with retry logic.

    Args:
        repo: PyGithub repository object.
        title: Issue title.
        body: Issue body (markdown).
        labels: Label names.
        milestone: PyGithub milestone object (or None).
        assignee: GitHub username or None.
        dry_run: If True, do not call the API.
        max_retries: Retry limit.
        base_backoff_s: Base backoff seconds.

    Returns:
        PyGithub Issue object or a stub dict if dry_run.
    """
    if dry_run:
        CONSOLE.print(f"[cyan]DRY RUN[/cyan] Create issue '{title}'")
        return {"number": -1, "title": title}

    kwargs: dict[str, Any] = {
        "title": title,
        "body": body,
    }
    if labels:
        kwargs["labels"] = labels
    if milestone is not None:
        kwargs["milestone"] = milestone
    if assignee:
        kwargs["assignee"] = assignee

    return call_with_retries(
        lambda: repo.create_issue(**kwargs),
        max_retries=max_retries,
        base_backoff_s=base_backoff_s,
    )


def materialize_project(
    project: Project,
    *,
    repo_full_name: str,
    token: str,
    t0: date,
    dry_run: bool,
    max_retries: int,
    base_backoff_s: float,
) -> None:
    """Materialize the project on GitHub.

    Steps:
      1) Create/update milestones.
      2) Ensure labels (epic/task + epic labels).
      3) Create epic issues.
      4) Topologically sort tasks and create them in order, injecting dependency links.

    Args:
        project: Parsed project.
        repo_full_name: "OWNER/REPO".
        token: GitHub token.
        t0: Pivot date.
        dry_run: If True, do not perform API writes.
        max_retries: Retry limit.
        base_backoff_s: Base backoff seconds.
    """
    if not dry_run and not token:
        raise ValueError("GitHub token is required (use --token or GITHUB_TOKEN).")

    gh = Github(token) if not dry_run else None
    repo = gh.get_repo(repo_full_name) if not dry_run else None

    CONSOLE.print(
        f"[bold]Project:[/bold] {project.metadata.projet_nom} "
        f"(Protocol {project.metadata.version_protocole})"
    )
    CONSOLE.print(f"[bold]Repo:[/bold] {repo_full_name}")
    CONSOLE.print(f"[bold]T0:[/bold] {t0.isoformat()}")

    # Phase 1: milestones
    milestone_lookup = upsert_milestones(
        repo,
        t0,
        project.milestones,
        dry_run=dry_run,
        max_retries=max_retries,
        base_backoff_s=base_backoff_s,
    )

    # Labels: mandatory + all epic labels
    label_names = {"epic", "task"}
    for epic in project.epics:
        if epic.label and epic.label.strip():
            label_names.add(epic.label.strip())

    if not dry_run:
        ensure_labels(
            repo,
            label_names,
            dry_run=dry_run,
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
    else:
        CONSOLE.print(f"[cyan]DRY RUN[/cyan] Ensure labels: {sorted(label_names)}")

    # Phase 2A: epics as issues
    epic_by_id = {e.id: e for e in project.epics}
    milestone_ids = {m.id for m in project.milestones}

    lookup_table: dict[str, int] = {}  # {"ID_PROTOCOLE": github_issue_number}

    CONSOLE.print("\n[bold]Creating epic issues...[/bold]")
    for epic in project.epics:
        labels = ["epic"]
        if epic.label and epic.label.strip():
            labels.append(epic.label.strip())

        gh_milestone = milestone_lookup.get(epic.parent_id)
        if gh_milestone is None:
            raise ValueError(
                f"Milestone lookup missing for epic '{epic.id}' -> '{epic.parent_id}'."
            )

        issue = create_issue(
            repo,
            title=epic.titre,
            body=render_epic_body(epic),
            labels=labels,
            milestone=gh_milestone,
            assignee=None,
            dry_run=dry_run,
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        number = int(issue["number"] if dry_run else issue.number)
        lookup_table[epic.id] = number
        CONSOLE.print(
            f"[green]Epic[/green] {epic.id} -> "
            f"{'#' + str(number) if number != -1 else '(dry-run)'}"
        )

    # Phase 2B: tasks in topological order
    CONSOLE.print("\n[bold]Topological sorting tasks...[/bold]")
    ordered_tasks = topological_sort_tasks(project.tasks)
    CONSOLE.print(f"[green]OK[/green] {len(ordered_tasks)} tasks ordered.")

    CONSOLE.print("\n[bold]Creating task issues...[/bold]")
    for task in ordered_tasks:
        # Resolve milestone and epic label inheritance
        mid = compute_task_milestone_id(task, milestone_ids, epic_by_id)
        gh_milestone = milestone_lookup.get(mid)
        if gh_milestone is None:
            raise ValueError(
                f"Milestone lookup missing for task '{task.id}' -> milestone '{mid}'."
            )

        inherited_epic_label: str | None = None
        if task.parent_link in epic_by_id:
            inherited_epic_label = epic_by_id[task.parent_link].label

        labels = ["task"]
        if inherited_epic_label and inherited_epic_label.strip():
            labels.append(inherited_epic_label.strip())

        # Dependency injection: "Depends on #X"
        dep_issue_numbers: list[int] = []
        for dep_id in task.depends_on:
            if dep_id not in lookup_table:
                raise ValueError(
                    f"Dependency '{dep_id}' for task '{task.id}' was not created yet. "
                    "This should not happen if the graph is a DAG and sorting is correct."
                )
            dep_issue_numbers.append(lookup_table[dep_id])

        issue = create_issue(
            repo,
            title=task.titre,
            body=render_task_body(task, dep_issue_numbers),
            labels=labels,
            milestone=gh_milestone,
            assignee=task.assignee,
            dry_run=dry_run,
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        number = int(issue["number"] if dry_run else issue.number)
        lookup_table[task.id] = number

        deps_txt = ""
        if dep_issue_numbers:
            deps_txt = " (depends on " + ", ".join(f"#{n}" for n in dep_issue_numbers) + ")"

        CONSOLE.print(
            f"[green]Task[/green] {task.id} -> "
            f"{'#' + str(number) if number != -1 else '(dry-run)'}{deps_txt}"
        )

    CONSOLE.print("\n[bold green]Deployment complete.[/bold green]")


# === CLI / ORCHESTRATION (STRICTLY IMMUTABLE) ===
def load_project_json(path: Path) -> dict[str, Any]:
    """Load JSON from disk.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed JSON dict.

    Raises:
        OSError: If file cannot be read.
        json.JSONDecodeError: If JSON is invalid.
    """
    # Delegates to validator's strictly identical JSON reader.
    return _read_json_file(path)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Instantiate a SPEC-1.0.0 project on GitHub using topological deployment."
    )
    parser.add_argument(
        "json_path",
        type=str,
        help="Path to the SPEC-1.0.0 JSON file.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=str,
        help="Target GitHub repository as OWNER/REPO.",
    )
    parser.add_argument(
        "--t0",
        required=False,
        type=str,
        default=None,
        help="Pivot date (T0) in YYYY-MM-DD. Defaults to today.",
    )
    parser.add_argument(
        "--token",
        required=False,
        type=str,
        default=None,
        help="GitHub token (overrides env var GITHUB_TOKEN).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call GitHub APIs; only print planned operations.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=6,
        help="Maximum number of retries for API calls (default: 6).",
    )
    parser.add_argument(
        "--base-backoff-s",
        type=float,
        default=2.0,
        help="Base backoff seconds for retries (default: 2.0).",
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Compatibility wrapper (public name preserved)."""
    return _build_arg_parser()


def _run(args: argparse.Namespace) -> int:
    """Execute CLI logic and return a process exit code.

    Args:
        args: Parsed argparse namespace.

    Returns:
        Exit code (0/1/2).
    """
    json_path = Path(args.json_path)
    if not json_path.exists():
        CONSOLE.print(f"[red]File not found:[/red] {json_path}")
        return 2

    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    try:
        t0 = parse_t0(args.t0)
    except ValueError as exc:
        CONSOLE.print(f"[red]Invalid --t0 value:[/red] {exc}")
        return 2

    try:
        raw = load_project_json(json_path)
    except Exception as exc:  # noqa: BLE001
        CONSOLE.print(f"[red]Failed to read/parse JSON:[/red] {exc}")
        return 2

    try:
        project = Project.model_validate(raw)
    except ValidationError as exc:
        CONSOLE.print("[red]Pydantic validation failed.[/red]")
        CONSOLE.print(str(exc))
        return 1
    except ValueError as exc:
        CONSOLE.print("[red]Validation failed.[/red]")
        CONSOLE.print(str(exc))
        return 1

    report = validate_project_semantics(project)
    print_validation_report(report)
    if report.has_errors():
        CONSOLE.print("[red]Blocking errors found. Aborting before any GitHub call.[/red]")
        return 1

    try:
        materialize_project(
            project,
            repo_full_name=args.repo,
            token=token,
            t0=t0,
            dry_run=bool(args.dry_run),
            max_retries=int(args.max_retries),
            base_backoff_s=float(args.base_backoff_s),
        )
    except GithubException as exc:
        CONSOLE.print("[red]GitHub API error.[/red]")
        CONSOLE.print(f"Status: {exc.status}")
        CONSOLE.print(f"Data: {exc.data}")
        return 1
    except Exception as exc:  # noqa: BLE001
        CONSOLE.print("[red]Deployment failed.[/red]")
        CONSOLE.print(str(exc))
        return 1

    return 0


# ///   E N T R Y   P O I N T   ///
def main() -> None:
    """CLI entry point.

    Notes:
        - Must not accept argv, and must not inject sys.argv explicitly.
        - Preserves the exact CLI contract (argparse) and exit codes (0/1/2).
    """
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(_run(args))


if __name__ == "__main__":
    main()