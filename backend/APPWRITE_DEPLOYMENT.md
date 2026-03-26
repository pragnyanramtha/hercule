# Appwrite Deployment Guide (Backend)

This backend runs as a standard FastAPI ASGI service and is prepared for Appwrite container-based deployment.

## Files Added For Appwrite

- `Dockerfile.appwrite`
- `appwrite.env.example`

## Deploy Steps

1. In Appwrite, create a new backend service/function using your `backend` source.
2. Use `Dockerfile.appwrite` as the build container definition.
3. Set environment variables from `appwrite.env.example`.
4. Ensure the runtime exposes port `8000` (or your Appwrite-assigned `PORT`).
5. Use health check path `/health`.

## Required Environment Variables

- `GEMINI_API_KEY`

## Recommended Environment Variables

- `STORAGE_MODE=local`
- `ALLOWED_ORIGINS=*` (restrict in production)
- `LOG_LEVEL=INFO`

## Local Verification Before Deploy

```bash
cd backend
docker build -f Dockerfile.appwrite -t hercule-backend-appwrite .
docker run --rm -p 8000:8000 --env-file appwrite.env.example hercule-backend-appwrite
curl http://localhost:8000/health
```
