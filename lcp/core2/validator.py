# lcp/core2/validator.py

"""
Core v2 LCP Validator

Validates LCP responses from the Unified Worker to Core v2.
This is COMPLETELY SEPARATE from SelfLoop LCP!

Allowed actions:
- list_files_result
- analysis_result
- create_followup_jobs
- write_file
- patch_file

Error format:
{"ok": false, "error": "..."}
"""

from __future__ import annotations
import json
from typing import Any, Dict, Tuple


class Core2LCPValidationError(Exception):
    """Raised when Core v2 LCP validation fails."""
    pass


ALLOWED_ACTIONS = {
    "list_files_result",
    "analysis_result",
    "create_followup_jobs",
    "write_file",
    "patch_file",
}


def parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Parse text as strict JSON object.
    
    Raises:
        Core2LCPValidationError: If text is not valid JSON or not an object
    """
    txt = text.strip()
    
    if not txt:
        raise Core2LCPValidationError("Empty response, expected JSON object")
    
    if not (txt.startswith("{") and txt.endswith("}")):
        raise Core2LCPValidationError("Response must be a single JSON object (no extra text)")
    
    try:
        obj = json.loads(txt)
    except json.JSONDecodeError as e:
        raise Core2LCPValidationError(f"Invalid JSON: {e}") from e
    
    if not isinstance(obj, dict):
        raise Core2LCPValidationError("Top-level JSON must be an object, not array or primitive")
    
    return obj


def _validate_common(obj: Dict[str, Any]) -> None:
    """
    Validate common fields that all LCP responses must have.
    
    Raises:
        Core2LCPValidationError: If validation fails
    """
    # Check 'ok' field
    if "ok" not in obj:
        raise Core2LCPValidationError("Missing required field 'ok'")
    
    if not isinstance(obj["ok"], bool):
        raise Core2LCPValidationError("Field 'ok' must be boolean, got: " + str(type(obj["ok"])))
    
    # If error response, check error field
    if obj["ok"] is False:
        if "error" not in obj:
            raise Core2LCPValidationError("Error responses (ok=false) must contain 'error' field")
        if not isinstance(obj["error"], str):
            raise Core2LCPValidationError("Field 'error' must be string")
        # Don't validate further for error responses
        return
    
    # For success responses (ok=true), check action
    if "action" not in obj:
        raise Core2LCPValidationError("Success responses (ok=true) must contain 'action' field")
    
    if not isinstance(obj["action"], str):
        raise Core2LCPValidationError("Field 'action' must be string")
    
    if obj["action"] not in ALLOWED_ACTIONS:
        raise Core2LCPValidationError(
            f"Unsupported action: {obj['action']}. "
            f"Allowed: {', '.join(ALLOWED_ACTIONS)}"
        )


def _validate_action_specific(obj: Dict[str, Any]) -> None:
    """
    Validate action-specific fields.
    
    Raises:
        Core2LCPValidationError: If validation fails
    """
    action = obj.get("action")
    
    # list_files_result: must have 'files' array of strings
    if action == "list_files_result":
        files = obj.get("files")
        if not isinstance(files, list):
            raise Core2LCPValidationError("'files' must be an array for list_files_result")
        if not all(isinstance(f, str) for f in files):
            raise Core2LCPValidationError("'files' must be an array of strings")
    
    # analysis_result: must have target_file, optional summary/issues/recommendations
    elif action == "analysis_result":
        if not isinstance(obj.get("target_file"), str):
            raise Core2LCPValidationError("'target_file' must be string for analysis_result")
        
        if "summary" in obj and not isinstance(obj["summary"], str):
            raise Core2LCPValidationError("'summary' must be string if present")
        
        for key in ("issues", "recommendations"):
            if key in obj:
                if not isinstance(obj[key], list):
                    raise Core2LCPValidationError(f"'{key}' must be array if present")
                if not all(isinstance(item, str) for item in obj[key]):
                    raise Core2LCPValidationError(f"'{key}' must be array of strings if present")
    
    # create_followup_jobs: must have 'new_jobs' array
    elif action == "create_followup_jobs":
        new_jobs = obj.get("new_jobs")
        if not isinstance(new_jobs, list):
            raise Core2LCPValidationError("'new_jobs' must be array for create_followup_jobs")
        
        for i, spec in enumerate(new_jobs):
            if not isinstance(spec, dict):
                raise Core2LCPValidationError(f"'new_jobs[{i}]' must be an object")
            
            if not isinstance(spec.get("task"), str):
                raise Core2LCPValidationError(f"'new_jobs[{i}].task' must be string")
            
            if "params" in spec and not isinstance(spec["params"], dict):
                raise Core2LCPValidationError(f"'new_jobs[{i}].params' must be object if present")
    
    # write_file / patch_file: must have 'file' field
    elif action in ("write_file", "patch_file"):
        if not isinstance(obj.get("file"), str):
            raise Core2LCPValidationError(f"'file' must be string for {action}")
        
        if action == "write_file":
            if not isinstance(obj.get("content"), str):
                raise Core2LCPValidationError("'content' must be string for write_file")
        
        if action == "patch_file":
            if not isinstance(obj.get("patch"), str):
                raise Core2LCPValidationError("'patch' must be string for patch_file")


def is_valid_core2_lcp_response(text: str) -> Tuple[bool, str]:
    """
    Validate a Core v2 LCP response.
    
    Args:
        text: Raw response text from Worker
    
    Returns:
        (is_valid, error_message)
        If valid: (True, "")
        If invalid: (False, "error description")
    
    Example:
        >>> is_valid_core2_lcp_response('{"ok": true, "action": "list_files_result", "files": []}')
        (True, '')
        
        >>> is_valid_core2_lcp_response('{"ok": false, "error": "Something went wrong"}')
        (True, '')
        
        >>> is_valid_core2_lcp_response('{"ok": true}')
        (False, "Success responses (ok=true) must contain 'action' field")
    """
    try:
        obj = parse_json_strict(text)
        _validate_common(obj)
        
        # Only validate action-specific fields for success responses
        if obj.get("ok") is True:
            _validate_action_specific(obj)
        
        return True, ""
    
    except Core2LCPValidationError as e:
        return False, str(e)
