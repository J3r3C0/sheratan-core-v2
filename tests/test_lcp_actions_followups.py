# tests/test_lcp_actions_followups.py

"""
Functional tests for LCP Action Interpreter.
Tests automatic follow-up job creation.
"""

import pytest
from pathlib import Path
import shutil
import json
from datetime import datetime

from sheratan_core_v2 import storage, models
from sheratan_core_v2.webrelay_bridge import WebRelayBridge, WebRelaySettings
from sheratan_core_v2.lcp_actions import LCPActionInterpreter


# Test directories
TEST_BASE = Path("test_data_lcp_actions")
TEST_DATA = TEST_BASE / "data"
TEST_OUT = TEST_BASE / "webrelay_out"
TEST_IN = TEST_BASE / "webrelay_in"


def setup_module(module):
    """Setup test environment."""
    if TEST_BASE.exists():
        shutil.rmtree(TEST_BASE)
    TEST_BASE.mkdir()
    TEST_DATA.mkdir()
    TEST_OUT.mkdir()
    TEST_IN.mkdir()
    
    # Override storage
    storage.DATA_DIR = TEST_DATA
    storage.MISSIONS_FILE = TEST_DATA / "missions.jsonl"
    storage.TASKS_FILE = TEST_DATA / "tasks.jsonl"
    storage.JOBS_FILE = TEST_DATA / "jobs.jsonl"
    
    # Create mission with all standard tasks
    mission = models.Mission(
        id="m_auto",
        title="Autonomous Code Analyst",
        description="Test mission",
        metadata={"project_root": "./project"},
        tags=["autonomous"],
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_mission(mission)
    
    # Task 1: project_discovery
    t1 = models.Task(
        id="t_discovery",
        mission_id="m_auto",
        name="project_discovery",
        description="List files",
        kind="list_files",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(t1)
    
    # Task 2: analyze_file
    t2 = models.Task(
        id="t_analyze",
        mission_id="m_auto",
        name="analyze_file",
        description="Analyze file",
        kind="llm_call",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(t2)
    
    # Task 3: write_python_module
    t3 = models.Task(
        id="t_write",
        mission_id="m_auto",
        name="write_python_module",
        description="Write module",
        kind="code_task",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(t3)
    
    # Task 4: update_existing_file
    t4 = models.Task(
        id="t_update",
        mission_id="m_auto",
        name="update_existing_file",
        description="Update file",
        kind="code_task",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(t4)
    
    # Setup bridge and interpreter
    settings = WebRelaySettings(
        relay_out_dir=TEST_OUT,
        relay_in_dir=TEST_IN,
        session_prefix="test"
    )
    bridge = WebRelayBridge(settings)
    module.interpreter = LCPActionInterpreter(bridge=bridge)


def teardown_module(module):
    """Cleanup."""
    if TEST_BASE.exists():
        shutil.rmtree(TEST_BASE)


class TestListFilesAction:
    """Test list_files_result action handling."""
    
    def test_creates_analyze_jobs_for_files(self):
        """Test that list_files_result creates analyze_file jobs."""
        # Create discovery job
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_disc",
            task_id="t_discovery",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "list_files_result",
                "files": ["main.py", "utils/helpers.py", "README.md"]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        # Process result
        new_jobs = interpreter.handle_job_result(job)
        
        # Should create 3 analyze jobs
        assert len(new_jobs) == 3
        
        # All should be analyze_file tasks
        for new_job in new_jobs:
            task = storage.get_task(new_job.task_id)
            assert task.name == "analyze_file"
        
        # Check payloads
        files = [j.payload["file"] for j in new_jobs]
        assert "main.py" in files
        assert "utils/helpers.py" in files
        assert "README.md" in files
    
    def test_dispatches_new_jobs_automatically(self):
        """Test that new jobs are dispatched to worker."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_disc2",
            task_id="t_discovery",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "list_files_result",
                "files": ["test.py"]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        
        # Job file should exist in webrelay_out
        job_file = TEST_OUT / f"{new_jobs[0].id}.job.json"
        assert job_file.exists()
    
    def test_empty_files_list_creates_no_jobs(self):
        """Test that empty files list doesn't create jobs."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_disc3",
            task_id="t_discovery",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "list_files_result",
                "files": []
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        assert len(new_jobs) == 0


class TestCreateFollowupJobsAction:
    """Test create_followup_jobs action handling."""
    
    def test_creates_multiple_job_types(self):
        """Test creating multiple different job types."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_followup",
            task_id="t_analyze",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "create_followup_jobs",
                "new_jobs": [
                    {
                        "task": "write_python_module",
                        "params": {
                            "target_file": "new_module.py",
                            "instruction": "Create helper module"
                        }
                    },
                    {
                        "task": "update_existing_file",
                        "params": {
                            "file": "main.py",
                            "modification": "Add async support"
                        }
                    }
                ]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        
        assert len(new_jobs) == 2
        
        # Check task types
        tasks = [storage.get_task(j.task_id) for j in new_jobs]
        task_names = [t.name for t in tasks]
        
        assert "write_python_module" in task_names
        assert "update_existing_file" in task_names
    
    def test_preserves_job_params(self):
        """Test that job params are preserved."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_followup2",
            task_id="t_analyze",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "create_followup_jobs",
                "new_jobs": [
                    {
                        "task": "write_python_module",
                        "params": {"key": "value", "num": 42}
                    }
                ]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        
        assert new_jobs[0].payload["key"] == "value"
        assert new_jobs[0].payload["num"] == 42
    
    def test_unknown_task_name_skips_job(self):
        """Test that unknown task names are skipped."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_followup3",
            task_id="t_analyze",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "create_followup_jobs",
                "new_jobs": [
                    {"task": "nonexistent_task", "params": {}},
                    {"task": "write_python_module", "params": {}}
                ]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        
        # Only 1 job created (the valid one)
        assert len(new_jobs) == 1


class TestAnalysisResultAction:
    """Test analysis_result action (no automatic follow-ups)."""
    
    def test_no_followups_created(self):
        """Test that analysis_result doesn't create follow-ups."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_analysis",
            task_id="t_analyze",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "analysis_result",
                "target_file": "main.py",
                "summary": "Main entry point",
                "issues": ["unused import"],
                "recommendations": ["add type hints"]
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        
        # No follow-ups
        assert len(new_jobs) == 0
        
        # But result is stored
        loaded = storage.get_job("j_analysis")
        assert loaded.result["target_file"] == "main.py"


class TestErrorHandling:
    """Test error handling in LCP interpreter."""
    
    def test_error_result_creates_no_followups(self):
        """Test that error results don't create follow-ups."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_error",
            task_id="t_analyze",
            payload={},
            status="failed",
            result={
                "ok": False,
                "error": "Worker error"
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        assert len(new_jobs) == 0
    
    def test_unknown_action_creates_no_followups(self):
        """Test that unknown actions are ignored."""
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j_unknown",
            task_id="t_analyze",
            payload={},
            status="completed",
            result={
                "ok": True,
                "action": "unknown_action",
                "data": {}
            },
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job)
        
        new_jobs = interpreter.handle_job_result(job)
        assert len(new_jobs) == 0
