# =============================================================================
# Dockerfile — NEXUS Disaster Response Agent
# Claw & Shield 2026 Hackathon
#
# Build:  docker build -t nexus-agent .
# Run:    docker run --env-file .env \
#           -v "$(pwd)/dispatch_output:/app/workspace/outgoing_dispatch" \
#           nexus-agent
# =============================================================================

# ── Base image: slim Python 3.10 (minimal attack surface) ────────────────────
FROM python:3.10-slim

# ── Metadata labels (good practice, shows care for production hygiene) ────────
LABEL maintainer="NEXUS Team — Claw & Shield 2026"
LABEL description="Disaster Response AI Agent with Shield enforcement middleware"
LABEL version="2.0.0"

# ── Prevent Python from writing .pyc files and enable unbuffered stdout ───────
# PYTHONDONTWRITEBYTECODE: keeps the image smaller (no __pycache__ clutter)
# PYTHONUNBUFFERED:        makes all print() and logging output appear in
#                          real-time in `docker run` — critical for demo video
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Create a non-root user (security best practice, OWASP / CIS) ─────────────
# Running as root inside a container is a privilege escalation risk.
RUN groupadd --gid 1001 nexus && \
    useradd  --uid 1001 --gid nexus --shell /bin/bash --create-home nexus

# ── Set working directory ─────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
# Copy requirements first so Docker layer-caches the pip install step.
# If only source code changes, pip install won't re-run — much faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application source files ─────────────────────────────────────────────
# Only copy what the agent needs — not the full static/ frontend.
COPY enforcement_middleware.py .
COPY agent_core.py             .
# Also copy .env if it exists (optional — prefer --env-file at runtime)
COPY .env* ./

# ── Create the authorised file-write directories ──────────────────────────────
# /app/workspace/outgoing_dispatch  ← Shield-scoped path for dispatch logs
# /app/logs                         ← LogisticsSubAgent log directory
# /app/dev_workspace/outgoing_dispatch ← dev fallback (used if Docker path missing)
RUN mkdir -p /app/workspace/outgoing_dispatch \
             /app/logs \
             /app/dev_workspace/outgoing_dispatch && \
    chown -R nexus:nexus /app

# ── Switch to non-root user for runtime ───────────────────────────────────────
USER nexus

# ── Default command: run the agent test harness ───────────────────────────────
# Override with `docker run ... nexus-agent uvicorn main:app` for the web server
CMD ["python", "agent_core.py"]
