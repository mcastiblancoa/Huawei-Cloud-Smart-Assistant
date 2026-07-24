# Commands

## Command to deploy the ecs-whisper instance

```docker
docker run -d -p 9000:9000 -e ASR_MODEL=large onerahmet/openai-whisper-asr-webservice:latest
```

## Command to deploy the ecs-kokoro instance

```docker
docker run -d -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
```

## Quick Troubleshooting — Huawei Cloud Smart Assistant

### Backend won't start

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'X'` | Run `venv/bin/pip install X` inside the virtual environment. |
| `Address already in use` on port 8000 | Run `kill $(lsof -i :8000 -t)` |
| `hcloud not found` | Verify that `hcloud` is available in your PATH or inside the project's `bin/` directory. |

### Vision (Sentiment / Safety)

| Error | Solution |
|-------|----------|
| `/vision/status` returns `"unavailable"` / `false` | Run `venv/bin/pip install deepface tf-keras tensorflow opencv-python-headless numpy ultralytics` |
| `ImportError: cannot import name 'Keras'` | Run `pip install tf-keras` (required for DeepFace + TensorFlow 2.21+). |
| `cv2` crashes on Linux without a GUI | Use `opencv-python-headless` instead of `opencv-python`. |
| YOLOv8 cannot download `yolov8n.pt` | The first execution requires Internet access. Check your proxy or firewall settings. |
| Camera works but no results are returned | Verify that `VITE_API_BASE_URL` points to the correct backend (IP address + port). |
| Stops retrying after 3 failures (circuit breaker) | Refresh the page. The circuit breaker resets when switching tabs. |

### Frontend

| Error | Solution |
|-------|----------|
| `ERR_CONNECTION_TIMED_OUT` when connecting to the backend | Verify the IP address and port configured in `VITE_API_BASE_URL`, and ensure the security group allows the port. |
| Updated `.env` but changes are not applied | Restart the Vite development server (`kill` + `nohup npm run dev`). Variables prefixed with `VITE_` are embedded at startup. |
| CORS error | Add the frontend IP address to `BACKEND_CORS_ORIGINS` in the `.env` file and restart the backend. |
| Browser does not request camera permissions | Use HTTPS or localhost. `MediaRecorder` requires a secure context. |

### ECS Processes

| Task | Command |
|------|---------|
| Get backend PID | `lsof -i :8000 -t` |
| Get frontend PID | `ps aux \| grep vite` |
| Stop frontend | `kill <PID npm>` (terminate the parent npm process) |
| View backend logs in real time | `tail -f backend-8000.log` |
| Restart backend (systemd) | `sudo systemctl restart huawei-assistant` |
| Get the ECS public IP | `curl -s ifconfig.me` |

### Huawei Cloud

| Error | Solution |
|-------|----------|
| `Authentication failed` | Verify `HUAWEI_AK` and `HUAWEI_SK` in the `.env` file. |
| 429 rate limit | The agent automatically retries (up to 6 attempts with a 3-second backoff). |
| 81011 content filter | Automatically retries with a safer prompt (without IDs or credentials). |
| `Domain ID not found` | Verify `CLOUD_SDK_DOMAIN_ID`. |

# Run Whisper on GPU with Docker

```docker
docker run -d --gpus all -p 9000:9000 -e ASR_MODEL=large-v3 -e ASR_ENGINE=openai_whisper --name whisper-gpu-service onerahmet/openai-whisper-asr-webservice:latest-gpu
```

# Restart the Backend Service

```bash
sudo systemctl restart huawei-assistant-backend.service
```