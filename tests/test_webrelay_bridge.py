# tests/test_webrelay_bridge.py

"""
Integration tests for WebRelay Bridge.
"""

import pytest
from pathlib import Path
import shutil
import json
from datetime import datetime

from sheratan_core_v2 import storage, models
from sheratan_core_v2.webrelay_bridge import WebRelayBridge, WebRelaySettings


# Test directories
TEST_BASE = Path("test_data_bridge")
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
    
    # Override storage paths
    storage.DATA_DIR = TEST_DATA
    storage.MISSIONS_FILE = TEST_DATA / "missions.jsonl"
    storage.TASKS_FILE = TEST_DATA / "tasks.jsonl"
    storage.JOBS_FILE = TEST_DATA / "jobs.jsonl"
    
    # Create test data
    mission = models.Mission(
        id="m1",
        title="Test Mission",
        description="Test",
        metadata={"project_root": "./project"},
        tags=["test"],
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_mission(mission)
    
    task = models.Task(
        id="t1",
        mission_id="m1",
        name="list_files",
        description="List files",
        kind="list_files",
        params={"root": "./project"},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(task)
    
    ts = datetime.utcnow().isoformat() + "Z"
    job = models.Job(
        id="j1",
        task_id="t1",
        payload={"patterns": ["*.py"]},
        status="pending",
        result=None,
        created_at=ts,
        updated_at=ts
    )
    storage.create_job(job)
    
    # Setup bridge
    settings = WebRelaySettings(
        relay_out_dir=TEST_OUT,
        relay_in_dir=TEST_IN,
        session_prefix="test"
    )
    module.bridge = WebRelayBridge(settings)


def teardown_module(module):
    """Cleanup test environment."""
    if TEST_BASE.exists():
        shutil.rmtree(TEST_BASE)


class TestJobEnqueue:
    """Test job enqueuing to worker."""
    
    def test_enqueue_creates_file(self):
        """Test that enqueue_job creates a .job.json file."""
        job_file = bridge.enqueue_job("j1")
        
        assert job_file.exists()
        assert job_file.name == "j1.job.json"
    
    def test_enqueue_unified_job_format(self):
        """Test UnifiedJob format structure."""
        job_file = bridge.enqueue_job("j1")
        data = json.loads(job_file.read_text())
        
        # Check required fields
        assert "job_id" in data
        assert data["job_id"] == "j1"
        
        assert "kind" in data
        assert data["kind"] == "list_files"
        
        assert "session_id" in data
        assert data["session_id"] == "test_m1"
        
        assert "created_at" in data
        assert data["created_at"].endswith("Z")
        
        assert "payload" in data
        payload = data["payload"]
        
        assert payload["response_format"] == "lcp"
        assert "mission" in payload
        assert "task" in payload
        assert "params" in payload
    
    def test_enqueue_includes_mission_data(self):
        """Test that mission data is included."""
        job_file = bridge.enqueue_job("j1")
        data = json.loads(job_file.read_text())
        
        mission_data = data["payload"]["mission"]
        assert mission_data["id"] == "m1"
        assert mission_data["title"] == "Test Mission"
    
    def test_enqueue_includes_task_data(self):
        """Test that task data is included."""
        job_file = bridge.enqueue_job("j1")
        data = json.loads(job_file.read_text())
        
        task_data = data["payload"]["task"]
        assert task_data["id"] == "t1"
        assert task_data["kind"] == "list_files"
    
    def test_enqueue_nonexistent_job_raises(self):
        """Test that enqueuing nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="Job not found"):
            bridge.enqueue_job("nonexistent")


class TestResultSync:
    """Test result synchronization from worker."""
    
    def test_sync_no_result_returns_none(self):
        """Test that sync returns None if no result file exists."""
        result = bridge.try_sync_result("j1")
        assert result is None
    
    def test_sync_reads_result_and_updates_job(self):
        """Test that sync reads result and updates job."""
        # Create fake result
        result_file = TEST_IN / "j1.result.json"
        result_data = {
            "ok": True,
            "action": "list_files_result",
            "files": ["main.py", "test.py"]
        }
        result_file.write_text(json.dumps(result_data))
        
        # Sync
        job = bridge.try_sync_result("j1")
        
        assert job is not None
        assert job.id == "j1"
        assert job.status == "completed"
        assert job.result == result_data
        
        # Result file should be deleted
        assert not result_file.exists()
    
    def test_sync_error_result_marks_failed(self):
        """Test that error results mark job as failed."""
        # Create error result
        result_file = TEST_IN / "j1.result.json"
        result_data = {
            "ok": False,
            "error": "Something went wrong"
        }
        result_file.write_text(json.dumps(result_data))
        
        # Sync
        job = bridge.try_sync_result("j1")
        
        assert job.status == "failed"
        assert job.result["ok"] is False
    
    def test_sync_invalid_json_marks_failed(self):
        """Test that invalid JSON marks job as failed."""
        result_file = TEST_IN / "j1.result.json"
        result_file.write_text("not valid json")
        
        job = bridge.try_sync_result("j1")
        
        assert job.status == "failed"
        assert "invalid" in job.result["error"].lower()
    
    def test_sync_preserves_result_if_no_remove(self):
        """Test that result file is preserved if remove_after_read=False."""
        result_file = TEST_IN / "j1.result.json"
        result_data = {"ok": True, "action": "list_files_result", "files": []}
        result_file.write_text(json.dumps(result_data))
        
        bridge.try_sync_result("j1", remove_after_read=False)
        
        # File should still exist
        assert result_file.exists()
        
        # Cleanup
        result_file.unlink()


class TestEndToEndFlow:
    """Test complete enqueue → sync flow."""
    
    def test_complete_flow(self):
        """Test complete job lifecycle."""
        # 1. Create new job
        ts = datetime.utcnow().isoformat() + "Z"
        job2 = models.Job(
            id="j2",
            task_id="t1",
            payload={},
            status="pending",
            result=None,
            created_at=ts,
            updated_at=ts
        )
        storage.create_job(job2)
        
        # 2. Enqueue
        job_file = bridge.enqueue_job("j2")
        assert job_file.exists()
        
        # 3. Simulate worker processing
        result_file = TEST_IN / "j2.result.json"
        worker_result = {
            "ok": True,
            "action": "list_files_result",
            "files": ["a.py", "b.py", "c.py"]
        }
        result_file.write_text(json.dumps(worker_result))
        
        # 4. Sync
        synced_job = bridge.try_sync_result("j2")
        
        # 5. Verify
        assert synced_job.status == "completed"
        assert synced_job.result["files"] == ["a.py", "b.py", "c.py"]
        
        # 6. Verify persistence
        loaded_job = storage.get_job("j2")
        assert loaded_job.status == "completed"
        assert loaded_job.result["files"] == ["a.py", "b.py", "c.py"]
