"""
=============================================================================
main.py — FastAPI Backend for Disaster Response AI Agent (Gemini Edition)
Claw & Shield 2026 Hackathon | ArmorIQ Security Compliant
=============================================================================

Endpoints:
    GET  /             → Serve static/index.html (frontend dashboard)
    POST /api/analyze  → Accept emergency report (text + optional image), return triage

Run:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Author: Disaster Response Team — Claw & Shield 2026
"""

# =============================================================================
# IMPORTS
# =============================================================================
import logging
import sys
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import analyze_emergency

# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),         # 🔊 TERMINAL OUTPUT
        logging.FileHandler("agent_errors.log"),    # 📁 FILE BACKUP
    ],
)
logger = logging.getLogger("NEXUS_API")

# =============================================================================
# CONSTANTS
# =============================================================================
BASE_DIR: Path = Path(__file__).resolve().parent
STATIC_DIR: Path = BASE_DIR / "static"
MAX_REPORT_LENGTH: int = 1000
MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================
app = FastAPI(
    title="Disaster Response AI Agent",
    description="AI-powered emergency triage system — Claw & Shield 2026",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# =============================================================================
# MOUNT STATIC FILES
# =============================================================================
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =============================================================================
# GLOBAL EXCEPTION HANDLER
# =============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.critical("💥 UNHANDLED EXCEPTION on %s: %s", request.url.path, type(exc).__name__)
    logger.exception("Full traceback:")
    traceback.print_exc()  # FORCE TERMINAL DUMP
    return JSONResponse(
        status_code=500,
        content={"error": "Service unavailable. Try later."},
    )


# =============================================================================
# ROUTE: GET / — Serve the frontend dashboard
# =============================================================================
# =============================================================================
# STARTUP PROBE — Test Gemini connectivity on boot
# =============================================================================
@app.on_event("startup")
async def startup_probe():
    """Probe Gemini client at startup to catch config errors immediately."""
    logger.info("🚀 NEXUS STARTUP: Probing Gemini client...")
    try:
        from agent import _get_gemini_client
        client = _get_gemini_client()
        if client is None:
            logger.critical("💥 NEXUS STARTUP: Gemini client returned None — check API key in .env!")
        else:
            logger.info("✅ NEXUS STARTUP: Gemini client initialized OK")
    except Exception:
        logger.critical("💥 NEXUS STARTUP: Gemini probe FAILED")
        traceback.print_exc()


@app.get("/")
async def serve_frontend() -> FileResponse:
    index_path: Path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        logger.error("index.html not found at %s", index_path)
        return JSONResponse(
            status_code=500,
            content={"error": "Frontend not available."},
        )
    return FileResponse(str(index_path), media_type="text/html")


# =============================================================================
# ROUTE: POST /api/analyze — Analyze emergency report (text + optional image)
# Accepts multipart form data:
#   - report: str (required) — emergency description text
#   - image: UploadFile (optional) — disaster photo for visual analysis
# =============================================================================
@app.post("/api/analyze")
async def analyze_report(
    report: str = Form(...),
    image: Optional[UploadFile] = File(None),
) -> JSONResponse:
    try:
        logger.debug("📥 /api/analyze HIT — report len=%d, image=%s", len(report), bool(image and image.filename))

        # ----- Validate report text -----
        if not isinstance(report, str) or not report.strip():
            logger.warning("⚠️ Empty report rejected")
            return JSONResponse(
                status_code=400,
                content={"error": "Emergency report cannot be empty."},
            )

        if len(report) > MAX_REPORT_LENGTH:
            logger.warning("⚠️ Report too long: %d chars", len(report))
            return JSONResponse(
                status_code=400,
                content={"error": f"Report exceeds {MAX_REPORT_LENGTH} character limit."},
            )

        # ----- Handle optional image -----
        image_bytes: Optional[bytes] = None
        image_mime: Optional[str] = None

        if image and image.filename:
            content_type = image.content_type or ""
            logger.debug("📸 Image received: %s (%s)", image.filename, content_type)
            if not content_type.startswith("image/"):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Uploaded file must be an image (JPEG, PNG, WebP)."},
                )

            image_bytes = await image.read()
            if len(image_bytes) > MAX_IMAGE_SIZE:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Image exceeds 10 MB size limit."},
                )

            image_mime = content_type

        # ----- Call the analysis pipeline -----
        logger.info("🧠 Calling analyze_emergency pipeline...")
        result: dict = analyze_emergency(report, image_bytes, image_mime)
        logger.info("✅ Pipeline returned severity=%s", result.get("severity", "???"))

        return JSONResponse(status_code=200, content=result)

    except Exception as exc:
        logger.critical("💥 /api/analyze CRASH: %s — %s", type(exc).__name__, str(exc))
        logger.exception("Full traceback:")
        traceback.print_exc()  # FORCE TERMINAL DUMP
        return JSONResponse(
            status_code=500,
            content={"error": "Service unavailable. Try later."},
        )
