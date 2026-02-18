"""Wrapper to run cloudflare_harden and capture output."""
import subprocess, sys, os

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_PROJECT_ROOT)
python = os.path.join(_PROJECT_ROOT, ".venv", "Scripts", "python.exe")

# Run dry-run first
print("=" * 60)
print("RUNNING: python -m shared.cloudflare_harden (dry-run)")
print("=" * 60)
result1 = subprocess.run(
    [python, "-m", "shared.cloudflare_harden"],
    capture_output=True, text=True, timeout=60
)
output1 = result1.stdout + result1.stderr

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "cf_harden_output.txt"), "w", encoding="utf-8") as f:
    f.write("=== DRY RUN ===\n")
    f.write(f"Exit code: {result1.returncode}\n")
    f.write("--- STDOUT ---\n")
    f.write(result1.stdout)
    f.write("\n--- STDERR ---\n")
    f.write(result1.stderr)
    f.write("\n")

# Check if Zone Settings are accessible (no lock emoji)
if "\U0001f512" not in output1 and "403" not in output1:
    print("Zone Settings appear accessible, running --apply...")
    result2 = subprocess.run(
        [python, "-m", "shared.cloudflare_harden", "--apply"],
        capture_output=True, text=True, timeout=60
    )
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "cf_harden_output.txt"), "a", encoding="utf-8") as f:
        f.write("\n=== APPLY RUN ===\n")
        f.write(f"Exit code: {result2.returncode}\n")
        f.write("--- STDOUT ---\n")
        f.write(result2.stdout)
        f.write("\n--- STDERR ---\n")
        f.write(result2.stderr)
        f.write("\n")
else:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "cf_harden_output.txt"), "a", encoding="utf-8") as f:
        f.write("\n=== APPLY RUN SKIPPED ===\n")
        f.write("Zone Settings still locked (403 or lock emoji found). Skipping --apply.\n")

print("Output written to scripts/output/cf_harden_output.txt")
