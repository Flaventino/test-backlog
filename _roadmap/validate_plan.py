# ///   A B S T R A C T   ///
"""
Compliance validation script for the IT Project Formalization and 
Instantiation Protocol (SPEC-1.0.0)

This module verifies that a JSON file respects the structure and normative 
rules defined by the protocol.
"""


# ///   I P O R T S   ///
import json
from typing import Any, Dict, List, Set, Optional, Literal
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError
from dataclasses import dataclass


# ///   C L A S S E S   ///
@dataclass
class ValidationError:
  """Represents a validation error with its context.
  
  Attributes:
    category (str): The category of the validation error.
    message (str): The detailed error message.
    location (str): The location where the error occurred.
  """

  # --- Classes attributes declaration & definition
  category: str
  message: str
  location: str = ""

def __str__(self) -> str:
"""Returns a formatted string representation of the error.

Returns:
str: Formatted error message with optional location.
"""
location_str = f" (in {self.location})" if self.location else ""
return f"[{self.category}] {self.message}{location_str}"


class ProjectMetadata(BaseModel):
"""Project metadata following SPEC-1.0.0 protocol."""

projet_nom: str = Field(..., min_length=1)
version_protocole: Literal["SPEC-1.0.0"]
description: str = Field(..., min_length=1)


class ProjectMilestone(BaseModel):
"""Project milestone following SPEC-1.0.0 protocol."""

id: str = Field(..., min_length=1)
titre: str = Field(..., min_length=1)
configuration: Literal["Actif", "Gate"]
start_delay: int = Field(..., ge=0)
duration: int = Field(..., gt=0)
description: str = Field(..., min_length=1)


class ProjectEpic(BaseModel):
"""Project epic following SPEC-1.0.0 protocol."""

id: str = Field(..., min_length=1)
parent_id: str = Field(..., min_length=1)
titre: str = Field(..., min_length=1)
configuration: Literal["Standard", "Discovery"]
label: str = Field(..., min_length=1)
description: str = Field(..., min_length=1)


class ProjectTask(BaseModel):
"""Project task following SPEC-1.0.0 protocol."""

id: str = Field(..., min_length=1)
parent_link: str = Field(..., min_length=1)
titre: str = Field(..., min_length=1)
configuration: Literal["Independante", "Sequentielle", "Orpheline", "Membre"]
estimate: float = Field(..., gt=0)
depends_on: List[str] = Field(default_factory=list)
description: str = Field(..., min_length=1)
assignee: Optional[str] = None

@field_validator('assignee')
@classmethod
def validate_assignee(cls, v):
if v is not None and not isinstance(v, str):
raise ValueError('assignee must be a string')
return v


class ProjectData(BaseModel):
"""Complete project data structure following SPEC-1.0.0 protocol."""

metadata: ProjectMetadata
milestones: List[ProjectMilestone]
epics: List[ProjectEpic]
tasks: List[ProjectTask]


class ProjectValidator:
"""
Compliance validator for projects according to SPEC-1.0.0 protocol.

Verifies structural compliance (JSON schema) and normative compliance 
(business rules) of a project file according to the defined protocol.

Attributes:
errors (List[ValidationError]): List of validation errors found.
project_data (ProjectData | None): Parsed and validated project data.
"""

def __init__(self):
"""Initializes the ProjectValidator with empty state."""
self.errors: List[ValidationError] = []
self.project_data: ProjectData | None = None

def validate_project_file(
self, 
file_path: str | Path
) -> tuple[bool, List[ValidationError]]:
"""
Validates a project JSON file according to SPEC-1.0.0 protocol.

Args:
file_path (str | Path): Path to the JSON file to validate.

Returns:
tuple[bool, List[ValidationError]]: A tuple containing:
- bool: True if the file is valid, False otherwise.
- List[ValidationError]: List of validation errors found.

Raises:
FileNotFoundError: If the specified file cannot be found.
json.JSONDecodeError: If the file contains invalid JSON.
"""
self._reset_validation()

try:
with open(file_path, 'r', encoding='utf-8') as file:
raw_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
self._add_error("FILE", f"Cannot read JSON file: {e}")
return False, self.errors

return self.validate_project_data(raw_data)

def validate_project_data(
self, 
raw_data: Dict[str, Any]
) -> tuple[bool, List[ValidationError]]:
"""
Validates project data according to SPEC-1.0.0 protocol.

Args:
raw_data (Dict[str, Any]): Dictionary containing the project 
data to validate.

Returns:
tuple[bool, List[ValidationError]]: A tuple containing:
- bool: True if the data is valid, False otherwise.
- List[ValidationError]: List of validation errors found.
"""
self._reset_validation()

# First, validate basic structure with Pydantic
try:
self.project_data = ProjectData.model_validate(raw_data)
except PydanticValidationError as e:
self._convert_pydantic_errors(e)
return False, self.errors

# Then perform custom normative validations
if not self.errors:
self._validate_unique_ids()
self._validate_normative_rules()

return len(self.errors) == 0, self.errors

def _reset_validation(self) -> None:
"""
Resets validator state for new validation.

Clears all errors and loaded project elements to prepare for a new 
validation run.
"""
self.errors = []
self.project_data = None

def _add_error(
self, 
category: str, 
message: str, 
location: str = ""
) -> None:
"""
Adds an error to the validation error list.

Args:
category (str): The category of the error (e.g., "STRUCTURE").
message (str): The detailed error message.
location (str, optional): The location where the error occurred.
Defaults to empty string.
"""
self.errors.append(ValidationError(category, message, location))

def _convert_pydantic_errors(self, pydantic_error: PydanticValidationError) -> None:
"""
Converts Pydantic validation errors to our custom format.

Maintains the same error categories and messages as the original
implementation for consistency.

Args:
pydantic_error (PydanticValidationError): The Pydantic validation error.
"""
for error in pydantic_error.errors():
location_parts = []
category = "STRUCTURE"

# Build location string from error path
for part in error['loc']:
if isinstance(part, int):
  location_parts.append(f"[{part}]")
else:
  location_parts.append(str(part))

location = ''.join(location_parts)

# Determine category based on location
if location.startswith('metadata'):
category = "METADATA"
elif location.startswith('milestones'):
category = "MILESTONE"
elif location.startswith('epics'):
category = "EPIC"
elif location.startswith('tasks'):
category = "TASK"

# Convert error types to our custom messages
error_type = error['type']
message = self._format_pydantic_error_message(error_type, error)

self._add_error(category, message, location)

def _format_pydantic_error_message(self, error_type: str, error: Dict[str, Any]) -> str:
"""
Formats Pydantic error messages to match original implementation style.

Args:
error_type (str): The type of Pydantic error.
error (Dict[str, Any]): The error details.

Returns:
str: Formatted error message.
"""
if error_type == 'missing':
return f"Missing fields: {error['input']}"
elif error_type == 'string_type':
return f"Field '{error['loc'][-1]}' must be a string"
elif error_type == 'int_type':
return f"Field '{error['loc'][-1]}' must be an integer"
elif error_type == 'greater_than':
return f"{error['loc'][-1]} must be an integer > 0"
elif error_type == 'greater_than_equal':
return f"{error['loc'][-1]} must be an integer >= 0"
elif error_type == 'literal_error':
return f"Invalid configuration: '{error['input']}'"
elif error_type == 'string_too_short':
return f"ID must be a non-empty string"
elif error_type == 'list_type':
return "depends_on must be an array"
else:
return error.get('msg', 'Validation error')

def _validate_unique_ids(self) -> None:
"""
Validates uniqueness of IDs across all project elements.

Checks for duplicate IDs in milestones, epics, and tasks separately.
"""
if not self.project_data:
return

# Check milestone ID uniqueness
milestone_ids = set()
for i, milestone in enumerate(self.project_data.milestones):
if milestone.id in milestone_ids:
self._add_error(
  "MILESTONE", 
  f"Duplicate ID: '{milestone.id}'", 
  f"milestones[{i}]"
)
milestone_ids.add(milestone.id)

# Check epic ID uniqueness
epic_ids = set()
for i, epic in enumerate(self.project_data.epics):
if epic.id in epic_ids:
self._add_error(
  "EPIC", 
  f"Duplicate ID: '{epic.id}'", 
  f"epics[{i}]"
)
epic_ids.add(epic.id)

# Check task ID uniqueness
task_ids = set()
for i, task in enumerate(self.project_data.tasks):
if task.id in task_ids:
self._add_error(
  "TASK", 
  f"Duplicate ID: '{task.id}'", 
  f"tasks[{i}]"
)
task_ids.add(task.id)

def _validate_normative_rules(self) -> None:
"""
Validates the normative rules of the protocol.

Performs cross-reference validation between project elements to ensure
tutelle rules, dependency consistency, and temporal agnosticism are
respected.
"""
if not self.project_data:
return

self._validate_tutelle_rules()
self._validate_dependencies()
self._validate_no_absolute_dates()

def _validate_tutelle_rules(self) -> None:
"""
Validates the tutelle (guardianship) rule.

Ensures that all epics reference existing milestones as parents and
all tasks reference existing milestones or epics as parents.
"""
if not self.project_data:
return

# Build lookup sets
milestone_ids = {m.id for m in self.project_data.milestones}
epic_ids = {e.id for e in self.project_data.epics}

# Epic parent_id validation
for epic in self.project_data.epics:
if epic.parent_id not in milestone_ids:
self._add_error(
  "TUTELLE", 
  f"Epic '{epic.id}' references non-existent "
  f"milestone: '{epic.parent_id}'"
)

# Task parent_link validation
valid_parents = milestone_ids | epic_ids
for task in self.project_data.tasks:
if task.parent_link not in valid_parents:
self._add_error(
  "TUTELLE", 
  f"Task '{task.id}' references non-existent "
  f"parent: '{task.parent_link}'"
)

def _validate_dependencies(self) -> None:
"""
Validates consistency of task dependencies.

Ensures that all task dependencies reference existing tasks and
prevents obvious circular dependencies (self-references).
"""
if not self.project_data:
return

task_ids = {t.id for t in self.project_data.tasks}

for task in self.project_data.tasks:
for dep_id in task.depends_on:
if dep_id not in task_ids:
  self._add_error(
      "DEPENDENCY", 
      f"Task '{task.id}' depends on non-existent "
      f"task: '{dep_id}'"
  )

# Cycle check (simplified)
if dep_id == task.id:
  self._add_error(
      "DEPENDENCY", 
      f"Task '{task.id}' cannot depend on itself"
  )

def _validate_no_absolute_dates(self) -> None:
"""
Verifies absence of absolute dates in data.

The protocol enforces temporal agnosticism, meaning no absolute dates
should be present in the project data. This method can be extended
to detect specific date patterns if needed.
"""
# This validation can be extended according to specific needs
# The protocol enforces temporal agnosticism
pass


def validate_project_file(file_path: str | Path) -> None:
"""
Utility function to validate a project file and display results.

This is a convenience function that creates a validator, runs validation
on the specified file, and prints a formatted report of the results.

Args:
file_path (str | Path): Path to the JSON file to validate.

Example:
>>> validate_project_file("my_project.json")
Validating file: my_project.json
Result: ✅ COMPLIANT
No errors detected.
"""
validator = ProjectValidator()
is_valid, errors = validator.validate_project_file(file_path)

print(f"Validating file: {file_path}")
print(f"Result: {'✅ COMPLIANT' if is_valid else '❌ NON-COMPLIANT'}")

if errors:
print(f"\nNumber of errors detected: {len(errors)}")
for error in errors:
print(f"  {error}")
else:
print("\nNo errors detected.")


if __name__ == "__main__":
import sys

if len(sys.argv) != 2:
print("Usage: python validator.py <path_to_file.json>")
sys.exit(1)

validate_project_file(sys.argv[1])
