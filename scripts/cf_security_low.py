"""One-shot: lower Cloudflare security_level to 'low' then run harden dry-run."""
import sys, os, importlib, traceback

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

print("=" * 60)
print("STEP 1 — Set security_level to 'low'")
print("=" * 60)
try:
    from shared.cloudflare_client import set_security_level, ZONE_ID
    result = set_security_level(ZONE_ID, "low")
    print("Security level set to:", result.get("value", result))
except Exception as e:
    traceback.print_exc()
    print("FAILED:", e)

print()
print("=" * 60)
print("STEP 2 — Hardening dry-run verification")
print("=" * 60)
try:
    mod = importlib.import_module("shared.cloudflare_harden")
    if hasattr(mod, "main"):
        mod.main()
    elif hasattr(mod, "run"):
        mod.run()
    else:
        # module-level execution already happened on import
        pass
except SystemExit:
    pass
except Exception as e:
    traceback.print_exc()
    print("FAILED:", e)
