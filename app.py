"""
OTP API Server - Flask Application
Exposes OTP functionality via REST API endpoints with background task support.

Usage:
    python app.py
    
API Endpoints:
    POST /api/task/start - Start background OTP task
    POST /api/task/stop/<task_id> - Stop a running task
    GET  /api/task/<task_id> - Get task info
    GET  /api/tasks - List all tasks
    DELETE /api/task/<task_id> - Delete a task
    GET  /health
"""
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from api import TaskManager

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize TaskManager with Redis URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
task_manager = TaskManager(REDIS_URL)


# ═══════════════════════════════════════════════════════════════════════════════
# TASK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/task/start', methods=['POST'])
def start_task():
    """
    Start a new background OTP task.
    
    Request Body (JSON):
        num (required): Phone number (10 digits, Indian format without country code)
        int (optional): Interval in seconds between requests (default: 60)
    
    Example:
        POST /api/task/start
        {"num": "9876543210", "int": 30}
    
    Returns:
        {
            "task_id": "taskid-xxxx-xxxx",
            "status": "started",
            "phone_number": "9876543210",
            "interval": 30,
            "message": "Task taskid-xxxx-xxxx started successfully"
        }
    """
    data = request.get_json() or {}
    
    phone_number = data.get('num') or request.args.get('num')
    interval = data.get('int', 60)
    
    # Also accept from query params
    if not phone_number:
        phone_number = request.args.get('num')
    if request.args.get('int'):
        interval = int(request.args.get('int'))

    # Validate phone number
    if not phone_number:
        return jsonify({
            "error": "Missing required parameter: num",
            "usage": "POST /api/task/start with JSON body: {\"num\": \"9876543210\", \"int\": 30}"
        }), 400

    if not phone_number.isdigit() or len(phone_number) != 10:
        return jsonify({
            "error": "Invalid phone number. Must be 10 digits.",
            "provided": phone_number
        }), 400

    # Validate interval
    if not isinstance(interval, int) or interval < 1 or interval > 3600:
        return jsonify({
            "error": "Invalid interval. Must be an integer between 1 and 3600 seconds.",
            "provided": interval
        }), 400

    # Start the task
    try:
        result = task_manager.start_task(phone_number, interval)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({
            "error": "Failed to start task",
            "details": str(e)
        }), 500


@app.route('/api/task/stop/<task_id>', methods=['POST'])
def stop_task(task_id: str):
    """
    Stop a running OTP task.
    
    URL Parameters:
        task_id (required): The task ID to stop
    
    Example:
        POST /api/task/stop/taskid-xxxx-xxxx
    
    Returns:
        {
            "task_id": "taskid-xxxx-xxxx",
            "status": "stopped",
            "message": "Task taskid-xxxx-xxxx stopped successfully"
        }
    """
    try:
        result = task_manager.stop_task(task_id)
        
        if "error" in result:
            return jsonify(result), 404 if "not found" in result["error"].lower() else 400
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to stop task",
            "details": str(e)
        }), 500


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    Get detailed information about a task.
    
    URL Parameters:
        task_id (required): The task ID to retrieve
    
    Example:
        GET /api/task/taskid-xxxx-xxxx
    
    Returns:
        {
            "task_id": "taskid-xxxx-xxxx",
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
    """
    try:
        result = task_manager.get_task_info(task_id)
        
        if result is None:
            return jsonify({
                "error": f"Task {task_id} not found"
            }), 404
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to get task info",
            "details": str(e)
        }), 500


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """
    List all tasks.
    
    Example:
        GET /api/tasks
    
    Returns:
        {
            "tasks": [
                {
                    "task_id": "taskid-xxxx-xxxx",
                    "phone_number": "9876543210",
                    "status": "running",
                    "iterations": 10,
                    "created_at": "2026-01-20T19:30:00"
                },
                ...
            ],
            "total": 5
        }
    """
    try:
        tasks = task_manager.get_all_tasks()
        return jsonify({
            "tasks": tasks,
            "total": len(tasks)
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to list tasks",
            "details": str(e)
        }), 500


@app.route('/api/task/<task_id>', methods=['DELETE'])
def delete_task(task_id: str):
    """
    Delete a task (must be stopped first).
    
    URL Parameters:
        task_id (required): The task ID to delete
    
    Example:
        DELETE /api/task/taskid-xxxx-xxxx
    
    Returns:
        {
            "task_id": "taskid-xxxx-xxxx",
            "status": "deleted",
            "message": "Task taskid-xxxx-xxxx deleted successfully"
        }
    """
    try:
        result = task_manager.delete_task(task_id)
        
        if "error" in result:
            status_code = 404 if "not found" in result["error"].lower() else 400
            return jsonify(result), status_code
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to delete task",
            "details": str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "OTP API",
        "version": "2.0.0"
    }), 200


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint."""
    return jsonify({
        "name": "OTP API Service",
        "version": "2.0.0",
        "description": "Background OTP Task Management API",
        "endpoints": {
            "/api/task/start": {
                "method": "POST",
                "description": "Start a new background OTP task",
                "body": {
                    "num": "Phone number (10 digits, required)",
                    "int": "Interval in seconds (optional, default: 60)"
                },
                "example": "POST /api/task/start with body: {\"num\": \"9876543210\", \"int\": 30}"
            },
            "/api/task/stop/<task_id>": {
                "method": "POST",
                "description": "Stop a running task",
                "example": "POST /api/task/stop/taskid-xxxx-xxxx"
            },
            "/api/task/<task_id>": {
                "methods": ["GET", "DELETE"],
                "description": "Get task info (GET) or delete task (DELETE)",
                "example": "GET /api/task/taskid-xxxx-xxxx"
            },
            "/api/tasks": {
                "method": "GET",
                "description": "List all tasks"
            },
            "/health": {
                "method": "GET",
                "description": "Health check endpoint"
            }
        }
    }), 200


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║          OTP API Server - v2.0.0 (Task Mode)             ║
╠══════════════════════════════════════════════════════════╣
║  Task Endpoints:                                         ║
║  • POST   /api/task/start      - Start new task          ║
║  • POST   /api/task/stop/<id>  - Stop running task       ║
║  • GET    /api/task/<id>       - Get task info           ║
║  • GET    /api/tasks           - List all tasks          ║
║  • DELETE /api/task/<id>       - Delete task             ║
║  • GET    /health              - Health check            ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=True)
