"""Short.io — Archive old links, create distribution tracking links on link.hedgedge.info -> hedgedge.info"""
import sys, os

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from shared.shortio_client import list_links, archive_link, create_link

SHORTIO_DOMAIN = "link.hedgedge.info"  # The configured Short.io domain
WEBSITE        = "https://hedgedge.info"  # The actual landing page
DOMAIN_ID      = 1661144

# ── Step 1: Archive old links ──
print("=" * 60)
print("STEP 1 — Archive old links (wrong destination)")
print("=" * 60)

old_links = list_links(domain_id=DOMAIN_ID, limit=150)
for link in old_links:
    lid = link.get("idString")
    path = link.get("path")
    target = link.get("originalURL")
    try:
        archive_link(lid)
        print(f"  ARCHIVED: {SHORTIO_DOMAIN}/{path} -> {target}")
    except Exception as e:
        print(f"  FAILED: {path} — {e}")

# ── Step 2: Create distribution tracking links ──
print()
print("=" * 60)
print(f"STEP 2 — Creating distribution links ({SHORTIO_DOMAIN} -> {WEBSITE})")
print("=" * 60)

LINKS = [
    # ── Channel attribution (landing page / waitlist) ──
    {
        "url": WEBSITE,
        "path": "reddit",
        "title": "Reddit — Landing Page",
        "tags": ["channel", "reddit"],
        "utm_source": "reddit",
        "utm_medium": "social",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "youtube",
        "title": "YouTube — Landing Page",
        "tags": ["channel", "youtube"],
        "utm_source": "youtube",
        "utm_medium": "video",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "forums",
        "title": "Forums (BabyPips, ForexFactory) — Landing Page",
        "tags": ["channel", "forums"],
        "utm_source": "forums",
        "utm_medium": "referral",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "twitter",
        "title": "Twitter/X — Landing Page",
        "tags": ["channel", "twitter"],
        "utm_source": "twitter",
        "utm_medium": "social",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "email",
        "title": "Email Campaigns — Landing Page",
        "tags": ["channel", "email"],
        "utm_source": "email",
        "utm_medium": "email",
        "utm_campaign": "nurture",
    },
    {
        "url": WEBSITE,
        "path": "telegram",
        "title": "Telegram Groups — Landing Page",
        "tags": ["channel", "telegram"],
        "utm_source": "telegram",
        "utm_medium": "social",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "linkedin",
        "title": "LinkedIn — Landing Page",
        "tags": ["channel", "linkedin"],
        "utm_source": "linkedin",
        "utm_medium": "social",
        "utm_campaign": "organic",
    },
    {
        "url": WEBSITE,
        "path": "tiktok",
        "title": "TikTok — Landing Page",
        "tags": ["channel", "tiktok"],
        "utm_source": "tiktok",
        "utm_medium": "social",
        "utm_campaign": "organic",
    },
    # ── Discord (external share link) ──
    {
        "url": "https://discord.gg/hedgeedge",
        "path": "discord",
        "title": "Discord Invite — External Share",
        "tags": ["channel", "discord"],
        "utm_source": "shortlink",
        "utm_medium": "referral",
        "utm_campaign": "community",
    },
    # ── Influencer/partner template ──
    {
        "url": WEBSITE,
        "path": "partner",
        "title": "Influencer/Partner — Landing Page",
        "tags": ["channel", "influencer"],
        "utm_source": "partner",
        "utm_medium": "referral",
        "utm_campaign": "influencer",
    },
]

created = []
for spec in LINKS:
    try:
        result = create_link(
            spec["url"],
            domain=SHORTIO_DOMAIN,
            path=spec["path"],
            title=spec["title"],
            tags=spec["tags"],
            utm_source=spec["utm_source"],
            utm_medium=spec["utm_medium"],
            utm_campaign=spec["utm_campaign"],
        )
        short = result.get("shortURL", "?")
        created.append({"path": spec["path"], "short": short, "target": spec["url"]})
        print(f"  CREATED: {short}  ->  {spec['url']}  [{spec['title']}]")
    except Exception as e:
        print(f"  FAILED: {spec['path']} — {e}")

# ── Summary ──
print()
print("=" * 60)
print(f"DONE — {len(created)}/{len(LINKS)} distribution links created")
print("=" * 60)
print()
print("Share these links to track which channels drive traffic:")
print()
for c in created:
    print(f"  {c['short']:<45s}  {c['target']}")
