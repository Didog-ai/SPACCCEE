import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK_DIR = ROOT / "playbook"

MODEL = os.environ.get("INNOVATIX_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("INNOVATIX_EFFORT", "medium")  # low | medium | high | xhigh | max
TARGET_CONTAINERS = float(os.environ.get("INNOVATIX_TARGET_CONTAINERS", "10"))
BASELINE_CONTAINERS = float(os.environ.get("INNOVATIX_BASELINE_CONTAINERS", "4"))
