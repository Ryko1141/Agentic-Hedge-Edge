"""
Populate Notion email_sequences DB with 20 segment-tailored email templates.
4 segments × 5 emails = 20 rows.

Usage:
    python scripts/notion_populate_segment_templates.py
"""
import os, sys, re, html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from shared.email_templates import ALL_SEGMENTS, SEGMENT_A, SEGMENT_B, SEGMENT_C, SEGMENT_D
from shared.notion_client import add_row, query_db

# Map internal key to human-readable email name
KEY_LABELS = {
    "welcome":        "Welcome Email (Day 0)",
    "day1_education": "Education Email (Day 1)",
    "day3_broker":    "Broker Setup (Day 3)",
    "day5_product":   "Product Walkthrough (Day 5)",
    "day7_offer":     "Founding Member Offer (Day 7)",
}


def html_to_plain(raw_html: str) -> str:
    """Strip HTML tags and convert to readable plain text."""
    text = re.sub(r'<style[^>]*>.*?</style>', '', raw_html, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</?(p|div|h[1-6]|li|ol|ul|tr|td|th|table)[^>]*>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    lines = [l.strip() for l in text.splitlines()]
    text = '\n'.join(l for l in lines if l)
    # Trim to Notion limit
    if len(text) > 1900:
        text = text[:1900] + '...'
    return text


def main():
    print("=" * 55)
    print("  POPULATING NOTION — 20 SEGMENT EMAIL TEMPLATES")
    print("=" * 55)

    # Check existing rows to avoid duplicates
    existing = query_db("email_sequences")
    existing_names = {r.get("Name", "") for r in existing}
    print(f"\n  Existing rows: {len(existing)}")

    created = 0

    for seg_key, seg_data in ALL_SEGMENTS.items():
        seg_label = seg_data["segment_label"]
        templates = seg_data["templates"]

        print(f"\n── {seg_label} ({seg_key}) ──")

        for tpl_key, tpl in templates.items():
            row_name = f"{KEY_LABELS.get(tpl_key, tpl_key)} — {seg_label}"

            if row_name in existing_names:
                print(f"  ⏭️  Already exists: {row_name}")
                continue

            # Render HTML with placeholder name and extract plain text preview
            raw_html = tpl["html"]("{{name}}")
            plain_text = html_to_plain(raw_html)

            row = {
                "Name":       row_name,
                "Status":     "Active",
                "Subject Line": tpl["subject"],
                "Trigger":    "Signup",
                "Notes":      plain_text,
            }

            try:
                add_row("email_sequences", row)
                created += 1
                print(f"  ✅ Created: {row_name} ({len(plain_text)} chars)")
            except Exception as e:
                print(f"  ❌ Failed: {row_name} — {e}")

    print(f"\n  Done. Created {created} new template rows.")


if __name__ == "__main__":
    main()
