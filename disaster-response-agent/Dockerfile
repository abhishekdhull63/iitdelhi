# =============================================================================
# Dockerfile — NEXUS Disaster Response Agent (Hybrid Python + Node.js)
# Claw & Shield 2026 Hackathon
#
# Build:  docker build -t nexus-agent .
# Run:    docker run -d -p 8501:8501 --env-file .env \
#           -v "$(pwd)/dispatch_output:/app/workspace/outgoing_dispatch" \
#           -v "$(pwd)/medical_logs:/app/workspace/medical_logs" \
#           nexus-agent
# =============================================================================

# ── Base image: slim Python 3.10 (minimal attack surface) ────────────────────
FROM python:3.10-slim

# ── Metadata labels (good practice, shows care for production hygiene) ────────
LABEL maintainer="NEXUS Team — Claw & Shield 2026"
LABEL description="Disaster Response AI Agent with ArmorIQ SDK + Shield middleware"
LABEL version="3.0.0"

# ── Prevent Python from writing .pyc files and enable unbuffered stdout ───────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Install Node.js 22 LTS (required: openclaw needs node >= 22.12.0) ─────────
# Using NodeSource setup script for Node 22 LTS on Debian slim.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ── Install OpenClaw CLI + ArmorIQ Plugin (via GitHub Clone) ──────────────────
RUN npm install -g openclaw && \
    git clone https://github.com/armoriq/armoriq-openclaw-plugin.git /opt/armoriq-openclaw-plugin && \
    cd /opt/armoriq-openclaw-plugin && \
    npm install && \
    npm run build && \
    openclaw plugins install .

# ── Create a non-root user (security best practice, OWASP / CIS) ─────────────
RUN groupadd --gid 1001 nexus && \
    useradd  --uid 1001 --gid nexus --shell /bin/bash --create-home nexus

# ── Set working directory ─────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application source files ─────────────────────────────────────────────
COPY enforcement_middleware.py .
COPY agent_core.py             .
COPY app.py                    .
COPY setup_sdk.py              .
COPY .env* ./

# ── Create the authorised file-write directories ──────────────────────────────
RUN mkdir -p /app/workspace/outgoing_dispatch \
    /app/workspace/medical_logs \
    /app/logs \
    /app/dev_workspace/outgoing_dispatch && \
    chown -R nexus:nexus /app

# ── Pre-create OpenClaw config directory for the nexus user ───────────────────
RUN mkdir -p /home/nexus/.openclaw && \
    chown -R nexus:nexus /home/nexus/.openclaw

# ── Switch to non-root user for runtime ───────────────────────────────────────
USER nexus

# ── Default command: run the Streamlit dashboard ──────────────────────────────
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
