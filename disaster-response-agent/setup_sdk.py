"""
=============================================================================
setup_sdk.py — ArmorIQ OpenClaw SDK Configuration Generator
Claw & Shield 2026 Hackathon | NEXUS Disaster Response Agent
=============================================================================

PURPOSE:
    Initialises the ArmorIQ OpenClaw SDK by writing the required JSON
    configuration file to ~/.openclaw/openclaw.json.

    This is called ONCE at application startup (imported from agent_core.py).
    It reads API credentials from environment variables (.env) and falls back
    to safe development defaults so the app boots even without a live key.

HACKATHON NOTE:
    ArmorIQ is a Node.js plugin.  This Python file generates the JSON config
    that the `openclaw` CLI reads.  The enforcement_middleware then calls
    the CLI via subprocess to get official SDK policy verdicts.
=============================================================================
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("NEXUS_SDK_SETUP")

# Canonical config path expected by the OpenClaw CLI
OPENCLAW_CONFIG_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG_FILE = OPENCLAW_CONFIG_DIR / "openclaw.json"


def initialize_armoriq() -> Path:
    """
    Create (or overwrite) ~/.openclaw/openclaw.json with ArmorIQ plugin config.

    Environment variables (read from .env at runtime):
        ARMORIQ_API_KEY   — ArmorIQ API key   (default: ak_dev_nexus_2026)
        ARMORIQ_USER_ID   — User identifier   (default: nexus-user-001)
        ARMORIQ_AGENT_ID  — Agent identifier   (default: nexus-triage-cmd)

    Returns:
        Path to the written config file.
    """
    api_key  = os.getenv("ARMORIQ_API_KEY",  "ak_dev_nexus_2026")
    user_id  = os.getenv("ARMORIQ_USER_ID",  "nexus-user-001")
    agent_id = os.getenv("ARMORIQ_AGENT_ID", "nexus-triage-cmd")

    config = {
        "plugins": {
            "entries": {
                "armoriq": {
                    "enabled": True,
                    "apiKey": api_key,
                    "userId": user_id,
                    "agentId": agent_id,
                    "contextId": "disaster-response",
                    "validitySeconds": 120,
                    "policy": {
                        "allow": [
                            "write",
                            "read",
                            "web_search",
                            "logistics_dispatch",
                        ],
                        "deny": [
                            "medical_dispatch",
                            "bash",
                            "exec",
                            "prescribe",
                            "diagnose",
                        ],
                    },
                },
            },
        },
    }

    # Write config
    OPENCLAW_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(OPENCLAW_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    logger.info(
        "🔧 ArmorIQ SDK config written → %s  (apiKey=%s…, userId=%s, agentId=%s)",
        OPENCLAW_CONFIG_FILE,
        api_key[:12],
        user_id,
        agent_id,
    )
    return OPENCLAW_CONFIG_FILE


# ── Self-test when run directly ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = initialize_armoriq()
    print(f"\n✅ Config created at {path}")
    print(json.dumps(json.loads(path.read_text()), indent=2))
