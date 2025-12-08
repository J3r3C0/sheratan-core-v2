# tests/test_end_to_end_mission.py

"""
End-to-End test for complete mission lifecycle.

Tests the full autonomous loop:
Mission → Task → Job → Dispatch → Worker → Sync → LCP → Follow-Ups
"""

import pytest
from pathlib import Path
import shutil
import json
from datetime import datetime
from fastapi.testclient import TestClient

from sheratan_core_v2.main import app
from sheratan_core_v2 import storage


# Test directories
TEST_BASE = Path("test_data_e2e")
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
    
    # Create test client
    module.client = TestClient(app)


def teardown_module(module):
    """Cleanup."""
    if TEST_BASE.exists():
        shutil.rmtree(TEST_BASE)


class TestCompleteMissionFlow:
    """Test complete autonomous mission flow."""
    
    def test_create_mission_and_tasks(self):
        """Step 1: Create mission with all tasks."""
        # Create mission
        r = client.post("/api/missions", json={
            "title": "E2E Test Mission",
            "description": "Complete test",
            "metadata": {"project_root": "./project", "max_iterations": 10},
            "tags": ["e2e", "test"]
        })
        assert r.status_code == 200
        mission = r.json()
        mission_id = mission["id"]
        
        # Create project_discovery task
        r = client.post(f"/api/missions/{mission_id}/tasks", json={
            "name": "project_discovery",
            "description": "List files",
            "kind": "list_files",
            "params": {"root": "./project", "patterns": ["*.py"]}
        })
        assert r.status_code == 200
        task_discovery = r.json()
        
        # Create analyze_file task
        r = client.post(f"/api/missions/{mission_id}/tasks", json={
            "name": "analyze_file",
            "description": "Analyze file",
            "kind": "llm_call",
            "params": {}
        })
        assert r.status_code == 200
        task_analyze = r.json()
        
        # Store for next tests
        TestCompleteMissionFlow.mission_id = mission_id
        TestCompleteMissionFlow.task_discovery_id = task_discovery["id"]
        TestCompleteMissionFlow.task_analyze_id = task_analyze["id"]
    
    def test_create_and_dispatch_job(self):
        """Step 2: Create discovery job and dispatch."""
        # Create job
        r = client.post(
            f"/api/tasks/{TestCompleteMissionFlow.task_discovery_id}/jobs",
            json={"payload": {}}
        )
        assert r.status_code == 200
        job = r.json()
        job_id = job["id"]
        
        # Dispatch
        r = client.post(f"/api/jobs/{job_id}/dispatch")
        assert r.status_code == 200
        
        # Verify job file created
        job_file = TEST_OUT / f"{job_id}.job.json"
        assert job_file.exists()
        
        # Verify UnifiedJob format
        data = json.loads(job_file.read_text())
        assert data["kind"] == "list_files"
        assert data["payload"]["response_format"] == "lcp"
        
        TestCompleteMissionFlow.job_id = job_id
    
    def test_worker_processes_and_returns_result(self):
        """Step 3: Simulate worker processing."""
        # Simulate worker writing result
        result_file = TEST_IN / f"{TestCompleteMissionFlow.job_id}.result.json"
        worker_result = {
            "ok": True,
            "action": "list_files_result",
            "files": ["main.py", "utils.py", "test.py"]
        }
        result_file.write_text(json.dumps(worker_result))
        
        # Verify file created
        assert result_file.exists()
    
    def test_sync_creates_followup_jobs(self):
        """Step 4: Sync result and verify follow-up jobs."""
        # Sync
        r = client.post(f"/api/jobs/{TestCompleteMissionFlow.job_id}/sync")
        assert r.status_code == 200
        synced_job = r.json()
        
        # Job should be completed
        assert synced_job["status"] == "completed"
        assert synced_job["result"]["action"] == "list_files_result"
        
        # Check that follow-up jobs were created
        r = client.get("/api/jobs")
        assert r.status_code == 200
        jobs = r.json()
        
        # Should have original job + 3 analyze jobs
        assert len(jobs) >= 4
        
        # Find analyze jobs
        analyze_jobs = [j for j in jobs if j["id"] != TestCompleteMissionFlow.job_id]
        assert len(analyze_jobs) == 3
        
        # All should have analyze_file task
        for job in analyze_jobs:
            assert job["task_id"] == TestCompleteMissionFlow.task_analyze_id
        
        # Check payloads
        files_in_jobs = [j["payload"]["file"] for j in analyze_jobs]
        assert "main.py" in files_in_jobs
        assert "utils.py" in files_in_jobs
        assert "test.py" in files_in_jobs
    
    def test_followup_jobs_are_dispatched(self):
        """Step 5: Verify follow-up jobs are dispatched."""
        # Get all analyze jobs
        r = client.get("/api/jobs")
        jobs = r.json()
        analyze_jobs = [j for j in jobs if j["task_id"] == TestCompleteMissionFlow.task_analyze_id]
        
        # Each should have a .job.json file
        for job in analyze_jobs:
            job_file = TEST_OUT / f"{job['id']}.job.json"
            assert job_file.exists()


class TestAutonomousContinuation:
    """Test that loop can continue autonomously."""
    
    def test_analyze_job_creates_more_followups(self):
        """Test that analyze jobs can create code tasks."""
        # Get first analyze job
        r = client.get("/api/jobs")
        jobs = r.json()
        analyze_jobs = [j for j in jobs if j["task_id"] == TestCompleteMissionFlow.task_analyze_id]
        first_analyze = analyze_jobs[0]
        
        # Create write_python_module task first
        r = client.post(f"/api/missions/{TestCompleteMissionFlow.mission_id}/tasks", json={
            "name": "write_python_module",
            "description": "Write module",
            "kind": "code_task",
            "params": {}
        })
        write_task = r.json()
        
        # Simulate worker result with create_followup_jobs
        result_file = TEST_IN / f"{first_analyze['id']}.result.json"
        worker_result = {
            "ok": True,
            "action": "create_followup_jobs",
            "new_jobs": [
                {
                    "task": "write_python_module",
                    "params": {
                        "target_file": "new_module.py",
                        "instruction": "Create helper module"
                    }
                }
            ]
        }
        result_file.write_text(json.dumps(worker_result))
        
        # Sync
        r = client.post(f"/api/jobs/{first_analyze['id']}/sync")
        assert r.status_code == 200
        
        # Check new job was created
        r = client.get("/api/jobs")
        jobs = r.json()
        
        # Find write job
        write_jobs = [j for j in jobs if j["task_id"] == write_task["id"]]
        assert len(write_jobs) == 1
        
        # Verify params preserved
        assert write_jobs[0]["payload"]["target_file"] == "new_module.py"


class TestAPIEndpoints:
    """Test all API endpoints work correctly."""
    
    def test_list_missions(self):
        """Test GET /api/missions."""
        r = client.get("/api/missions")
        assert r.status_code == 200
        missions = r.json()
        assert len(missions) >= 1
    
    def test_get_mission(self):
        """Test GET /api/missions/{id}."""
        r = client.get(f"/api/missions/{TestCompleteMissionFlow.mission_id}")
        assert r.status_code == 200
        mission = r.json()
        assert mission["title"] == "E2E Test Mission"
    
    def test_list_tasks(self):
        """Test GET /api/tasks."""
        r = client.get("/api/tasks")
        assert r.status_code == 200
        tasks = r.json()
        assert len(tasks) >= 2
    
    def test_list_jobs(self):
        """Test GET /api/jobs."""
        r = client.get("/api/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) >= 1
    
    def test_status_endpoint(self):
        """Test GET /api/status."""
        r = client.get("/api/status")
        assert r.status_code == 200
        status = r.json()
        assert "status" in status
        assert status["status"] == "ok"
    
    def test_root_endpoint(self):
        """Test GET /."""
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "sheratan_core_v2" in data
