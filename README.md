# OTP Task API

A Flask-based REST API for managing background OTP tasks with Redis persistence.

## Features

- 🚀 **Background Task Management** - Start, stop, and monitor OTP tasks
- 📊 **Real-time Statistics** - Track success rates and service-level stats
- 🔄 **Persistent Storage** - Uses Upstash Redis for task state management
- 🛠️ **Multiple OTP Services** - Integrates with Hungama, ShemarooMe, and Unacademy

## Requirements

- Python 3.10+
- Upstash Redis account

## Setup

1. **Clone and install dependencies:**
   ```bash
   pip install flask httpx upstash-redis python-dotenv
   ```

2. **Configure environment variables:**
   ```env
   UPSTASH_REDIS_REST_URL=https://your-url.upstash.io
   UPSTASH_REDIS_REST_TOKEN=your-token
   ```

3. **Run the server:**
   ```bash
   python app.py
   ```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/task/start` | Start a new OTP task |
| `POST` | `/api/task/stop/<task_id>` | Stop a running task |
| `GET` | `/api/task/<task_id>` | Get task details |
| `GET` | `/api/tasks` | List all tasks |
| `DELETE` | `/api/task/<task_id>` | Delete a stopped task |
| `GET` | `/health` | Health check |

## Quick Start

```bash
# Start a task
curl -X POST http://localhost:5000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{"num": "9876543210", "int": 30}'

# Check task status
curl http://localhost:5000/api/task/taskid-xxxx-xxxx

# Stop a task
curl -X POST http://localhost:5000/api/task/stop/taskid-xxxx-xxxx
```

## Deployment

⚠️ **Not compatible with serverless platforms** (Vercel, AWS Lambda, etc.)

Recommended platforms:
- Railway.app
- Render.com
- Fly.io
- Any VPS with persistent processes

## Documentation

See [docs/API.md](docs/API.md) for detailed API documentation and AI agent integration guide.

## License

MIT
