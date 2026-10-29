# Single-container build: the React app is built once, then served by FastAPI
# from the same origin as the API (no CORS or proxy setup needed).

# --- Stage 1: build the frontend ---
FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# --- Stage 2: backend + built frontend ---
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend /web/dist ./static

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Hosts like Render set PORT at runtime; 8000 is the local default.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
