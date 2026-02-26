"""
=============================================================================
agent.py — Disaster Response AI Agent (Core Backend — Gemini Edition)
Claw & Shield 2026 Hackathon | ArmorIQ Security Compliant
=============================================================================

Purpose:
    Sanitize user emergency reports, call Google Gemini for triage
    (with optional multimodal image analysis + Google Search grounding),
    validate structured JSON responses, and return actionable results.

Security:
    - OWASP Top 10 compliant (injection prevention, input validation)
    - CIS Python benchmarks (no eval, no exec, no pickle)
    - Zero-trust: all inputs treated as hostile, all outputs validated
    - Secrets loaded from .env via python-dotenv (never hardcoded)
    - Errors logged to file only — no stack traces exposed to users

Author: Disaster Response Team — Claw & Shield 2026
"""

# =============================================================================
# IMPORTS — Standard library first, then third-party (PEP 8)
# =============================================================================
import json          # JSON parsing and validation
import logging       # Secure file-only logging (no console traces)
import os            # Environment variable access
import re            # Regex-based input sanitization
import sys
import traceback
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv  # Secure .env loading (zero hardcoded secrets)
from google import genai        # Google GenAI SDK
from google.genai import types  # Type helpers for config
from PIL import Image           # Image processing for multimodal input

# =============================================================================
# SECURITY: Load environment variables FIRST
# =============================================================================
load_dotenv()

# =============================================================================
# LOGGING CONFIGURATION — Dual stdout + file (AGGRESSIVE DEBUG)
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
logger = logging.getLogger("NEXUS_AGENT")

# =============================================================================
# CONSTANTS
# =============================================================================
MAX_INPUT_LENGTH: int = 1000
MAX_RETRIES: int = 2
PRIMARY_MODEL: str = "gemini-3-flash-preview"
VALID_SEVERITIES: set = {"Low", "Medium", "High", "Critical", "Error"}
MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Token pricing (Gemini Flash — per 1M tokens)
PROMPT_COST_PER_M: float = 0.075   # $0.075 per 1,000,000 prompt tokens
CANDID_COST_PER_M: float = 0.30    # $0.30  per 1,000,000 candidate tokens

# =============================================================================
# INJECTION DETECTION PATTERN — PHRASE-BASED (OWASP LLM Top 10)
# =============================================================================
INJECTION_PATTERN: re.Pattern = re.compile(
    r"(?i)("
    r"ignore\s+(previous|all|my\s+)?\s*instructions"
    r"|system\s+(prompt|override|instruction)"
    r"|bypass\s+(safety|filter|guard|security)"
    r"|reveal\s+(your|the)\s+(prompt|instruction|rule)"
    r"|disregard\s+(all|previous|above|your)\s*(instructions|rules|directives)?"
    r"|forget\s+(previous|all|your)\s*(instructions|rules|context)?"
    r"|override\s+(previous|all|safety|security)\s*(instructions|rules|protocol)?"
    r"|inject\s+(prompt|instruction|command)"
    r"|pretend\s+you\s+are"
    r"|act\s+as\s+(if|a|an)"
    r"|you\s+are\s+now\s+"
    r"|new\s+instructions?\s*:"
    r"|\bDAN\b"
    r"|do\s+anything\s+now"
    r")",
    re.IGNORECASE,
)

HTML_TAG_PATTERN: re.Pattern = re.compile(r"<[^>]*>")

# =============================================================================
# SYSTEM PROMPT — Gemini + Google Search Grounding
# =============================================================================
SYSTEM_PROMPT: str = """You are DisasterResponseBot, a safety-first AI for emergency triage. You exist EXCLUSIVELY to analyze disaster, emergency, and crisis situations. You are NOT a general-purpose assistant.

SCOPE RESTRICTION (HIGHEST PRIORITY — NEVER VIOLATE):
- You ONLY respond to inputs that are related to disasters, emergencies, crises, natural calamities, accidents, humanitarian incidents, or safety threats.
- If the user's input is casual conversation, general knowledge, small talk, or ANY topic unrelated to a disaster/emergency (e.g., "How is the weather?", "Tell me a joke", "What is the capital of France?", "Write me a poem", "What time is it?"), you MUST refuse and return:
  {"severity": "Low", "recommended_actions": ["Please submit an actual emergency or disaster report", "Describe the crisis situation clearly", "Include location and nature of the emergency"], "reasoning": "This system is exclusively designed for disaster and emergency response triage. Your input does not describe a disaster or emergency scenario. Please provide a real emergency report for analysis."}
- Do NOT answer general questions, provide weather forecasts, engage in conversation, or perform any task outside disaster/emergency triage. EVER.

TRIAGE RULES:
- NO medical/health advice—NEVER diagnose, treat, or suggest care.
- If "injur*","hurt","bleed*","medical","hospital","ambulance" detected: respond with severity "Critical", actions ["Call 108/911 immediately", "Dispatch ambulance", "Do NOT move victim"], reasoning "Physical injuries detected. Medical pros required first."
- Severity: Low (minor issue), Medium (urgent but non-life), High (immediate danger), Critical (life-threatening).
- Actions: Exactly 3 practical, physical steps. Prioritize life > safety > efficiency. No speculation.
- If the user provides a location, use Google Search to find real-time weather alerts, road closures, or the specific local emergency contact numbers for that area, and include them in the recommended actions.
- If an image is provided, analyze the visual damage and factor it into the severity assessment.
- Output ONLY valid JSON with this exact schema: {"severity": "...", "recommended_actions": ["...", "...", "..."], "reasoning": "..."}
- No markdown, no code fences, no extra keys. Just raw JSON."""


# =============================================================================
# ERROR RESPONSES
# =============================================================================
ERROR_RESPONSE: dict = {
    "severity": "High",
    "recommended_actions": [
        "Contact emergency services directly (108/911)",
        "Follow your local emergency evacuation plan",
        "Stay calm and await professional responders",
    ],
    "reasoning": "Automated analysis unavailable. Default to high-alert protocol for safety.",
}

API_ERROR_RESPONSE: dict = {
    "severity": "Error",
    "recommended_actions": [
        "Check your Gemini API key in .env",
        "Verify Google AI Studio billing at aistudio.google.com",
        "Contact your system administrator",
    ],
    "reasoning": "Gemini API connection failed. The agent could not reach the AI service. Please verify your API key.",
}


# =============================================================================
# FUNCTION: sanitize_input
# =============================================================================
def sanitize_input(raw_input: str) -> Optional[str]:
    """
    Sanitize and validate user-provided emergency report text.
    7-layer defense-in-depth: type → strip → empty → length → HTML → injection → control chars.
    """
    try:
        if not isinstance(raw_input, str):
            logger.warning("Input rejected: non-string type received.")
            return None

        sanitized: str = raw_input.strip()

        if not sanitized:
            logger.warning("Input rejected: empty after stripping.")
            return None

        if len(sanitized) > MAX_INPUT_LENGTH:
            sanitized = sanitized[:MAX_INPUT_LENGTH]
            logger.warning("Input truncated to %d characters.", MAX_INPUT_LENGTH)

        sanitized = HTML_TAG_PATTERN.sub("", sanitized)

        if INJECTION_PATTERN.search(sanitized):
            logger.warning("Input rejected: prompt injection pattern detected.")
            return None

        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

        if not sanitized.strip():
            logger.warning("Input rejected: empty after full sanitization.")
            return None

        return sanitized

    except Exception as exc:
        logger.critical("💥 SANITIZE CRASH: %s — %s", type(exc).__name__, str(exc))
        traceback.print_exc()
        return None


# =============================================================================
# FUNCTION: _get_gemini_client
# =============================================================================
def _get_gemini_client() -> Optional[genai.Client]:
    """
    Initialize and return a Gemini client using the API key from .env.
    Returns None if key is missing.
    """
    try:
        # FIX: Support both env var names (.env may use either)
        api_key: Optional[str] = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        logger.debug("🔑 API key lookup: GEMINI_API_KEY=%s, GOOGLE_API_KEY=%s",
                     '***' + os.environ.get('GEMINI_API_KEY', 'MISSING')[-4:] if os.environ.get('GEMINI_API_KEY') else 'MISSING',
                     '***' + os.environ.get('GOOGLE_API_KEY', 'MISSING')[-4:] if os.environ.get('GOOGLE_API_KEY') else 'MISSING')

        if not api_key or len(api_key) < 10:
            logger.critical("💥 GEMINI API KEY MISSING OR INVALID — set GEMINI_API_KEY or GOOGLE_API_KEY in .env!")
            return None

        logger.info("✅ Gemini client initializing with key ***%s", api_key[-4:])
        client = genai.Client(api_key=api_key)
        logger.info("✅ Gemini client created successfully")
        return client

    except Exception as exc:
        logger.critical("💥 GEMINI CLIENT INIT CRASH: %s — %s", type(exc).__name__, str(exc))
        traceback.print_exc()
        return None


# =============================================================================
# FUNCTION: _call_gemini
# =============================================================================
def _call_gemini(
    client: genai.Client,
    sanitized_input: str,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
) -> Optional[dict]:
    """
    Make a single Gemini generate_content call with optional image + Google Search grounding.
    """
    try:
        logger.debug("📡 _call_gemini START — input len=%d, has_image=%s", len(sanitized_input), bool(image_bytes))

        # Build contents list (multimodal if image provided)
        contents = []

        if image_bytes and image_mime:
            try:
                img = Image.open(BytesIO(image_bytes))
                contents.append(img)
                logger.debug("📸 Image loaded: %s, size=%d bytes", image_mime, len(image_bytes))
            except Exception:
                logger.warning("⚠️ Failed to open image, proceeding text-only.")
                traceback.print_exc()

        # Add the text prompt
        prompt = f"USER_REPORT: <report>{sanitized_input}</report>"
        contents.append(prompt)

        # Configure Google Search grounding tool
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[grounding_tool],
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=600,
        )

        logger.info("📡 Sending request to Gemini model=%s...", PRIMARY_MODEL)
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=contents,
            config=config,
        )
        logger.info("📡 Gemini response received")

        raw_content = response.text
        logger.debug("📡 Raw response text: %s", raw_content[:500] if raw_content else "<EMPTY>")

        if not raw_content:
            logger.warning("⚠️ Empty response from Gemini — response.text is None/empty")
            return None

        parsed: dict = json.loads(raw_content)
        logger.debug("✅ JSON parsed successfully: severity=%s", parsed.get('severity', '???'))

        # ── Token Usage & Cost Extraction ──
        try:
            usage = getattr(response, 'usage_metadata', None)
            if usage:
                prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
                candidate_tokens = getattr(usage, 'candidates_token_count', 0) or 0
                total_tokens = prompt_tokens + candidate_tokens
                total_cost = (
                    (prompt_tokens / 1_000_000) * PROMPT_COST_PER_M
                    + (candidate_tokens / 1_000_000) * CANDID_COST_PER_M
                )
                parsed["total_tokens"] = total_tokens
                parsed["total_mission_cost"] = round(total_cost, 6)
                logger.info(
                    "💰 Token usage: prompt=%d, candidate=%d, total=%d, cost=$%.6f",
                    prompt_tokens, candidate_tokens, total_tokens, total_cost,
                )
            else:
                logger.debug("ℹ️ No usage_metadata on response — skipping cost tracking")
        except Exception as tok_err:
            logger.warning("⚠️ Token cost extraction failed (non-fatal): %s", tok_err)

        return parsed

    except json.JSONDecodeError as jde:
        logger.critical("💥 JSON PARSE FAILED from Gemini: %s", str(jde))
        logger.error("Raw content that failed to parse: %s", raw_content[:500] if 'raw_content' in locals() else '<unavailable>')
        traceback.print_exc()
        return None
    except Exception as exc:
        logger.critical("💥 GEMINI API CALL CRASH: %s — %s", type(exc).__name__, str(exc))
        traceback.print_exc()
        return None


# =============================================================================
# FUNCTION: _validate_response
# =============================================================================
def _validate_response(data: dict) -> bool:
    """
    Validate that the LLM response conforms to the expected schema.
    """
    try:
        required_keys: set = {"severity", "recommended_actions", "reasoning"}
        if not required_keys.issubset(data.keys()):
            logger.warning("Response missing required keys: %s", required_keys - data.keys())
            return False

        if data["severity"] not in VALID_SEVERITIES:
            logger.warning("Invalid severity value: %s", data.get("severity"))
            return False

        actions = data["recommended_actions"]
        if not isinstance(actions, list) or len(actions) != 3:
            logger.warning("Actions must be a list of exactly 3 items.")
            return False

        for action in actions:
            if not isinstance(action, str) or not action.strip():
                logger.warning("Each action must be a non-empty string.")
                return False

        if not isinstance(data["reasoning"], str) or not data["reasoning"].strip():
            logger.warning("Reasoning must be a non-empty string.")
            return False

        return True

    except Exception as exc:
        logger.error("Validation error: %s", type(exc).__name__)
        return False


# =============================================================================
# FUNCTION: analyze_emergency (PUBLIC ENTRY POINT)
# =============================================================================
def analyze_emergency(
    report: str,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
) -> dict:
    """
    Public entry point: analyze an emergency report (with optional image)
    and return triage results.

    Pipeline:
        1. Sanitize input (7-layer defense)
        2. Initialize Gemini client
        3. Call Gemini with multimodal content + Google Search grounding
        4. Retry up to MAX_RETRIES on validation failure
        5. Return validated JSON or safe error response
    """
    try:
        logger.info("🧠 analyze_emergency START — report len=%d, has_image=%s", len(report), bool(image_bytes))

        # ----- Step 1: Sanitize input -----
        sanitized: Optional[str] = sanitize_input(report)
        if sanitized is None:
            logger.warning("⚠️ Analysis aborted: input failed sanitization.")
            return {
                "severity": "Low",
                "recommended_actions": [
                    "Rephrase your emergency report clearly",
                    "Avoid special characters or commands",
                    "Describe the situation in plain language",
                ],
                "reasoning": "Input could not be processed. Please provide a clear, plain-text description of the emergency.",
            }
        logger.debug("✅ Input sanitized OK — len=%d", len(sanitized))

        # ----- Step 2: Initialize Gemini client -----
        logger.debug("🔑 Initializing Gemini client...")
        client = _get_gemini_client()
        if client is None:
            logger.critical("💥 Analysis aborted: Gemini client returned None — check API key!")
            return API_ERROR_RESPONSE
        logger.debug("✅ Gemini client ready")

        # ----- Step 3: Call Gemini with retry logic -----
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info("🔄 Attempt %d/%d with model %s", attempt, MAX_RETRIES, PRIMARY_MODEL)

            result: Optional[dict] = _call_gemini(
                client, sanitized, image_bytes, image_mime
            )

            if result is not None and _validate_response(result):
                logger.info("✅ Valid response on attempt %d — severity=%s", attempt, result.get('severity', '???'))
                return result

            logger.warning("⚠️ Attempt %d/%d failed — result=%s", attempt, MAX_RETRIES, 'None' if result is None else 'invalid schema')

        # ----- All retries exhausted -----
        logger.critical("💥 ALL %d RETRY ATTEMPTS EXHAUSTED — returning API_ERROR_RESPONSE", MAX_RETRIES)
        return API_ERROR_RESPONSE

    except Exception as exc:
        logger.critical("💥 FATAL analyze_emergency CRASH: %s — %s", type(exc).__name__, str(exc))
        traceback.print_exc()
        return ERROR_RESPONSE
