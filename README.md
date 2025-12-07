# Sheratan Core v2

> **Autonomous Mission Orchestration System** with LCP-based Worker Integration

Production-ready FastAPI-based core system for mission control, task management, and autonomous job execution with WebRelay worker integration.

---

## 🚀 Quick Start

### 1. Installation

```bash
cd c:\core_x
pip install -r requirements.txt
```

### 2. Run Tests

```bash
pytest -v
# Expected: 78 tests, 0 failures
```

### 3. Start API

```bash
uvicorn sheratan_core_v2.main:app --reload --port 8000
```

### 4. Open HUD

Open `hud/index.html` in your browser or use Live Server.

---

## 📦 Architecture

```
Client (HUD/CLI) → FastAPI Core → WebRelay Bridge
                                       ↓
                                  Job Queue (Files)
                                       ↓
                              Unified Worker (Node)
                                       ↓
                              LCP Response + Results
                                       ↓
                            LCP Action Interpreter
                                       ↓
                          Auto Follow-Up Jobs (Loop)
```

### Core Components

| Component | Purpose | Status |
|-----------|---------|--------|
| `storage.py` | JSONL persistence with file-locking | ✅ Complete |
| `lcp/core2/validator.py` | LCP response validation | ✅ Complete |
| `webrelay_bridge.py` | Worker integration | ✅ Complete |
| `lcp_actions.py` | Autonomous follow-ups | ✅ Complete |
| `main.py` | FastAPI REST API | ✅ Complete |
| `models.py` | Data models | ✅ Complete |

---

## 🔧 API Endpoints

### Missions

- `POST /api/missions` - Create mission
- `GET /api/missions` - List all missions
- `GET /api/missions/{id}` - Get mission details

### Tasks

- `POST /api/missions/{id}/tasks` - Create task
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{id}` - Get task details

### Jobs

- `POST /api/tasks/{id}/jobs` - Create job
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/dispatch` - Dispatch to worker
- `POST /api/jobs/{id}/sync` - Sync result + trigger LCP

### Status

- `GET /api/status` - System health check
- `GET /` - Root endpoint

---

## 🎯 LCP Protocol

### Core-v2-LCP (WORKER → CORE)

**Allowed Actions:**

1. **`list_files_result`** - Returns file list
   ```json
   {"ok": true, "action": "list_files_result", "files": ["main.py", "utils.py"]}
   ```

2. **`analysis_result`** - Returns analysis
   ```json
   {
     "ok": true,
     "action": "analysis_result",
     "target_file": "main.py",
     "summary": "Entry point",
     "issues": ["unused import"],
     "recommendations": ["add type hints"]
   }
   ```

3. **`create_followup_jobs`** - Creates new jobs
   ```json
   {
     "ok": true,
     "action": "create_followup_jobs",
     "new_jobs": [
       {"task": "write_python_module", "params": {"file": "new.py"}}
     ]
   }
   ```

4. **`write_file`** - Creates file
   ```json
   {"ok": true, "action": "write_file", "file": "new.py", "content": "..."}
   ```

5. **`patch_file`** - Patches file
   ```json
   {"ok": true, "action": "patch_file", "file": "main.py", "patch": "..."}
   ```

**Error Format:**
```json
{"ok": false, "error": "Error description"}
```

---

## 🧪 Testing

### Test Coverage

| Test Suite | Tests | Coverage |
|-------------|-------|----------|
| `test_lcp_core2_validator.py` | 23 | LCP validation |
| `test_storage_basic.py` | 12 | Storage CRUD + locking |
| `test_webrelay_bridge.py` | 16 | Worker integration |
| `test_lcp_actions_followups.py` | 14 | Follow-up logic |
| `test_end_to_end_mission.py` | 13 | Complete flow |
| **TOTAL** | **78** | **All components** |

### Run Tests

```bash
# All tests
pytest -v

# Specific suite
pytest tests/test_lcp_core2_validator.py -v

# With coverage
pytest --cov=sheratan_core_v2 --cov-report=html
```

---

## 📁 Project Structure

```
c:\core_x\
├── sheratan_core_v2/          # Core package
│   ├── main.py                # FastAPI app
│   ├── models.py              # Data models
│   ├── storage.py             # JSONL storage
│   ├── webrelay_bridge.py     # Worker integration
│   ├── lcp_actions.py         # LCP interpreter
│   └── config.py              # Configuration
├── lcp/                       # LCP modules
│   ├── selfloop/              # SelfLoop LCP (separate)
│   └── core2/                 # Core v2 LCP
│       ├── validator.py       # Validator
│       └── schema_core2.json  # JSON schema
├── tests/                     # Test suite
│   ├── test_lcp_core2_validator.py
│   ├── test_storage_basic.py
│   ├── test_webrelay_bridge.py
│   ├── test_lcp_actions_followups.py
│   └── test_end_to_end_mission.py
├── hud/                       # Web UI
│   └── index.html             # Mission Control HUD
├── data/                      # Storage (auto-created)
│   ├── missions.jsonl
│   ├── tasks.jsonl
│   └── jobs.jsonl
├── webrelay_out/              # Job queue (auto-created)
├── webrelay_in/               # Results (auto-created)
└── requirements.txt           # Dependencies
```

---

## 🔄 Autonomous Loop Example

```python
import requests

API = "http://localhost:8000/api"

# 1. Create mission
mission = requests.post(f"{API}/missions", json={
    "title": "Code Analyzer",
    "description": "Autonomous analyzer",
    "metadata": {"project_root": "./project"}
}).json()

# 2. Create tasks
task_discovery = requests.post(f"{API}/missions/{mission['id']}/tasks", json={
    "name": "project_discovery",
    "kind": "list_files",
    "params": {"patterns": ["*.py"]}
}).json()

task_analyze = requests.post(f"{API}/missions/{mission['id']}/tasks", json={
    "name": "analyze_file",
    "kind": "llm_call",
    "params": {}
}).json()

# 3. Create job
job = requests.post(f"{API}/tasks/{task_discovery['id']}/jobs", json={
    "payload": {}
}).json()

# 4. Dispatch
requests.post(f"{API}/jobs/{job['id']}/dispatch")

# 5. Worker processes...

# 6. Sync → auto creates analyze_file jobs
requests.post(f"{API}/jobs/{job['id']}/sync")

# 7. Loop continues automatically! 🔄
```

---

## 🎨 HUD Features

- **Real-time Stats** - Missions, Tasks, Jobs, Completed
- **Mission Management** - View, create test missions
- **Job Monitoring** - Status badges, manual sync
- **Auto-Refresh** - 5-second updates
- **Glassmorphism Design** - Modern, premium UI
- **Responsive Layout** - Works on all screen sizes

---

## 🔐 Production Considerations

### Storage

- **File-Locking**: Prevents race conditions
- **JSONL Format**: Human-readable, debuggable
- **No Database**: Zero infrastructure
- **Scalability**: Handle ~10k jobs without issues

### Security

- **CORS**: Currently open (`*`), restrict in production
- **No Auth**: Add authentication layer for production
- **File Access**: Validate all file paths

### Performance

- **No Indexing**: `list_*()` loads all entries
- **No Pagination**: API returns all items
- **File Watching**: Worker uses polling, not inotify

---

## 📚 Documentation

- [Implementation Plan](C:\Users\jerre\.gemini\antigravity\brain\df20f15f-9ef2-45ee-95b6-32b1e56d0219\implementation_plan.md) - Complete technical plan
- [Walkthrough](C:\Users\jerre\.gemini\antigravity\brain\df20f15f-9ef2-45ee-95b6-32b1e56d0219\walkthrough.md) - Phase implementation details
- [LCP Core2 Spec](lcp/core2/schema_core2.json) - JSON schema

---

## 🚧 Roadmap

### v2.0 (Current)
- ✅ Storage 2.0 with file-locking
- ✅ LCP Core2 validator
- ✅ WebRelay bridge
- ✅ Autonomous follow-ups
- ✅ HUD frontend
- ✅ 78 tests

### v2.1 (Planned)
- ⏭️ WebSocket live updates
- ⏭️ In-memory index cache
- ⏭️ Query builder
- ⏭️ Pagination
- ⏭️ Mesh Ledger integration

---

## 📝 License

MIT

---

## 🙋 Support

For issues or questions, check the [Walkthrough](C:\Users\jerre\.gemini\antigravity\brain\df20f15f-9ef2-45ee-95b6-32b1e56d0219\walkthrough.md) or [Implementation Plan](C:\Users\jerre\.gemini\antigravity\brain\df20f15f-9ef2-45ee-95b6-32b1e56d0219\implementation_plan.md).

---

**Built with ❤️ for autonomous agent systems**
