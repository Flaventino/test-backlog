# ///   A B S T R A C T   ///
"""
Protocol Compliance Validator (SPEC-1.0.0)

This script validates whether a given JSON file is a conforming instantiation of
the protocol "PROTOCOLE DE FORMALISATION ET D'INSTANCIATION DE PROJETS
INFORMATIQUES" (SPEC-1.0.0).

Validation covers two inseparable dimensions:
1) Structural compliance (strict schema, types, required fields, allowed values)
2) Minimal normative compliance (referential integrity, uniqueness, mandatory
   protocol rules, and specified warnings)

Core output (common to all usage modes):
- A comprehensive set of validation issues (errors and warnings), each with:
  * Category (error/warning)
  * Location (JSON path)
  * Clear description in English
  * Correction suggestion (when possible)

Mode-specific output:
- CLI tool: Exit code 0 (success) or 20 (blocking errors detected)
- Module: Boolean status True (success) or False (blocking errors detected)

Requirements:
- Python 3.11+
- pydantic v2
"""


# ///   I M P O R T S   ///
from __future__ import annotations

import argparse
import json
import sys

from enum import Enum
from typing import Any, Iterable, Literal
from pathlib import Path
from dataclasses import dataclass

from pydantic import ValidationError, model_validator
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt


# ///   C L A S S E S   ///
class Severity(str, Enum):
    """Issue severity as required by the protocol."""

    ERROR = "error"
    WARNING = "warning"


class IssueType(str, Enum):
    """Semantic categorization of validation issues."""

    STRUCTURAL = "structural"
    REFERENTIAL = "referential"
    UNIQUENESS = "uniqueness"
    PROTOCOL_RULE = "protocol_rule"
    RECOMMENDATION = "recommendation"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Represents a single validation anomaly."""

    severity: Severity
    issue_type: IssueType
    location: str
    message: str
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Aggregates validation issues and provides convenience helpers."""

    issues: list[ValidationIssue]

    def has_errors(self) -> bool:
        """Returns True if at least one blocking error exists."""
        return any(i.severity == Severity.ERROR for i in self.issues)


class Metadata(BaseModel):
    """Pydantic model for project metadata."""

    model_config = ConfigDict(extra="forbid", strict=True)

    projet_nom: str
    version_protocole: Literal["SPEC-1.0.0"]
    description: str | None = None


class Milestone(BaseModel):
    """Pydantic model for milestones."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    titre: str
    configuration: Literal["Actif", "Gate"]
    start_delay: StrictInt = Field(ge=0)
    duration: StrictInt = Field(ge=0)
    description: str | None = None


class Epic(BaseModel):
    """Pydantic model for epics."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    parent_id: str
    titre: str
    configuration: Literal["Standard", "Discovery"]
    label: str | None = None
    description: str | None = None


class Task(BaseModel):
    """Pydantic model for tasks."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    parent_link: str
    titre: str
    configuration: Literal["Indépendante", "Sequentielle", "Orpheline", "Membre"]
    estimate: StrictInt | StrictFloat = Field(ge=0)
    depends_on: list[str]
    description: str | None = None
    assignee: str | None = None

    @model_validator(mode="after")
    def _check_task_is_really_independent(self) -> "Task":
        """Protocol rule: Independent tasks must have an empty depends_on.

        Returns:
            The validated task.

        Raises:
            ValueError: If the rule is violated.
        """
        if self.configuration == "Indépendante" and self.depends_on:
            txt = "For configuration 'Indépendante', 'depends_on' must empty."
            raise ValueError(txt)
        return self


class Project(BaseModel):
    """Root Pydantic model for the protocol JSON document."""

    model_config = ConfigDict(extra="forbid", strict=True)

    metadata: Metadata
    milestones: list[Milestone]
    epics: list[Epic]
    tasks: list[Task]


# # ///   F U N C T I O N S   ///

# # === BUSINESS LOGIC ===
# def _loc_to_json_path(loc: Iterable[Any]) -> str:
#     """Convert a Pydantic error location to a JSONPath-like string.

#     Args:
#         loc: Pydantic "loc" iterable (e.g., ('tasks', 0, 'id')).

#     Returns:
#         A JSONPath-like location (e.g., $.tasks[0].id).
#     """
#     path = "$"
#     for part in loc:
#         if isinstance(part, int):
#             path += f"[{part}]"
#         else:
#             path += f".{part}"
#     return path
  

# def _suggest_from_pydantic_error(err: dict[str, Any]) -> str | None:
#     """Generate a best-effort suggestion based on a Pydantic error entry."""
#     err_type = err.get("type", "")
#     loc = err.get("loc", ())
#     last = loc[-1] if loc else None

#     if err_type == "missing" and isinstance(last, str):
#         return f"Add the required field '{last}' as defined by the protocol."
#     if err_type == "literal_error":
#         if last == "version_protocole":
#             return "Set 'metadata.version_protocole' to exactly 'SPEC-1.0.0'."
#         return "Set the value to one of the allowed literals defined by the protocol."
#     if err_type in {"extra_forbidden"}:
#         return "Remove the unexpected field (the protocol schema is strict)."
#     if "int" in err_type or "float" in err_type:
#         return "Fix the value type to match the protocol (numeric field expected)."
#     return None


# def _check_global_id_uniqueness(project: Project) -> list[ValidationIssue]:
#     """Check global uniqueness of IDs across milestones, epics and tasks."""
#     occurrences: dict[str, list[str]] = {}

#     for i, m in enumerate(project.milestones):
#         occurrences.setdefault(m.id, []).append(f"$.milestones[{i}].id")
#     for i, e in enumerate(project.epics):
#         occurrences.setdefault(e.id, []).append(f"$.epics[{i}].id")
#     for i, t in enumerate(project.tasks):
#         occurrences.setdefault(t.id, []).append(f"$.tasks[{i}].id")

#     issues: list[ValidationIssue] = []
#     for obj_id, locs in occurrences.items():
#         if len(locs) <= 1:
#             continue
#         locs_str = ", ".join(locs)
#         for loc in locs:
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.ERROR,
#                     issue_type=IssueType.UNIQUENESS,
#                     location=loc,
#                     message=(
#                         f"Duplicate ID '{obj_id}' detected. IDs must be globally unique. "
#                         f"Occurrences: {locs_str}."
#                     ),
#                     suggestion="Rename IDs so each milestone/epic/task ID is unique.",
#                 )
#             )
#     return issues


# def _check_references(project: Project) -> list[ValidationIssue]:
#     """Check referential integrity for parent links and dependencies."""
#     milestone_ids = {m.id for m in project.milestones}
#     epic_ids = {e.id for e in project.epics}
#     task_ids = {t.id for t in project.tasks}

#     issues: list[ValidationIssue] = []

#     for i, e in enumerate(project.epics):
#         if e.parent_id not in milestone_ids:
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.ERROR,
#                     issue_type=IssueType.REFERENTIAL,
#                     location=f"$.epics[{i}].parent_id",
#                     message=(
#                         f"Epic parent_id '{e.parent_id}' does not reference an "
#                         "existing milestone."
#                     ),
#                     suggestion="Set 'parent_id' to an existing milestone ID.",
#                 )
#             )

#     for i, t in enumerate(project.tasks):
#         parent_is_milestone = t.parent_link in milestone_ids
#         parent_is_epic = t.parent_link in epic_ids

#         if not (parent_is_milestone or parent_is_epic):
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.ERROR,
#                     issue_type=IssueType.REFERENTIAL,
#                     location=f"$.tasks[{i}].parent_link",
#                     message=(
#                         f"Task parent_link '{t.parent_link}' does not reference an "
#                         "existing milestone or epic."
#                     ),
#                     suggestion="Set 'parent_link' to an existing milestone ID or epic ID.",
#                 )
#             )

#         if t.configuration == "Orpheline" and not parent_is_milestone:
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.ERROR,
#                     issue_type=IssueType.PROTOCOL_RULE,
#                     location=f"$.tasks[{i}].parent_link",
#                     message=(
#                         "Task configuration is 'Orpheline' but parent_link does not "
#                         "reference a milestone."
#                     ),
#                     suggestion=(
#                         "Either set parent_link to a milestone ID, or change the "
#                         "task configuration."
#                     ),
#                 )
#             )

#         if t.configuration == "Membre" and not parent_is_epic:
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.ERROR,
#                     issue_type=IssueType.PROTOCOL_RULE,
#                     location=f"$.tasks[{i}].parent_link",
#                     message=(
#                         "Task configuration is 'Membre' but parent_link does not "
#                         "reference an epic."
#                     ),
#                     suggestion=(
#                         "Either set parent_link to an epic ID, or change the task "
#                         "configuration."
#                     ),
#                 )
#             )

#         for j, dep in enumerate(t.depends_on):
#             if dep not in task_ids:
#                 issues.append(
#                     ValidationIssue(
#                         severity=Severity.ERROR,
#                         issue_type=IssueType.REFERENTIAL,
#                         location=f"$.tasks[{i}].depends_on[{j}]",
#                         message=(
#                             f"Dependency '{dep}' does not reference an existing task ID."
#                         ),
#                         suggestion="Replace it with an existing task ID or remove it.",
#                     )
#                 )

#     return issues


# def _resolve_task_milestone_id(project: Project) -> dict[str, str]:
#     """Resolve each task's milestone ID using parent_link and epic.parent_id.

#     Returns:
#         Mapping: task_id -> milestone_id

#     Notes:
#         If a task parent_link points to a milestone, that is the milestone.
#         If it points to an epic, milestone is epic.parent_id.
#         If resolution is impossible, the task is omitted from the mapping.
#         (Referential errors are handled elsewhere.)
#     """
#     epic_to_milestone = {e.id: e.parent_id for e in project.epics}
#     milestone_ids = {m.id for m in project.milestones}

#     mapping: dict[str, str] = {}
#     for t in project.tasks:
#         if t.parent_link in milestone_ids:
#             mapping[t.id] = t.parent_link
#         elif t.parent_link in epic_to_milestone:
#             mapping[t.id] = epic_to_milestone[t.parent_link]
#     return mapping


# def _check_gate_milestone_empty(project: Project) -> list[ValidationIssue]:
#     """Warn if a Gate milestone contains epics and/or tasks."""
#     milestone_by_id = {m.id: m for m in project.milestones}
#     epic_parent_map: dict[str, list[int]] = {}
#     for i, e in enumerate(project.epics):
#         epic_parent_map.setdefault(e.parent_id, []).append(i)

#     task_to_milestone = _resolve_task_milestone_id(project)
#     tasks_by_milestone: dict[str, list[int]] = {}
#     for i, t in enumerate(project.tasks):
#         ms_id = task_to_milestone.get(t.id)
#         if ms_id is not None:
#             tasks_by_milestone.setdefault(ms_id, []).append(i)

#     issues: list[ValidationIssue] = []
#     for i, m in enumerate(project.milestones):
#         if m.configuration != "Gate":
#             continue

#         epic_count = len(epic_parent_map.get(m.id, []))
#         task_count = len(tasks_by_milestone.get(m.id, []))
#         if epic_count == 0 and task_count == 0:
#             continue

#         issues.append(
#             ValidationIssue(
#                 severity=Severity.WARNING,
#                 issue_type=IssueType.RECOMMENDATION,
#                 location=f"$.milestones[{i}].configuration",
#                 message=(
#                     "Milestone configuration is 'Gate' but it contains content "
#                     f"(epics: {epic_count}, tasks: {task_count}). A Gate milestone is "
#                     "expected to be empty."
#                 ),
#                 suggestion=(
#                     "Move epics/tasks to an 'Actif' milestone, or change the milestone "
#                     "configuration to 'Actif'."
#                 ),
#             )
#         )

#     return issues


# def _check_dependency_milestone_order(project: Project) -> list[ValidationIssue]:
#     """Warn if a task depends on another task in a later milestone.

#     Protocol statement: dependencies should ideally belong to the same milestone
#     or an earlier milestone (warning if not).
#     """
#     milestone_index = {m.id: i for i, m in enumerate(project.milestones)}
#     task_to_milestone = _resolve_task_milestone_id(project)

#     task_to_milestone_index: dict[str, int] = {}
#     for task_id, ms_id in task_to_milestone.items():
#         if ms_id in milestone_index:
#             task_to_milestone_index[task_id] = milestone_index[ms_id]

#     issues: list[ValidationIssue] = []
#     task_by_id = {t.id: (idx, t) for idx, t in enumerate(project.tasks)}

#     for i, t in enumerate(project.tasks):
#         cur_idx = task_to_milestone_index.get(t.id)
#         if cur_idx is None:
#             continue

#         for j, dep_id in enumerate(t.depends_on):
#             dep_idx = task_to_milestone_index.get(dep_id)
#             if dep_idx is None:
#                 continue
#             if dep_idx > cur_idx:
#                 issues.append(
#                     ValidationIssue(
#                         severity=Severity.WARNING,
#                         issue_type=IssueType.RECOMMENDATION,
#                         location=f"$.tasks[{i}].depends_on[{j}]",
#                         message=(
#                             f"Task depends on '{dep_id}', which belongs to a later "
#                             "milestone. Dependencies should ideally be in the same or an "
#                             "earlier milestone."
#                         ),
#                         suggestion=(
#                             "Move the dependent task earlier, or adjust milestone ordering, "
#                             "or revisit dependencies."
#                         ),
#                     )
#                 )

#     return issues


# def _check_id_prefix_recommendations(project: Project) -> list[ValidationIssue]:
#     """Warn if IDs do not follow the recommended prefix conventions."""
#     issues: list[ValidationIssue] = []

#     for i, m in enumerate(project.milestones):
#         if not m.id.startswith("M-"):
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.WARNING,
#                     issue_type=IssueType.RECOMMENDATION,
#                     location=f"$.milestones[{i}].id",
#                     message=(
#                         "Milestone ID does not follow the recommended prefix convention "
#                         "('M-')."
#                     ),
#                     suggestion="Consider using IDs like 'M-01', 'M-02', etc.",
#                 )
#             )

#     for i, e in enumerate(project.epics):
#         if not e.id.startswith("E-"):
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.WARNING,
#                     issue_type=IssueType.RECOMMENDATION,
#                     location=f"$.epics[{i}].id",
#                     message=(
#                         "Epic ID does not follow the recommended prefix convention ('E-')."
#                     ),
#                     suggestion="Consider using IDs like 'E-01', 'E-02', etc.",
#                 )
#             )

#     for i, t in enumerate(project.tasks):
#         if not t.id.startswith("T-"):
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.WARNING,
#                     issue_type=IssueType.RECOMMENDATION,
#                     location=f"$.tasks[{i}].id",
#                     message=(
#                         "Task ID does not follow the recommended prefix convention ('T-')."
#                     ),
#                     suggestion="Consider using IDs like 'T-01', 'T-02', etc.",
#                 )
#             )

#     return issues


# def _check_missing_descriptions(project: Project) -> list[ValidationIssue]:
#     """Warn when description is missing or null, as required by the protocol."""
#     issues: list[ValidationIssue] = []

#     def warn_if_missing(value: str | None, location: str) -> None:
#         if value is None:
#             issues.append(
#                 ValidationIssue(
#                     severity=Severity.WARNING,
#                     issue_type=IssueType.RECOMMENDATION,
#                     location=location,
#                     message="Consider adding a description to improve project clarity.",
#                     suggestion="Provide a non-null 'description' string.",
#                 )
#             )

#     warn_if_missing(project.metadata.description, "$.metadata.description")

#     for i, m in enumerate(project.milestones):
#         warn_if_missing(m.description, f"$.milestones[{i}].description")
#     for i, e in enumerate(project.epics):
#         warn_if_missing(e.description, f"$.epics[{i}].description")
#     for i, t in enumerate(project.tasks):
#         warn_if_missing(t.description, f"$.tasks[{i}].description")

#     return issues


def _parse_with_pydantic(data: Any) -> tuple[Project | None, list[ValidationIssue]]:
    """Parse and validate the project structurally with Pydantic.

    Args:
        data: Raw parsed JSON.

    Returns:
        A tuple (project_or_none, structural_issues).
    """

    try:
        project = Project.model_validate(data)
        return project, []
    except ValidationError as exceptions:
        issues: list[ValidationIssue] = []
        for error in exceptions.errors():
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    issue_type=IssueType.STRUCTURAL,
                    location=_loc_to_json_path(error.get("loc", ())),
                    message=str(error.get("msg", "Invalid value.")),
                    suggestion=_suggest_from_pydantic_error(error),
                )
            )
        return None, issues


def validate_project_data(data: Any) -> ValidationReport:
    """Validate a parsed JSON object against the protocol.

    Args:
        data: Parsed JSON content (typically a dict).

    Returns:
        ValidationReport containing all detected issues.
    """
    project, issues = _parse_with_pydantic(data)
    if project is None:
        return ValidationReport(issues=issues)

    issues.extend(_check_global_id_uniqueness(project))
    issues.extend(_check_references(project))
    issues.extend(_check_gate_milestone_empty(project))
    issues.extend(_check_dependency_milestone_order(project))
    issues.extend(_check_id_prefix_recommendations(project))
    issues.extend(_check_missing_descriptions(project))

    return ValidationReport(issues=issues)


def _print_report(report: ValidationReport) -> None:
    """Print a human-readable validation report to stdout.
    
    Formats and displays all validation issues grouped by severity and type,
    with suggestions when available. Also shows a final summary indicating
    whether the project is valid or not.
    
    Args:
        report: The ValidationReport object containing all detected issues.
    
    Returns:
        None. Output is printed directly to stdout.
    
    Notes:
        - If no issues are found, prints a success message.
        - Issues are formatted as: [SEVERITY] (type) location: message
        - Suggestions are indented and prefixed with "Suggestion:"
        - Final result line indicates validity status based on presence of errors.
    """

    if not report.issues:
        print("No issues detected. Project is valid.")
        return

    print("Validation report:")
    for issue in report.issues:
        print(
            f"- [{issue.severity.value.upper()}] "
            f"({issue.issue_type.value}) {issue.location}: {issue.message}"
        )
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")

    if report.has_errors():
        print("\nResult: INVALID (blocking errors detected).")
    else:
        print("\nResult: VALID (warnings detected, but no blocking errors).")


def _read_json_file(file_path: Path) -> Any:
    """Read and parse a JSON file.

    Args:
        file_path: Path to a JSON file.

    Returns:
        Parsed JSON content.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    return json.loads(file_path.read_text(encoding="utf-8"))


def validate_project_file(file_path: str | Path) -> bool:
    """Validate a JSON file against the protocol and print the report.

    Args:
        file_path: Path to the JSON file.

    Returns:
        True if valid (no blocking errors), False otherwise.
    """

    # --- Try to load data & handle reading/parsing errors
    try:
        path = Path(file_path)
        data = _read_json_file(path)
    except OSError as error:
        report = ValidationReport(
            issues=[
                ValidationIssue(
                    severity=Severity.ERROR,
                    issue_type=IssueType.STRUCTURAL,
                    location="$",
                    message=f"Cannot read file: {error}.",
                    suggestion="Check the file path and permissions.",
                )
            ]
        )
        _print_report(report)
        return False
    except json.JSONDecodeError as error:
        report = ValidationReport(
            issues=[
                ValidationIssue(
                    severity=Severity.ERROR,
                    issue_type=IssueType.STRUCTURAL,
                    location="$",
                    message=f"Invalid JSON: {error}.",
                    suggestion="Fix JSON syntax (JSON does not support comments).",
                )
            ]
        )
        _print_report(report)
        return False

    # --- Validate business logic & print report
    report = validate_project_data(data)
    _print_report(report)
    return not report.has_errors()


# === ENTRY POINT ===

# --- Command-line interface
def _build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    # --- CLI arguments descriptions
    summary = "Validate a project JSON file against SPEC-1.0.0."
    plan_help = "Path to the JSON file to validate."

    # --- Argument parser configuration
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("--plan", help=plan_help, required=True)
    return parser


# --- Main execution
def main() -> None:
    """CLI entry point.
    
    Parses command-line arguments, validates the specified JSON file,
    prints the validation report, and exits with appropriate exit code.
    
    Exit codes:
        - 0: Validation successful (no blocking errors)
        - 20: Validation failed (blocking errors detected)
    
    Notes:
        This function is only called when the script is executed directly
        from the command line (not when imported as a module).
    """

    # --- CLI argument parsing
    plan = _build_arg_parser().parse_args().plan

    # --- Execute validation and handle exit code
    is_plan_valid = validate_project_file(plan)
    sys.exit(0 if is_plan_valid else 20)


if __name__ == "__main__":
    main()
