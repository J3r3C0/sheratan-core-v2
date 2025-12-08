# tests/test_lcp_core2_validator.py

"""
Tests for LCP Core2 Validator.
"""

import pytest
from lcp.core2.validator import is_valid_core2_lcp_response, Core2LCPValidationError


class TestValidResponses:
    """Test valid LCP responses."""
    
    def test_valid_list_files_result(self):
        text = '{"ok": true, "action": "list_files_result", "files": ["main.py", "utils/helpers.py"]}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
        assert err == ""
    
    def test_valid_empty_files_list(self):
        text = '{"ok": true, "action": "list_files_result", "files": []}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
    
    def test_valid_analysis_result(self):
        text = '''{
            "ok": true,
            "action": "analysis_result",
            "target_file": "main.py",
            "summary": "Main entry point",
            "issues": ["unused import"],
            "recommendations": ["add type hints"]
        }'''
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
    
    def test_valid_create_followup_jobs(self):
        text = '''{
            "ok": true,
            "action": "create_followup_jobs",
            "new_jobs": [
                {"task": "analyze_file", "params": {"file": "test.py"}},
                {"task": "write_python_module", "params": {}}
            ]
        }'''
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
    
    def test_valid_write_file(self):
        text = '{"ok": true, "action": "write_file", "file": "new.py", "content": "print(1)"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
    
    def test_valid_patch_file(self):
        text = '{"ok": true, "action": "patch_file", "file": "main.py", "patch": "diff..."}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
    
    def test_valid_error_response(self):
        text = '{"ok": false, "error": "Something went wrong"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is True
        assert err == ""


class TestInvalidResponses:
    """Test invalid LCP responses."""
    
    def test_invalid_missing_ok(self):
        text = '{"action": "list_files_result"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "ok" in err.lower()
    
    def test_invalid_ok_not_boolean(self):
        text = '{"ok": "true", "action": "list_files_result"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "boolean" in err.lower()
    
    def test_invalid_missing_action_on_success(self):
        text = '{"ok": true}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "action" in err.lower()
    
    def test_invalid_unsupported_action(self):
        text = '{"ok": true, "action": "invalid_action"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "unsupported" in err.lower() or "allowed" in err.lower()
    
    def test_invalid_error_missing_error_field(self):
        text = '{"ok": false}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "error" in err.lower()
    
    def test_invalid_empty_text(self):
        text = ''
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
    
    def test_invalid_not_json(self):
        text = 'this is not json'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
    
    def test_invalid_json_array(self):
        text = '[1, 2, 3]'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "object" in err.lower()


class TestActionSpecificValidation:
    """Test action-specific field validation."""
    
    def test_list_files_missing_files(self):
        text = '{"ok": true, "action": "list_files_result"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "files" in err.lower()
    
    def test_list_files_files_not_array(self):
        text = '{"ok": true, "action": "list_files_result", "files": "string"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
    
    def test_analysis_missing_target_file(self):
        text = '{"ok": true, "action": "analysis_result"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "target_file" in err.lower()
    
    def test_create_followup_missing_new_jobs(self):
        text = '{"ok": true, "action": "create_followup_jobs"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "new_jobs" in err.lower()
    
    def test_write_file_missing_content(self):
        text = '{"ok": true, "action": "write_file", "file": "test.py"}'
        ok, err = is_valid_core2_lcp_response(text)
        assert ok is False
        assert "content" in err.lower()
