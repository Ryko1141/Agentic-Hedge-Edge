"""Re-apply minification and run full hardening audit."""
import sys, os, io

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# Tee stdout to both console and file
class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()
    def flush(self):
        for s in self.streams:
            s.flush()

outfile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "minify_harden_output.txt"), "w", encoding="utf-8")
sys.stdout = Tee(sys.__stdout__, outfile)

print("=" * 60)
print("STEP 1: Re-apply minification")
print("=" * 60)
try:
    from shared.cloudflare_client import update_zone_setting, ZONE_ID
    r = update_zone_setting(ZONE_ID, 'minify', {'css': 'on', 'html': 'on', 'js': 'on'})
    print('Minify:', r.get('value', r))
except Exception as e:
    print(f'ERROR: {e}')

print()
print("=" * 60)
print("STEP 2: Full hardening audit")
print("=" * 60)

# Run the hardening module's report
sys.argv = [sys.argv[0]]  # reset args so argparse doesn't choke
from shared.cloudflare_harden import print_report
print_report(apply=False)

outfile.close()
