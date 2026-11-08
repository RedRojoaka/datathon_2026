"""Tournament entry point. The complete poker project lives in pokerbot/."""

import os
import sys
from pathlib import Path

import uvicorn

# The organizer's unchanged modules use imports relative to the bundle root.
sys.path.insert(0, str(Path(__file__).resolve().parent / "pokerbot"))
from pokerbot.agent import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5008"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
