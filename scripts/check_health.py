"""Quick script to check service health and write results to file."""
import sys, os

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from shared.dashboard import get_service_health

health = get_service_health()
lines = []
for k, v in health.items():
    lines.append(f"{k}: {v}")
    print(f"{k}: {v}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "health_output.txt"), "w") as f:
    f.write("\n".join(lines))
