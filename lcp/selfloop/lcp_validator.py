# lcp_validator.py
"""
LCP Response Validator
Version: 1.0

Validiert, ob eine LLM-Antwort dem Sheratan LCP entspricht.
- Ein einziges JSON-Objekt
- Felder: decision, actions[, explanation]
- actions: Liste von Objekten mit mindestens "kind"
- Maximal 3 Actions
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple


class LCPValidationError(Exception):
    """Fehler, wenn eine LCP-Response die Spezifikation verletzt."""


def strip_whitespace(text: str) -> str:
    return text.strip() if text is not None else ""


def parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Parst einen String als JSON-Objekt und stellt sicher,
    dass kein extrahierter Text vor/nach dem JSON existiert.
    """
    stripped = strip_whitespace(text)
    if not stripped:
        raise LCPValidationError("Empty response, expected JSON.")

    if not stripped.startswith("{") or not stripped.endswith("}"):
        # Beispiel: Text vor oder nach JSON
        raise LCPValidationError("Response must be a single JSON object, no text around it.")

    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise LCPValidationError(f"Invalid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise LCPValidationError("Top-level JSON must be an object.")
    return obj


def validate_decision(decision: Any) -> None:
    if not isinstance(decision, dict):
        raise LCPValidationError("`decision` must be an object.")
    # Allow legacy `kind` or newer `action_type` as the decision type field.
    if "kind" in decision:
        kind = decision["kind"]
    elif "action_type" in decision:
        kind = decision["action_type"]
    else:
        raise LCPValidationError("Either `decision.kind` or `decision.action_type` is required.")
    if not isinstance(kind, str):
        raise LCPValidationError("Decision type must be a string.")
    if not kind:
        raise LCPValidationError("Decision type must not be empty.")

def validate_action(action: Any) -> None:
    if not isinstance(action, dict):
        raise LCPValidationError("Each action must be an object.")
    if "kind" not in action:
        raise LCPValidationError("Each action must contain `kind`.")
    if not isinstance(action["kind"], str):
        raise LCPValidationError("`action.kind` must be a string.")
    if not action["kind"]:
        raise LCPValidationError("`action.kind` must not be empty.")


def validate_actions(actions: Any) -> None:
    if not isinstance(actions, list):
        raise LCPValidationError("`actions` must be a list.")
    if len(actions) > 3:
        raise LCPValidationError("`actions` list must not contain more than 3 items.")
    for action in actions:
        validate_action(action)


def validate_explanation(explanation: Any) -> None:
    if explanation is None:
        return
    if not isinstance(explanation, str):
        raise LCPValidationError("`explanation` must be a string if present.")


def is_valid_lcp_response(text: str) -> Tuple[bool, str]:
    """
    Prüft, ob ein Response-Text LCP-konform ist.

    Returns:
        (True, "") wenn gültig, sonst (False, Fehlerbeschreibung).
    """
    try:
        obj = parse_json_strict(text)

        if "decision" not in obj:
            raise LCPValidationError("Missing `decision` field.")
        if "actions" not in obj:
            raise LCPValidationError("Missing `actions` field.")

        validate_decision(obj["decision"])
        validate_actions(obj["actions"])
        validate_explanation(obj.get("explanation"))

        return True, ""
    except LCPValidationError as e:
        return False, str(e)
