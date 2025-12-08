# tests/test_storage_basic.py

"""
Basic tests for Storage Module.
"""

import pytest
from pathlib import Path
import shutil
from datetime import datetime

from sheratan_core_v2 import storage, models


# Test data directory
TEST_DATA_DIR = Path("test_data_storage")


def setup_module(module):
    """Setup test environment."""
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    TEST_DATA_DIR.mkdir()
    
    # Override storage paths
    storage.DATA_DIR = TEST_DATA_DIR
    storage.MISSIONS_FILE = TEST_DATA_DIR / "missions.jsonl"
    storage.TASKS_FILE = TEST_DATA_DIR / "tasks.jsonl"
    storage.JOBS_FILE = TEST_DATA_DIR / "jobs.jsonl"


def teardown_module(module):
    """Cleanup test environment."""
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)


class TestMissionCRUD:
    """Test Mission CRUD operations."""
    
    def test_create_and_get_mission(self):
        mission = models.Mission(
            id="m1",
            title="Test Mission",
            description="Test description",
            metadata={"key": "value"},
            tags=["test"],
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
        storage.create_mission(mission)
        loaded = storage.get_mission("m1")
        
        assert loaded is not None
        assert loaded.id == "m1"
        assert loaded.title == "Test Mission"
        assert loaded.metadata["key"] == "value"
    
    def test_list_missions(self):
        missions = storage.list_missions()
        assert len(missions) >= 1
        assert any(m.id == "m1" for m in missions)
    
    def test_update_mission(self):
        mission = storage.get_mission("m1")
        mission.title = "Updated Title"
        storage.update_mission(mission)
        
        loaded = storage.get_mission("m1")
        assert loaded.title == "Updated Title"
    
    def test_get_nonexistent_mission(self):
        result = storage.get_mission("nonexistent")
        assert result is None


class TestTaskCRUD:
    """Test Task CRUD operations."""
    
    def test_create_and_get_task(self):
        task = models.Task(
            id="t1",
            mission_id="m1",
            name="test_task",
            description="Test task",
            kind="llm_call",
            params={"key": "value"},
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
        storage.create_task(task)
        loaded = storage.get_task("t1")
        
        assert loaded is not None
        assert loaded.id == "t1"
        assert loaded.name == "test_task"
        assert loaded.kind == "llm_call"
    
    def test_find_task_by_name(self):
        task = storage.find_task_by_name("m1", "test_task")
        assert task is not None
        assert task.id == "t1"
    
    def test_find_task_by_name_nonexistent(self):
        task = storage.find_task_by_name("m1", "nonexistent")
        assert task is None
    
    def test_update_task(self):
        task = storage.get_task("t1")
        task.description = "Updated description"
        storage.update_task(task)
        
        loaded = storage.get_task("t1")
        assert loaded.description == "Updated description"


class TestJobCRUD:
    """Test Job CRUD operations."""
    
    def test_create_and_get_job(self):
        ts = datetime.utcnow().isoformat() + "Z"
        job = models.Job(
            id="j1",
            task_id="t1",
            payload={"file": "test.py"},
            status="pending",
            result=None,
            created_at=ts,
            updated_at=ts
        )
        
        storage.create_job(job)
        loaded = storage.get_job("j1")
        
        assert loaded is not None
        assert loaded.id == "j1"
        assert loaded.status == "pending"
        assert loaded.payload["file"] == "test.py"
    
    def test_update_job(self):
        job = storage.get_job("j1")
        job.status = "completed"
        job.result = {"ok": True}
        job.updated_at = datetime.utcnow().isoformat() + "Z"
        storage.update_job(job)
        
        loaded = storage.get_job("j1")
        assert loaded.status == "completed"
        assert loaded.result["ok"] is True
    
    def test_list_jobs(self):
        jobs = storage.list_jobs()
        assert len(jobs) >= 1
        assert any(j.id == "j1" for j in jobs)


class TestFileLocking:
    """Test file locking mechanism."""
    
    def test_concurrent_mission_creation(self):
        """Test that file locking prevents race conditions."""
        import concurrent.futures
        
        def create_mission_concurrent(i):
            mission = models.Mission(
                id=f"concurrent_{i}",
                title=f"Concurrent {i}",
                description="",
                metadata={},
                tags=[],
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            storage.create_mission(mission)
        
        # Create 10 missions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_mission_concurrent, i) for i in range(10)]
            concurrent.futures.wait(futures)
        
        # All 10 should be created
        missions = storage.list_missions()
        concurrent_missions = [m for m in missions if m.id.startswith("concurrent_")]
        assert len(concurrent_missions) == 10
