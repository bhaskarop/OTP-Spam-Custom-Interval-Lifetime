# OTP Task API - Documentation

Complete API reference and AI agent implementation guide.

---

## Base URL

```
https://bhaskar-op-otp.onrender.com
```

---

## Authentication

All task endpoints require the `X-API-KEY` header.

**Header:**
```
X-API-KEY: your-api-key-here
```

**Public Endpoints (no auth required):**
- `GET /` - API documentation
- `GET /health` - Health check

**Protected Endpoints (require X-API-KEY):**
- All `/api/task/*` endpoints

**Error Responses:**

Missing API key (401):
```json
{
  "error": "Missing API key",
  "message": "X-API-KEY header is required"
}
```

Invalid API key (403):
```json
{
  "error": "Invalid API key",
  "message": "The provided API key is not valid"
}
```

## Endpoints

### 1. Start Task

Creates and starts a new background OTP task.

```http
POST /api/task/start
Content-Type: application/json
```

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `num` | string | ✅ Yes | - | 10-digit Indian phone number |
| `int` | integer | No | 60 | Interval between requests (1-3600 seconds) |

**Example Request:**

```bash
curl -X POST http://localhost:5000/api/task/start \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{"num": "9876543210", "int": 30}'
```

**Success Response (201):**

```json
{
  "task_id": "taskid-a1b2-c3d4",
  "status": "started",
  "phone_number": "9876543210",
  "interval": 30,
  "message": "Task taskid-a1b2-c3d4 started successfully"
}
```

**Error Response (400):**

```json
{
  "error": "Invalid phone number. Must be 10 digits.",
  "provided": "123"
}
```

---

### 2. Stop Task

Stops a running task.

```http
POST /api/task/stop/{task_id}
```

**Success Response (200):**

```json
{
  "task_id": "taskid-a1b2-c3d4",
  "status": "stopped",
  "message": "Task taskid-a1b2-c3d4 stopped successfully"
}
```

---

### 3. Get Task Info

Retrieves detailed information about a specific task.

```http
GET /api/task/{task_id}
```

**Success Response (200):**

```json
{
  "task_id": "taskid-a1b2-c3d4",
  "phone_number": "9876543210",
  "interval_seconds": 30,
  "status": "running",
  "created_at": "2026-01-20T19:30:00",
  "started_at": "2026-01-20T19:30:01",
  "stopped_at": null,
  "runtime": "0:05:32",
  "statistics": {
    "iterations": 10,
    "total_requests": 30,
    "successful_requests": 28,
    "failed_requests": 2,
    "success_rate": "93.3%"
  },
  "last_activity": "2026-01-20T19:35:33",
  "services_stats": {
    "Hungama": {"success": 10, "failed": 0},
    "ShemarooMe": {"success": 9, "failed": 1},
    "Unacademy": {"success": 9, "failed": 1}
  }
}
```

---

### 4. List All Tasks

Returns a summary of all tasks.

```http
GET /api/tasks
```

**Success Response (200):**

```json
{
  "tasks": [
    {
      "task_id": "taskid-a1b2-c3d4",
      "phone_number": "9876543210",
      "status": "running",
      "iterations": 10,
      "created_at": "2026-01-20T19:30:00"
    }
  ],
  "total": 1
}
```

---

### 5. Delete Task

Deletes a stopped task from storage.

```http
DELETE /api/task/{task_id}
```

**Success Response (200):**

```json
{
  "task_id": "taskid-a1b2-c3d4",
  "status": "deleted",
  "message": "Task taskid-a1b2-c3d4 deleted successfully"
}
```

**Error (must stop first):**

```json
{
  "error": "Cannot delete running task. Stop it first."
}
```

---

### 6. Health Check

```http
GET /health
```

**Response (200):**

```json
{
  "status": "healthy",
  "service": "OTP API",
  "version": "2.0.0"
}
```

---

## AI Agent Implementation Guide

Instructions for AI agents (LLMs, automation tools) to integrate with this API.

### Workflow Pattern

```
1. START TASK → Get task_id
2. POLL STATUS → Monitor progress via GET /api/task/{task_id}
3. STOP TASK → When condition met or user requests
4. CLEANUP → Delete task when done
```

### Implementation Steps

#### Step 1: Start an OTP Task

```python
import requests

API_KEY = "your-api-key"
HEADERS = {"X-API-KEY": API_KEY}

def start_otp_task(phone_number: str, interval: int = 60) -> dict:
    """
    Start a new OTP task.
    
    Args:
        phone_number: 10-digit Indian phone number (no country code)
        interval: Seconds between OTP requests (1-3600)
    
    Returns:
        dict with task_id and status
    """
    response = requests.post(
        "http://localhost:5000/api/task/start",
        headers=HEADERS,
        json={"num": phone_number, "int": interval}
    )
    return response.json()
```

#### Step 2: Monitor Task Status

```python
def get_task_status(task_id: str) -> dict:
    """
    Get current task status and statistics.
    
    Returns:
        dict with status, iterations, success_rate, etc.
    """
    response = requests.get(f"http://localhost:5000/api/task/{task_id}")
    return response.json()
```

#### Step 3: Stop Task

```python
def stop_task(task_id: str) -> dict:
    """Stop a running task."""
    response = requests.post(f"http://localhost:5000/api/task/stop/{task_id}")
    return response.json()
```

#### Step 4: Delete Task

```python
def delete_task(task_id: str) -> dict:
    """Delete a stopped task."""
    response = requests.delete(f"http://localhost:5000/api/task/{task_id}")
    return response.json()
```

### Complete Example

```python
import requests
import time

BASE_URL = "http://localhost:5000"
API_KEY = "your-api-key"
HEADERS = {"X-API-KEY": API_KEY}

# 1. Start task
result = requests.post(
    f"{BASE_URL}/api/task/start",
    headers=HEADERS,
    json={"num": "9876543210", "int": 30}
).json()

task_id = result["task_id"]
print(f"Started task: {task_id}")

# 2. Monitor for 2 minutes
for _ in range(4):
    time.sleep(30)
    status = requests.get(
        f"{BASE_URL}/api/task/{task_id}",
        headers=HEADERS
    ).json()
    print(f"Iterations: {status['statistics']['iterations']}")
    print(f"Success Rate: {status['statistics']['success_rate']}")

# 3. Stop task
requests.post(f"{BASE_URL}/api/task/stop/{task_id}", headers=HEADERS)
print("Task stopped")

# 4. Cleanup
requests.delete(f"{BASE_URL}/api/task/{task_id}", headers=HEADERS)
print("Task deleted")
```

### Task Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task created, not yet started |
| `running` | Task is actively sending OTPs |
| `stopped` | Task was stopped by user |
| `completed` | Task finished (rare) |
| `error` | Task crashed due to error |

### Error Handling

Always check for error keys in responses:

```python
result = requests.post(f"{BASE_URL}/api/task/start", json=data).json()

if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Task ID: {result['task_id']}")
```

### Rate Limits

- Minimum interval: 1 second
- Maximum interval: 3600 seconds (1 hour)
- Tasks auto-expire after 24 hours in Redis

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UPSTASH_REDIS_REST_URL` | ✅ | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ | Upstash Redis REST token |

---

## OTP Services

The API sends OTPs via these services:

1. **Hungama** - Music streaming platform
2. **ShemarooMe** - Video streaming platform  
3. **Unacademy** - Education platform

Each iteration sends requests to all 3 services with the configured interval between each.
