"""
Compliance validation script for the IT Project Formalization and 
Instantiation Protocol (SPEC-1.0.0).

This module verifies that a JSON file respects the structure and normative 
rules defined by the protocol.
"""

import json
from typing import Any, Dict, List, Set, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationError:
    """Represents a validation error with its context.
    
    Attributes:
        category (str): The category of the validation error.
        message (str): The detailed error message.
        location (str): The location where the error occurred.
    """
    
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


class ProjectValidator:
    """
    Compliance validator for projects according to SPEC-1.0.0 protocol.
    
    Verifies structural compliance (JSON schema) and normative compliance 
    (business rules) of a project file according to the defined protocol.
    
    Attributes:
        REQUIRED_VERSION (str): The required protocol version.
        VALID_MILESTONE_CONFIGS (set): Valid milestone configurations.
        VALID_EPIC_CONFIGS (set): Valid epic configurations.
        VALID_TASK_CONFIGS (set): Valid task configurations.
        errors (List[ValidationError]): List of validation errors found.
        milestones (Dict[str, Dict[str, Any]]): Loaded milestones by ID.
        epics (Dict[str, Dict[str, Any]]): Loaded epics by ID.
        tasks (Dict[str, Dict[str, Any]]): Loaded tasks by ID.
    """
    
    REQUIRED_VERSION = "SPEC-1.0.0"
    VALID_MILESTONE_CONFIGS = {"Actif", "Gate"}
    VALID_EPIC_CONFIGS = {"Standard", "Discovery"}
    VALID_TASK_CONFIGS = {
        "Independante", "Sequentielle", "Orpheline", "Membre"
    }
    
    def __init__(self):
        """Initializes the ProjectValidator with empty state."""
        self.errors: List[ValidationError] = []
        self.milestones: Dict[str, Dict[str, Any]] = {}
        self.epics: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
    
    def validate_project_file(
        self, 
        file_path: Union[str, Path]
    ) -> tuple[bool, List[ValidationError]]:
        """
        Validates a project JSON file according to SPEC-1.0.0 protocol.
        
        Args:
            file_path (Union[str, Path]): Path to the JSON file to validate.
            
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
                project_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._add_error("FILE", f"Cannot read JSON file: {e}")
            return False, self.errors
        
        return self.validate_project_data(project_data)
    
    def validate_project_data(
        self, 
        project_data: Dict[str, Any]
    ) -> tuple[bool, List[ValidationError]]:
        """
        Validates project data according to SPEC-1.0.0 protocol.
        
        Args:
            project_data (Dict[str, Any]): Dictionary containing the project 
                data to validate.
            
        Returns:
            tuple[bool, List[ValidationError]]: A tuple containing:
                - bool: True if the data is valid, False otherwise.
                - List[ValidationError]: List of validation errors found.
        """
        self._reset_validation()
        
        # Structural validation
        self._validate_root_structure(project_data)
        
        if not self.errors:
            self._validate_metadata(project_data.get("metadata", {}))
            self._validate_milestones(project_data.get("milestones", []))
            self._validate_epics(project_data.get("epics", []))
            self._validate_tasks(project_data.get("tasks", []))
            
            # Normative validation (after loading all elements)
            if not self.errors:
                self._validate_normative_rules()
        
        return len(self.errors) == 0, self.errors
    
    def _reset_validation(self) -> None:
        """
        Resets validator state for new validation.
        
        Clears all errors and loaded project elements to prepare for a new 
        validation run.
        """
        self.errors = []
        self.milestones = {}
        self.epics = {}
        self.tasks = {}
    
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
    
    def _validate_root_structure(self, data: Dict[str, Any]) -> None:
        """
        Validates the root JSON structure.
        
        Checks that the root object contains all required sections and that
        array sections are properly formatted.
        
        Args:
            data (Dict[str, Any]): The root JSON data to validate.
        """
        required_sections = {"metadata", "milestones", "epics", "tasks"}
        
        if not isinstance(data, dict):
            self._add_error(
                "STRUCTURE", 
                "File must contain a root JSON object"
            )
            return
        
        missing_sections = required_sections - set(data.keys())
        if missing_sections:
            missing_list = ', '.join(missing_sections)
            self._add_error(
                "STRUCTURE", 
                f"Missing sections: {missing_list}"
            )
        
        for section in ["milestones", "epics", "tasks"]:
            if section in data and not isinstance(data[section], list):
                self._add_error(
                    "STRUCTURE", 
                    f"Section '{section}' must be an array"
                )
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Validates the metadata section.
        
        Checks that all required metadata fields are present and have correct
        types, with special attention to protocol version compliance.
        
        Args:
            metadata (Dict[str, Any]): The metadata section to validate.
        """
        required_fields = {"projet_nom", "version_protocole", "description"}
        
        if not isinstance(metadata, dict):
            self._add_error(
                "METADATA", 
                "Metadata section must be an object"
            )
            return
        
        missing_fields = required_fields - set(metadata.keys())
        if missing_fields:
            missing_list = ', '.join(missing_fields)
            self._add_error(
                "METADATA", 
                f"Missing fields: {missing_list}"
            )
        
        # Version validation
        version = metadata.get("version_protocole")
        if version != self.REQUIRED_VERSION:
            self._add_error(
                "METADATA", 
                f"Incorrect protocol version: '{version}', "
                f"expected: '{self.REQUIRED_VERSION}'"
            )
        
        # Type validation
        for field in required_fields:
            if field in metadata and not isinstance(metadata[field], str):
                self._add_error(
                    "METADATA", 
                    f"Field '{field}' must be a string"
                )
    
    def _validate_milestones(self, milestones: List[Dict[str, Any]]) -> None:
        """
        Validates the milestones list.
        
        Checks each milestone for required fields, correct types, unique IDs,
        and valid configurations according to the protocol.
        
        Args:
            milestones (List[Dict[str, Any]]): List of milestone objects to 
                validate.
        """
        required_fields = {
            "id", "titre", "configuration", 
            "start_delay", "duration", "description"
        }
        
        for i, milestone in enumerate(milestones):
            location = f"milestones[{i}]"
            
            if not isinstance(milestone, dict):
                self._add_error(
                    "MILESTONE", 
                    "Each milestone must be an object", 
                    location
                )
                continue
            
            # Required fields check
            missing_fields = required_fields - set(milestone.keys())
            if missing_fields:
                missing_list = ', '.join(missing_fields)
                self._add_error(
                    "MILESTONE", 
                    f"Missing fields: {missing_list}", 
                    location
                )
                continue
            
            milestone_id = milestone["id"]
            
            # Unique ID validation
            if not isinstance(milestone_id, str) or not milestone_id:
                self._add_error(
                    "MILESTONE", 
                    "ID must be a non-empty string", 
                    location
                )
                continue
                
            if milestone_id in self.milestones:
                self._add_error(
                    "MILESTONE", 
                    f"Duplicate ID: '{milestone_id}'", 
                    location
                )
                continue
            
            # Type validation
            if not isinstance(milestone["titre"], str):
                self._add_error(
                    "MILESTONE", 
                    "Title must be a string", 
                    location
                )
            
            config = milestone["configuration"]
            if config not in self.VALID_MILESTONE_CONFIGS:
                self._add_error(
                    "MILESTONE", 
                    f"Invalid configuration: '{config}'", 
                    location
                )
            
            start_delay = milestone["start_delay"]
            if not isinstance(start_delay, int) or start_delay < 0:
                self._add_error(
                    "MILESTONE", 
                    "start_delay must be an integer >= 0", 
                    location
                )
            
            duration = milestone["duration"]
            if not isinstance(duration, int) or duration <= 0:
                self._add_error(
                    "MILESTONE", 
                    "duration must be an integer > 0", 
                    location
                )
            
            if not isinstance(milestone["description"], str):
                self._add_error(
                    "MILESTONE", 
                    "Description must be a string", 
                    location
                )
            
            self.milestones[milestone_id] = milestone
    
    def _validate_epics(self, epics: List[Dict[str, Any]]) -> None:
        """
        Validates the epics list.
        
        Checks each epic for required fields, correct types, unique IDs,
        and valid configurations according to the protocol.
        
        Args:
            epics (List[Dict[str, Any]]): List of epic objects to validate.
        """
        required_fields = {
            "id", "parent_id", "titre", 
            "configuration", "label", "description"
        }
        
        for i, epic in enumerate(epics):
            location = f"epics[{i}]"
            
            if not isinstance(epic, dict):
                self._add_error(
                    "EPIC", 
                    "Each epic must be an object", 
                    location
                )
                continue
            
            # Required fields check
            missing_fields = required_fields - set(epic.keys())
            if missing_fields:
                missing_list = ', '.join(missing_fields)
                self._add_error(
                    "EPIC", 
                    f"Missing fields: {missing_list}", 
                    location
                )
                continue
            
            epic_id = epic["id"]
            
            # Unique ID validation
            if not isinstance(epic_id, str) or not epic_id:
                self._add_error(
                    "EPIC", 
                    "ID must be a non-empty string", 
                    location
                )
                continue
                
            if epic_id in self.epics:
                self._add_error(
                    "EPIC", 
                    f"Duplicate ID: '{epic_id}'", 
                    location
                )
                continue
            
            # Type validation
            string_fields = ["titre", "label", "description"]
            for field in string_fields:
                if not isinstance(epic[field], str):
                    self._add_error(
                        "EPIC", 
                        f"Field '{field}' must be a string", 
                        location
                    )
            
            config = epic["configuration"]
            if config not in self.VALID_EPIC_CONFIGS:
                self._add_error(
                    "EPIC", 
                    f"Invalid configuration: '{config}'", 
                    location
                )
            
            self.epics[epic_id] = epic
    
    def _validate_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """
        Validates the tasks list.
        
        Checks each task for required fields, correct types, unique IDs,
        valid configurations, and proper dependency formatting according 
        to the protocol.
        
        Args:
            tasks (List[Dict[str, Any]]): List of task objects to validate.
        """
        required_fields = {
            "id", "parent_link", "titre", "configuration", 
            "estimate", "depends_on", "description"
        }
        
        for i, task in enumerate(tasks):
            location = f"tasks[{i}]"
            
            if not isinstance(task, dict):
                self._add_error(
                    "TASK", 
                    "Each task must be an object", 
                    location
                )
                continue
            
            # Required fields check
            missing_fields = required_fields - set(task.keys())
            if missing_fields:
                missing_list = ', '.join(missing_fields)
                self._add_error(
                    "TASK", 
                    f"Missing fields: {missing_list}", 
                    location
                )
                continue
            
            task_id = task["id"]
            
            # Unique ID validation
            if not isinstance(task_id, str) or not task_id:
                self._add_error(
                    "TASK", 
                    "ID must be a non-empty string", 
                    location
                )
                continue
                
            if task_id in self.tasks:
                self._add_error(
                    "TASK", 
                    f"Duplicate ID: '{task_id}'", 
                    location
                )
                continue
            
            # Type validation
            string_fields = ["titre", "description"]
            for field in string_fields:
                if not isinstance(task[field], str):
                    self._add_error(
                        "TASK", 
                        f"Field '{field}' must be a string", 
                        location
                    )
            
            config = task["configuration"]
            if config not in self.VALID_TASK_CONFIGS:
                self._add_error(
                    "TASK", 
                    f"Invalid configuration: '{config}'", 
                    location
                )
            
            estimate = task["estimate"]
            if not isinstance(estimate, (int, float)) or estimate <= 0:
                self._add_error(
                    "TASK", 
                    "estimate must be a number > 0", 
                    location
                )
            
            # depends_on validation
            depends_on = task["depends_on"]
            if not isinstance(depends_on, list):
                self._add_error(
                    "TASK", 
                    "depends_on must be an array", 
                    location
                )
            else:
                for dep_id in depends_on:
                    if not isinstance(dep_id, str):
                        self._add_error(
                            "TASK", 
                            "Dependencies must be strings", 
                            location
                        )
            
            # assignee validation (optional)
            if "assignee" in task and not isinstance(task["assignee"], str):
                self._add_error(
                    "TASK", 
                    "assignee must be a string", 
                    location
                )
            
            self.tasks[task_id] = task
    
    def _validate_normative_rules(self) -> None:
        """
        Validates the normative rules of the protocol.
        
        Performs cross-reference validation between project elements to ensure
        tutelle rules, dependency consistency, and temporal agnosticism are
        respected.
        """
        self._validate_tutelle_rules()
        self._validate_dependencies()
        self._validate_no_absolute_dates()
    
    def _validate_tutelle_rules(self) -> None:
        """
        Validates the tutelle (guardianship) rule.
        
        Ensures that all epics reference existing milestones as parents and
        all tasks reference existing milestones or epics as parents.
        """
        # Epic parent_id validation
        for epic_id, epic in self.epics.items():
            parent_id = epic["parent_id"]
            if parent_id not in self.milestones:
                self._add_error(
                    "TUTELLE", 
                    f"Epic '{epic_id}' references non-existent "
                    f"milestone: '{parent_id}'"
                )
        
        # Task parent_link validation
        for task_id, task in self.tasks.items():
            parent_link = task["parent_link"]
            valid_parents = set(self.milestones.keys()) | set(self.epics.keys())
            if parent_link not in valid_parents:
                self._add_error(
                    "TUTELLE", 
                    f"Task '{task_id}' references non-existent "
                    f"parent: '{parent_link}'"
                )
    
    def _validate_dependencies(self) -> None:
        """
        Validates consistency of task dependencies.
        
        Ensures that all task dependencies reference existing tasks and
        prevents obvious circular dependencies (self-references).
        """
        for task_id, task in self.tasks.items():
            depends_on = task["depends_on"]
            for dep_id in depends_on:
                if dep_id not in self.tasks:
                    self._add_error(
                        "DEPENDENCY", 
                        f"Task '{task_id}' depends on non-existent "
                        f"task: '{dep_id}'"
                    )
                
                # Cycle check (simplified)
                if dep_id == task_id:
                    self._add_error(
                        "DEPENDENCY", 
                        f"Task '{task_id}' cannot depend on itself"
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


def validate_project_file(file_path: Union[str, Path]) -> None:
    """
    Utility function to validate a project file and display results.
    
    This is a convenience function that creates a validator, runs validation
    on the specified file, and prints a formatted report of the results.
    
    Args:
        file_path (Union[str, Path]): Path to the JSON file to validate.
        
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
