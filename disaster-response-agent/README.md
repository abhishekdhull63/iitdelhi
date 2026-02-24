# 🚨 NEXUS — Disaster Response AI Agent
### Claw & Shield 2026 Hackathon

> **AI-powered emergency triage with multimodal vision, real-time search grounding, and a programmatic safety enforcement layer (The Shield).**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Tech Stack](#tech-stack)
6. [Getting Started](#getting-started)
7. [Running the Application](#running-the-application)
8. [API Reference](#api-reference)
9. [Bounded Delegation & Security](#bounded-delegation--security)
10. [The Shield — Enforcement Middleware](#the-shield--enforcement-middleware)
11. [Docker Deployment](#docker-deployment)
12. [Test Harness](#test-harness)
13. [Configuration Reference](#configuration-reference)

---

## Overview

NEXUS is a production-grade **Disaster Response AI Agent** built for the Claw & Shield 2026 security hackathon. It accepts free-text emergency reports (with an optional disaster photo), runs them through a 7-layer security pipeline, and returns a structured JSON triage result — including severity classification, exactly 3 recommended actions, and an AI reasoning summary.

The system is designed around **zero-trust principles**: every input is treated as hostile, every output is validated, and no LLM output can bypass the deterministic enforcement layer ("The Shield") to touch the filesystem.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      NEXUS COMMAND CENTER                       │
│        (Streamlit Glass-Box Dashboard + HITL Checkbox)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │  process_mission()
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              TriageCommander  (agent_core.py)                   │
│  Gemini reasoning → IntentModel → 🛡️ Shield → SubAgent          │
│                                                                 │
│          🛡️  enforcement_middleware.py  (The Shield)            │
│          ├─ ArmorIQ SDK Bridge  (calls Node.js CLI)             │
│          ├─ RULE:ACTION_TYPE    allowlist check                  │
│          ├─ RULE:MEDICAL_BLOCK  keyword + regex scan             │
│          ├─ RULE:DIR_SCOPE      pathlib containment check        │
│          └─ 🗄️ SQLite Audit DB   persistent logging (/workspace)  │
│                                                                 │
│          LogisticsSubAgent  (Bounded Delegation)                │
│          ├─ Accepts: .json payloads → writes to /logs/ only      │
│          └─ Rejects: .py / .sh / .exe → AuthorityExceededError  │
│                                                                 │
│          MedicalTriageAgent (Sandboxed Routing)                 │
│          └─ Accepts: Symptom analysis → writes to /medical_logs/│
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Detail |
|---|---|
| **ArmorIQ Node.js SDK Bridge** | Hybrid architecture calls the official ArmorIQ OpenClaw SDK via Python `subprocess`, falling back to the local rule engine if offline. |
| **Enterprise Governance** | Simultaneous implementation of Human-in-the-Loop (HITL) volume limits, persistent SQLite audit logging, and a glass-box live data feed UI. |
| **Multimodal Analysis** | Upload a disaster photo alongside a text report for visual damage assessment by Gemini |
| **Real-Time Search Grounding** | Google Search is enabled as a tool — live weather alerts, road closures, and local emergency contacts are included in recommendations |
| **Bounded Delegation** | `TriageCommander` delegates to `LogisticsSubAgent` which operates under strict Principle of Least Authority (PoLA) |
| **Self-Healing Reflection Loop** | If the Shield blocks an action (e.g., directory scope violation), the Agent feeds the error back to Gemini to auto-correct and retry. |
| **Programmatic Shield** | Deterministic, LLM-independent enforcement layer that blocks medical out-of-scope content and filesystem scope violations |
| **Docker Ready** | Run as a non-root container (`uid=1001`) with dedicated volume-mounted dispatch and audit log directories |
| **Glassmorphism UI** | Streamlit-powered dark-mode dashboard with real-time feedback, HTML log rendering, and live SQLite database visual feeds. |

---

## Project Structure

```
disaster-response-agent/
├── app.py                     # Streamlit web dashboard (Glass-Box UI)
├── agent_core.py              # Bounded delegation: TriageCommander + LogisticsSubAgent + MedicalTriageAgent
├── enforcement_middleware.py  # The Shield — policy enforcement + SQLite logging + HITL + ArmorIQ SDK Bridge
├── setup_sdk.py               # Generates ~/.openclaw/openclaw.json for ArmorIQ SDK
├── main.py                    # Legacy FastAPI server
├── agent.py                   # Legacy core triage pipeline
│
├── dispatch_output/           # Bounded directory for Logistics write actions
├── medical_logs/              # Bounded directory for Medical write actions
├── security_audit.db          # Persistent SQLite database storing all Shield routing decisions
│
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Production hybrid container (Node 22 + Python 3.10-slim)
├── .env.example               # Environment variable template
├── .env                       # Your secrets (never commit)
├── agent_core.log             # TriageCommander execution logs
└── agent_errors.log           # Runtime error log
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM / AI** | Google Gemini 3.0 Flash Preview (`gemini-3-flash-preview`) via `google-genai ≥ 1.0.0` |
| **Search Grounding** | Google Search tool (built-in Gemini tool, zero additional config) |
| **Web Framework** | Streamlit ≥ 1.42.0 |
| **Image Processing** | Pillow ≥ 10.0.0 (multimodal upload decoding) |
| **Env Management** | `python-dotenv` ≥ 1.0.0 |
| **Data Visualization** | `pandas` for SQLite datafeeds |
| **Container** | Docker — Python 3.10-slim + Node.js 22 LTS (CLI), non-root user |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A [Google AI Studio API key](https://aistudio.google.com/apikey) (free tier works)

### 1. Clone and set up the environment

```bash
git clone <your-repo-url>
cd disaster-response-agent

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
# Edit .env and set your key:
#   GEMINI_API_KEY=AIza...
```

> The application also accepts `GOOGLE_API_KEY` as an alias for `GEMINI_API_KEY`.

---

## Running the Application

### Development Server (Streamlit UI)

```bash
streamlit run app.py
```

Open your browser at **[http://localhost:8501](http://localhost:8501)**.

### Run the bounded delegation test harness

```bash
python agent_core.py
```

This runs 3 pre-defined test scenarios (see [Test Harness](#test-harness) below).

---

## API Reference

### `GET /`

Serves the NEXUS Command Center HTML dashboard (`static/index.html`).

---

### `POST /api/analyze`

Analyze an emergency report with optional image.

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `report` | `string` | ✅ | Emergency description text (max 1,000 characters) |
| `image` | `file` | ❌ | Disaster photo for visual analysis (JPEG/PNG/WebP, max 10 MB) |

**Response** — `application/json`

```json
{
  "severity": "Critical",
  "recommended_actions": [
    "Call 108/911 immediately",
    "Evacuate residents within 500m radius",
    "Establish emergency command post at sector entry"
  ],
  "reasoning": "Structural collapse detected in uploaded image. Multiple injury indicators present. Immediate rescue operation required."
}
```

**Severity levels:** `Low` | `Medium` | `High` | `Critical` | `Error`

**Error responses:**

| Status | Condition |
|---|---|
| `400` | Empty report, report > 1,000 chars, non-image file upload, image > 10 MB |
| `500` | Gemini API failure or unhandled exception |

---

## Bounded Delegation & Security

NEXUS implements a **two-tier agent architecture** with strict authority boundaries:

```
TriageCommander (broad authority)
    │
    │  delegates only a JSON payload + .json filename
    ▼
LogisticsSubAgent (narrow authority)
    │  independently enforces its OWN boundary
    └─ AuthorityExceededError if extension ≠ .json
```

### Why This Matters

The `TriageCommander` holds broad reasoning authority (Gemini, policy evaluation). The `LogisticsSubAgent` has a **strictly narrower scope** — it can only write `.json` files to the `/logs/` directory, regardless of what the Commander tells it to do.

This mirrors production security architectures where privilege is shed at execution time (**Principle of Least Authority, PoLA**).

### `AuthorityExceededError`

Raised by `LogisticsSubAgent.validate_filename()` when:
- File extension is not `.json` (e.g., `.py`, `.sh`, `.exe`)
- Filename contains null bytes (path injection)
- Resolved path escapes the `log_dir` (directory traversal)

---

## The Shield — Enforcement Middleware

`enforcement_middleware.py` implements a **deterministic, LLM-independent** safety layer that runs _before_ any disk write or external call.

### Why Not Prompt Engineering?

> Prompt engineering ("don't do X") is probabilistic — the model can comply or fail depending on temperature, context drift, or jailbreaks. The Shield enforces policy in compiled Python, which is immune to such failure modes.

### Three-Phase Pipeline

| Phase | Function | What It Checks |
|---|---|---|
| **1. Action Type** | `_check_action_type()` | Allowlist: only `WRITE_DISPATCH_LOG` is permitted |
| **2. Medical Block** | `_check_medical_keywords()` | 11 blocked keyword clusters + 6 regex patterns detect out-of-scope medical content |
| **3. Directory Scope** | `_check_filepath_scope()` | `pathlib.relative_to()` containment check prevents directory traversal |

### Blocked Keyword Clusters (examples)

```python
frozenset({"diagnosis", "treatment"})
frozenset({"prescription", "medication"})
frozenset({"burns", "laceration", "fracture"})
frozenset({"patient", "clinical", "symptom"})
```

Any single set being fully present in the intent text causes an immediate `PolicyViolationError`.

### Disaster Categories Supported

`FLOOD` · `EARTHQUAKE` · `WILDFIRE` · `CYCLONE` · `INFRASTRUCTURE` · `EVACUATION` · `SEARCH_RESCUE` · `LOGISTICS`

---

## Docker Deployment

### Build the Image

```bash
docker build -t nexus-agent .
```

### Run the Hybrid Container

Run the Docker container, exposing the Streamlit dashboard and safely mounting all necessary persistence volumes:

```bash
docker run -d --rm \
  -p 8501:8501 \
  -v "$(pwd)/dispatch_output:/app/workspace/outgoing_dispatch"\
  -v "$(pwd)/medical_logs:/app/workspace/medical_logs"\
  -v "$(pwd)/security_audit.db:/app/workspace/security_audit.db"\
  --env-file .env \
  nexus-agent
```

**Security highlights in the Dockerfile:**
- Base image: `python:3.10-slim` (minimal attack surface) with Node.js 22
- Non-root runtime user: `nexus` (uid/gid 1001)
- `PYTHONDONTWRITEBYTECODE=1` — no `.pyc` clutter in the image
- `PYTHONUNBUFFERED=1` — real-time log visibility in container
- Isolated volume mounts ensure that the agent can ONLY write to specific directories on the host system.

---

## Test Harness

Run `python agent_core.py` to execute 3 built-in scenarios:

| Test | Mission | Expected Outcome |
|---|---|---|
| **A — Logistics** | Flood logistics dispatch (500 water units, 200 rescue boats) | `SUCCESS` ✅ — dispatch JSON written to `/logs/` |
| **B — Medical Block** | Request for treatment prescription and diagnosis report | `BLOCKED_BY_SHIELD` 🛑 — `RULE:MEDICAL_BLOCK` |
| **C — Authority Block** | Direct `LogisticsSubAgent` call with `.py` / `.sh` / `.exe` filenames | `BLOCKED_BY_SUB_AGENT` 🚫 — `AuthorityExceededError` |

All 3 tests exit `0` if they behave as expected, `1` otherwise.

---

## Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `GOOGLE_API_KEY` | ✅ (alias) | Alternative name accepted by both `agent.py` and `agent_core.py` |

### Key Constants

| File | Constant | Default | Description |
|---|---|---|---|
| `agent.py` | `MAX_INPUT_LENGTH` | `1000` | Max characters accepted from the frontend |
| `agent.py` | `MAX_RETRIES` | `2` | Gemini call retry attempts on schema validation failure |
| `agent.py` | `PRIMARY_MODEL` | `gemini-3-flash-preview` | Gemini model used for triage |
| `main.py` | `MAX_REPORT_LENGTH` | `1000` | HTTP-layer report length cap |
| `main.py` | `MAX_IMAGE_SIZE` | `10 MB` | Maximum uploaded image size |
| `agent_core.py` | `GEMINI_MODEL_NAME` | `gemini-3-flash-preview` | Model used by TriageCommander |

---

## Security Compliance

- **OWASP Top 10** — Injection prevention, input validation, no stack traces exposed to users
- **OWASP LLM Top 10** — Prompt injection detection with 15+ phrase patterns
- **CIS Python Benchmarks** — No `eval`, no `exec`, no `pickle`
- **Zero-Trust** — All inputs treated as hostile; all LLM outputs schema-validated before use
- **Secrets Management** — API keys loaded from `.env` via `python-dotenv`; never hardcoded

---

*Built with ❤️ for the Claw & Shield 2026 Hackathon by the NEXUS Team.*
