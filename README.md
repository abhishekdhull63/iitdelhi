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
│                      (Browser Frontend)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │  POST /api/analyze
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (FastAPI)                        │
│  • Input validation (length, MIME type)                         │
│  • CORS middleware                                              │
│  • Startup Gemini connectivity probe                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   agent.py  (Triage Pipeline)                   │
│  7-Layer Input Sanitization                                     │
│  ├─ Type check → Strip → Empty → Length → HTML strip            │
│  ├─ Prompt Injection Detection (OWASP LLM Top 10)               │
│  └─ Control character removal                                   │
│                                                                 │
│  Gemini 2.0 Flash  (multimodal + Google Search grounding)       │
│  ├─ Optional image bytes (JPEG / PNG / WebP, ≤10 MB)            │
│  └─ Retry logic (MAX_RETRIES = 2)                               │
│                                                                 │
│  Output Validation                                              │
│  └─ Schema: severity | recommended_actions (×3) | reasoning     │
└──────────────────────────┬──────────────────────────────────────┘
                           │  (agent_core.py — advanced flow)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              TriageCommander  (agent_core.py)                   │
│  Gemini reasoning → IntentModel → 🛡️ Shield → SubAgent          │
│                                                                 │
│          🛡️  enforcement_middleware.py  (The Shield)            │
│          ├─ RULE:ACTION_TYPE    allowlist check                  │
│          ├─ RULE:MEDICAL_BLOCK  keyword + regex scan             │
│          └─ RULE:DIR_SCOPE      pathlib containment check        │
│                                                                 │
│          LogisticsSubAgent  (Bounded Delegation)                │
│          ├─ Accepts: .json payloads → writes to /logs/ only      │
│          └─ Rejects: .py / .sh / .exe → AuthorityExceededError  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Detail |
|---|---|
| **Multimodal Analysis** | Upload a disaster photo alongside a text report for visual damage assessment by Gemini |
| **Real-Time Search Grounding** | Google Search is enabled as a tool — live weather alerts, road closures, and local emergency contacts are included in recommendations |
| **7-Layer Input Sanitization** | Type check → Strip → Length cap → HTML stripping → Prompt injection detection → Control-char removal |
| **Prompt Injection Guard** | 15+ regex patterns covering DAN, system prompt overrides, `ignore previous instructions`, `act as`, etc. |
| **Retry Logic** | Two automatic retry attempts if Gemini returns an invalid/malformed JSON schema |
| **Bounded Delegation** | `TriageCommander` delegates to `LogisticsSubAgent` which operates under strict Principle of Least Authority (PoLA) |
| **Programmatic Shield** | Deterministic, LLM-independent enforcement layer that blocks medical out-of-scope content and filesystem scope violations |
| **Docker Ready** | Run as a non-root container (`uid=1001`) with dedicated volume-mounted dispatch directories |
| **Glassmorphism UI** | Fully client-side dashboard (HTML/CSS/JS) with rapid triage chips, copy-for-dispatch button, and analysis history |

---

## Project Structure

```
disaster-response-agent/
├── main.py                    # FastAPI server — routes /api/analyze and serves frontend
├── agent.py                   # Core triage pipeline (sanitize → Gemini → validate)
├── agent_core.py              # Bounded delegation: TriageCommander + LogisticsSubAgent
├── enforcement_middleware.py  # The Shield — deterministic policy enforcement
│
├── static/
│   ├── index.html             # NEXUS Command Center frontend dashboard
│   ├── style.css              # Glassmorphism dark-mode UI styles
│   └── script.js              # Frontend logic (fetch, history, rapid triage chips)
│
├── logs/                      # LogisticsSubAgent output directory (created at runtime)
├── dev_workspace/             # Local dev fallback for dispatch outputs
│   └── outgoing_dispatch/
│
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Production container (Python 3.10-slim, non-root)
├── .env.example               # Environment variable template
├── .env                       # Your secrets (never commit — already in .gitignore)
├── .gitignore
├── .dockerignore
├── agent_core.log             # TriageCommander execution logs
└── agent_errors.log           # FastAPI + agent runtime error log
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM / AI** | Google Gemini 2.0 Flash (`gemini-2.0-flash`) via `google-genai ≥ 1.0.0` |
| **Search Grounding** | Google Search tool (built-in Gemini tool, zero additional config) |
| **Web Framework** | FastAPI ≥ 0.115.0 + Uvicorn (ASGI) |
| **Image Processing** | Pillow ≥ 10.0.0 (multimodal upload decoding) |
| **Env Management** | `python-dotenv` ≥ 1.0.0 |
| **Frontend** | Vanilla HTML5, CSS3 (glassmorphism), ES6 JavaScript |
| **Container** | Docker — Python 3.10-slim, non-root user |

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

### Development server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at **[http://localhost:8000](http://localhost:8000)**.

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

### Build the image

```bash
docker build -t nexus-agent .
```

### Run the test harness

```bash
docker run --env-file .env nexus-agent
```

### Run the web server

```bash
docker run --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/dispatch_output:/app/workspace/outgoing_dispatch" \
  nexus-agent \
  uvicorn main:app --host 0.0.0.0 --port 8000
```

**Security highlights in the Dockerfile:**
- Base image: `python:3.10-slim` (minimal attack surface)
- Non-root runtime user: `nexus` (uid/gid 1001)
- `PYTHONDONTWRITEBYTECODE=1` — no `.pyc` clutter in the image
- `PYTHONUNBUFFERED=1` — real-time log visibility in container

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
| `agent.py` | `PRIMARY_MODEL` | `gemini-2.0-flash` | Gemini model used for triage |
| `main.py` | `MAX_REPORT_LENGTH` | `1000` | HTTP-layer report length cap |
| `main.py` | `MAX_IMAGE_SIZE` | `10 MB` | Maximum uploaded image size |
| `agent_core.py` | `GEMINI_MODEL_NAME` | `gemini-1.5-flash-latest` | Model used by TriageCommander |

---

## Security Compliance

- **OWASP Top 10** — Injection prevention, input validation, no stack traces exposed to users
- **OWASP LLM Top 10** — Prompt injection detection with 15+ phrase patterns
- **CIS Python Benchmarks** — No `eval`, no `exec`, no `pickle`
- **Zero-Trust** — All inputs treated as hostile; all LLM outputs schema-validated before use
- **Secrets Management** — API keys loaded from `.env` via `python-dotenv`; never hardcoded

---

*Built with ❤️ for the Claw & Shield 2026 Hackathon by the NEXUS Team.*
