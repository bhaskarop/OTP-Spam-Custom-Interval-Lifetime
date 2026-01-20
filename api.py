"""
OTP API Module - Core API Logic with Task Management
Provides the OTP sending functionality with background task support using Upstash Redis.
"""

import os
import json
import uuid
import time
import threading
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum

import httpx
from upstash_redis import Redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """Configuration for OTP requests."""
    phone_number: str
    interval_seconds: int = 60
    country_code: str = "+91"
    request_timeout: int = 30


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ServiceResponse:
    """Represents a response from an OTP service."""
    service_name: str
    status_code: int | None = None
    response_data: Any = None
    error: str | None = None
    success: bool = field(init=False)

    def __post_init__(self) -> None:
        self.success = self.error is None

    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            "service_name": self.service_name,
            "status_code": self.status_code,
            "response_data": self.response_data,
            "error": self.error,
            "success": self.success
        }


# ═══════════════════════════════════════════════════════════════════════════════
# REDIS MANAGER (UPSTASH)
# ═══════════════════════════════════════════════════════════════════════════════

class RedisManager:
    """Manages Upstash Redis connection and task storage."""
    
    def __init__(self, redis_url: str = None):
        """Initialize Upstash Redis connection using environment variables."""
        # Use environment variables for Upstash connection
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        
        if url and token:
            self.client = Redis(url=url, token=token)
        else:
            raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set in environment")
        
        self.task_prefix = "otp:task:"
    
    def _get_key(self, task_id: str) -> str:
        return f"{self.task_prefix}{task_id}"
    
    def create_task(self, task_id: str, phone_number: str, interval: int) -> dict:
        """Create a new task in Redis."""
        task_data = {
            "task_id": task_id,
            "phone_number": phone_number,
            "interval": interval,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "stopped_at": None,
            "iterations": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_activity": None,
            "services_stats": {}
        }
        
        # Convert to string format for Redis hash
        key = self._get_key(task_id)
        redis_data = {}
        for k, v in task_data.items():
            if isinstance(v, dict):
                redis_data[k] = json.dumps(v)
            elif v is None:
                redis_data[k] = ""
            else:
                redis_data[k] = str(v)
        
        # Use hset with mapping dict for Upstash Redis
        self.client.hset(key, redis_data)
        
        # Set expiry to 24 hours
        self.client.expire(key, 86400)
        return task_data
    
    def get_task(self, task_id: str) -> dict | None:
        """Get task data from Redis."""
        data = self.client.hgetall(self._get_key(task_id))
        if not data:
            return None
        
        # Parse the data
        parsed = {}
        for k, v in data.items():
            if k in ["services_stats"]:
                parsed[k] = json.loads(v) if v else {}
            elif k in ["iterations", "total_requests", "successful_requests", "failed_requests", "interval"]:
                parsed[k] = int(v) if v else 0
            elif v == "None" or v == "":
                parsed[k] = None
            else:
                parsed[k] = v
        return parsed
    
    def update_task(self, task_id: str, updates: dict) -> None:
        """Update task data in Redis."""
        key = self._get_key(task_id)
        redis_data = {}
        for k, v in updates.items():
            if isinstance(v, dict):
                redis_data[k] = json.dumps(v)
            elif v is None:
                redis_data[k] = ""
            else:
                redis_data[k] = str(v)
        
        # Use hset with mapping dict for Upstash Redis
        self.client.hset(key, redis_data)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from Redis."""
        result = self.client.delete(self._get_key(task_id))
        return result > 0 if isinstance(result, int) else bool(result)
    
    def get_all_tasks(self) -> list[dict]:
        """Get all tasks from Redis."""
        keys = self.client.keys(f"{self.task_prefix}*")
        tasks = []
        if keys:
            for key in keys:
                task_id = key.replace(self.task_prefix, "")
                task = self.get_task(task_id)
                if task:
                    tasks.append(task)
        return tasks


# ═══════════════════════════════════════════════════════════════════════════════
# BASE SERVICE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OTPService:
    """Base class for OTP services."""

    def __init__(self, client: httpx.Client, config: Config) -> None:
        self.client = client
        self.config = config

    @property
    def name(self) -> str:
        return "Base"

    @property
    def url(self) -> str:
        return ""

    @property
    def base_headers(self) -> dict[str, str]:
        """Return common headers used by most services."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Sec-GPC": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Connection": "keep-alive",
        }

    def get_headers(self) -> dict[str, str]:
        return {}

    def get_payload(self) -> dict | str:
        return {}

    def send_request(self) -> ServiceResponse:
        """Send OTP request to the service."""
        try:
            headers = {**self.base_headers, **self.get_headers()}
            payload = self.get_payload()

            if isinstance(payload, dict):
                response = self.client.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.request_timeout
                )
            else:
                response = self.client.post(
                    self.url,
                    headers=headers,
                    content=payload,
                    timeout=self.config.request_timeout
                )

            response_data = self._parse_response(response)

            return ServiceResponse(
                service_name=self.name,
                status_code=response.status_code,
                response_data=response_data
            )

        except httpx.TimeoutException:
            return ServiceResponse(
                service_name=self.name,
                error="Request timed out"
            )
        except httpx.RequestError as e:
            return ServiceResponse(
                service_name=self.name,
                error=f"Request failed: {e}"
            )
        except Exception as e:
            return ServiceResponse(
                service_name=self.name,
                error=str(e)
            )

    @staticmethod
    def _parse_response(response: httpx.Response) -> Any:
        """Parse the HTTP response content."""
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            return response.json()
        return response.text


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class HungamaService(OTPService):
    """Hungama OTP Service implementation."""

    @property
    def name(self) -> str:
        return "Hungama"

    @property
    def url(self) -> str:
        return "https://chcommunication.api.hungama.com/v1/communication/otp"

    def get_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://www.hungama.com/",
            "Origin": "https://www.hungama.com",
            "identifier": "home",
            "mlang": "en",
            "vlang": "en",
            "alang": "en",
            "country_code": "IN",
            "Sec-Fetch-Site": "same-site",
            "Priority": "u=0",
        }

    def get_payload(self) -> dict:
        return {
            "mobileNo": self.config.phone_number,
            "countryCode": self.config.country_code,
            "appCode": "un",
            "messageId": "1",
            "emailId": "",
            "subject": "Register",
            "priority": "1",
            "device": "web",
            "variant": "v1",
            "templateCode": 1
        }


class ShemarooMeService(OTPService):
    """ShemarooMe OTP Service implementation."""

    @property
    def name(self) -> str:
        return "ShemarooMe"

    @property
    def url(self) -> str:
        return "https://www.shemaroome.com/users/mobile_no_signup"

    def get_headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://www.shemaroome.com/users/sign_in",
            "Origin": "https://www.shemaroome.com",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
        }

    def get_payload(self) -> str:
        return f"mobile_no=%2B91{self.config.phone_number}&registration_source=organic"


class UnacademyService(OTPService):
    """Unacademy OTP Service implementation."""

    @property
    def name(self) -> str:
        return "Unacademy"

    @property
    def url(self) -> str:
        return "https://unacademy.com/api/v3/user/user_check/?enable-email=true"

    def get_headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Referer": "https://unacademy.com/",
            "Origin": "https://unacademy.com",
            "X-Platform": "0",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=4",
        }

    def get_payload(self) -> dict:
        return {
            "phone": self.config.phone_number,
            "country_code": "IN",
            "otp_type": 1,
            "email": "",
            "send_otp": True,
            "is_un_teach_user": False
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TASK MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TaskManager:
    """Manages background OTP tasks."""
    
    SERVICES = [HungamaService, ShemarooMeService, UnacademyService]
    
    def __init__(self, redis_url: str):
        self.redis = RedisManager(redis_url)
        self.active_tasks: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
    
    @staticmethod
    def generate_task_id() -> str:
        """Generate a unique task ID."""
        uid = uuid.uuid4().hex
        return f"taskid-{uid[:4]}-{uid[4:8]}"
    
    def start_task(self, phone_number: str, interval: int) -> dict:
        """Start a new OTP task."""
        task_id = self.generate_task_id()
        
        # Create task in Redis
        task_data = self.redis.create_task(task_id, phone_number, interval)
        
        # Create stop event
        stop_event = threading.Event()
        
        with self._lock:
            self.active_tasks[task_id] = stop_event
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, phone_number, interval, stop_event),
            daemon=True
        )
        thread.start()
        
        return {
            "task_id": task_id,
            "status": "started",
            "phone_number": phone_number,
            "interval": interval,
            "message": f"Task {task_id} started successfully"
        }
    
    def stop_task(self, task_id: str) -> dict:
        """Stop a running task."""
        task = self.redis.get_task(task_id)
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        if task["status"] != TaskStatus.RUNNING.value:
            return {"error": f"Task {task_id} is not running (status: {task['status']})"}
        
        with self._lock:
            stop_event = self.active_tasks.get(task_id)
            if stop_event:
                stop_event.set()
                del self.active_tasks[task_id]
        
        # Update task status
        self.redis.update_task(task_id, {
            "status": TaskStatus.STOPPED.value,
            "stopped_at": datetime.now().isoformat()
        })
        
        return {
            "task_id": task_id,
            "status": "stopped",
            "message": f"Task {task_id} stopped successfully"
        }
    
    def get_task_info(self, task_id: str) -> dict | None:
        """Get detailed task information."""
        task = self.redis.get_task(task_id)
        
        if not task:
            return None
        
        # Calculate runtime
        runtime = None
        if task.get("started_at"):
            start = datetime.fromisoformat(task["started_at"])
            if task["status"] == TaskStatus.RUNNING.value:
                runtime = str(datetime.now() - start)
            elif task.get("stopped_at"):
                stop = datetime.fromisoformat(task["stopped_at"])
                runtime = str(stop - start)
        
        return {
            "task_id": task["task_id"],
            "phone_number": task["phone_number"],
            "interval_seconds": task["interval"],
            "status": task["status"],
            "created_at": task["created_at"],
            "started_at": task.get("started_at"),
            "stopped_at": task.get("stopped_at"),
            "runtime": runtime,
            "statistics": {
                "iterations": task.get("iterations", 0),
                "total_requests": task.get("total_requests", 0),
                "successful_requests": task.get("successful_requests", 0),
                "failed_requests": task.get("failed_requests", 0),
                "success_rate": f"{(task.get('successful_requests', 0) / max(task.get('total_requests', 1), 1)) * 100:.1f}%"
            },
            "last_activity": task.get("last_activity"),
            "services_stats": task.get("services_stats", {})
        }
    
    def get_all_tasks(self) -> list[dict]:
        """Get all tasks."""
        tasks = self.redis.get_all_tasks()
        return [
            {
                "task_id": t["task_id"],
                "phone_number": t["phone_number"],
                "status": t["status"],
                "iterations": t.get("iterations", 0),
                "created_at": t["created_at"]
            }
            for t in tasks
        ]
    
    def delete_task(self, task_id: str) -> dict:
        """Delete a task (must be stopped first)."""
        task = self.redis.get_task(task_id)
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        if task["status"] == TaskStatus.RUNNING.value:
            return {"error": f"Cannot delete running task. Stop it first."}
        
        self.redis.delete_task(task_id)
        
        return {
            "task_id": task_id,
            "status": "deleted",
            "message": f"Task {task_id} deleted successfully"
        }
    
    def _run_task(self, task_id: str, phone_number: str, interval: int, stop_event: threading.Event) -> None:
        """Background task runner."""
        config = Config(phone_number=phone_number, interval_seconds=interval)
        
        # Update status to running
        self.redis.update_task(task_id, {
            "status": TaskStatus.RUNNING.value,
            "started_at": datetime.now().isoformat()
        })
        
        iteration = 0
        services_stats = {s(None, config).name: {"success": 0, "failed": 0} for s in self.SERVICES}
        
        try:
            with httpx.Client(http2=True, verify=True) as client:
                while not stop_event.is_set():
                    iteration += 1
                    total_requests = 0
                    successful = 0
                    failed = 0
                    
                    for service_class in self.SERVICES:
                        if stop_event.is_set():
                            break
                        
                        service = service_class(client, config)
                        response = service.send_request()
                        
                        total_requests += 1
                        if response.success:
                            successful += 1
                            services_stats[service.name]["success"] += 1
                        else:
                            failed += 1
                            services_stats[service.name]["failed"] += 1
                        
                        # Update Redis after each request
                        task = self.redis.get_task(task_id)
                        if task:
                            self.redis.update_task(task_id, {
                                "iterations": iteration,
                                "total_requests": task.get("total_requests", 0) + 1,
                                "successful_requests": task.get("successful_requests", 0) + (1 if response.success else 0),
                                "failed_requests": task.get("failed_requests", 0) + (0 if response.success else 1),
                                "last_activity": datetime.now().isoformat(),
                                "services_stats": services_stats
                            })
                        
                        # Wait between services
                        if not stop_event.is_set():
                            stop_event.wait(interval)
                    
        except Exception as e:
            self.redis.update_task(task_id, {
                "status": TaskStatus.ERROR.value,
                "stopped_at": datetime.now().isoformat(),
                "last_activity": f"Error: {str(e)}"
            })
        finally:
            with self._lock:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
