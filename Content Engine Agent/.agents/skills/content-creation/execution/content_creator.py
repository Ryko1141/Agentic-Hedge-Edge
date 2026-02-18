#!/usr/bin/env python3
"""
content_creator.py — Content Engine Agent Content Creation

Create and manage content pieces across all formats: blog, video script,
social post, guide, case study, and thread.

Usage:
    python content_creator.py --action create --title "5 Hedging Strategies Every Funded Trader Needs" --type blog --topic "hedging education"
    python content_creator.py --action create --title "FTMO Challenge Protection Guide" --type guide --topic "prop firm tips" --target-segment "FTMO traders"
    python content_creator.py --action list-drafts
    python content_creator.py --action update-status --title "5 Hedging Strategies..." --status Approved
    python content_creator.py --action content-stats
    python content_creator.py --action idea-bank
"""

import sys, os, argparse, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

CONTENT_TYPES = ["blog", "video-script", "social-post", "guide", "case-study", "thread"]
STATUS_FLOW = ["Draft", "In-Review", "Approved", "Published", "Archived"]

PROP_FIRM_TOPICS = [
    "How drawdown protection saves funded accounts",
    "MT5 hedging setup walkthrough for beginners",
    "FTMO vs MyFundedFX: challenge rules compared",
    "Why 80% of prop firm traders fail (and how to fix it)",
    "Hedge Edge automated risk management tutorial",
    "5 signs you need a hedging strategy today",
    "The real cost of prop firm challenge resets",
    "How to survive news events on a funded account",
    "Scaling plan optimization with Hedge Edge",
    "Common hedging mistakes that blow prop accounts",
    "Prop firm drawdown rules decoded for MT4/MT5",
    "Building a trading journal that actually works",
    "Psychology of risk management for funded traders",
    "How to hedge during high-volatility sessions",
    "Case study: saving a $200k funded account from drawdown breach",
]


def create_content(args):
    """Create a new content piece in the content_calendar."""
    if args.type not in CONTENT_TYPES:
        print(f"❌ Invalid type '{args.type}'. Choose from: {', '.join(CONTENT_TYPES)}")
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = {
        "Title":          args.title,
        "Format":         args.type,
        "Topic":          args.topic or "",
        "Status":         "Draft",
        "Platform":       _infer_platform(args.type),
        "Target Segment": args.target_segment or "All Traders",
        "Created Date":   now,
    }
    add_row("content_calendar", row)
    print("=" * 65)
    print("  ✅ CONTENT PIECE CREATED")
    print("=" * 65)
    print(f"\n  Title:    {args.title}")
    print(f"  Type:     {args.type}")
    print(f"  Topic:    {row['Topic']}")
    print(f"  Platform: {row['Platform']}")
    print(f"  Segment:  {row['Target Segment']}")
    print(f"  Status:   Draft")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", f"Created content: {args.title}", "Complete", "P2",
             f"Type={args.type}, Topic={args.topic or 'N/A'}")


def _infer_platform(content_type):
    """Infer the primary distribution platform from content type."""
    mapping = {
        "blog": "Website",
        "video-script": "YouTube",
        "social-post": "Instagram",
        "guide": "Website",
        "case-study": "Website",
        "thread": "LinkedIn",
    }
    return mapping.get(content_type, "Multi-Platform")


def list_drafts(args):
    """List all content pieces currently in Draft status."""
    items = query_db("content_calendar", filter={
        "property": "Status", "select": {"equals": "Draft"}
    })
    print("=" * 65)
    print("  📝 DRAFT CONTENT PIECES")
    print("=" * 65)
    if not items:
        print("\n  No drafts in pipeline. Use --action create to add content.")
        return
    for i, item in enumerate(items, 1):
        title = item.get("Title", "Untitled")
        fmt = item.get("Format", "?")
        platform = item.get("Platform", "?")
        topic = item.get("Topic", "")
        print(f"\n  {i}. {title}")
        print(f"     Type: {fmt} | Platform: {platform}")
        if topic:
            print(f"     Topic: {topic}")
    print(f"\n{'─' * 65}")
    print(f"  Total drafts: {len(items)}")
    log_task("Content Engine", "Listed drafts", "Complete", "P3",
             f"{len(items)} drafts found")


def update_status(args):
    """Update the status of a content piece."""
    if args.status not in STATUS_FLOW:
        print(f"❌ Invalid status '{args.status}'. Choose from: {', '.join(STATUS_FLOW)}")
        return
    items = query_db("content_calendar", filter={
        "property": "Title", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Content not found: {args.title}")
        return
    item = items[0]
    old_status = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.status == "Published":
        updates["Publish Date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update_row(item["_id"], "content_calendar", updates)
    print(f"✅ {args.title}")
    print(f"   Status: {old_status} → {args.status}")
    log_task("Content Engine", f"Status update: {args.title}", "Complete", "P3",
             f"{old_status} → {args.status}")


def content_stats(args):
    """Show content production statistics."""
    items = query_db("content_calendar")
    print("=" * 65)
    print("  📊 CONTENT PRODUCTION STATS")
    print("=" * 65)
    if not items:
        print("\n  No content tracked yet.")
        return

    by_type = {}
    by_status = {}
    published_dates = []
    for item in items:
        fmt = item.get("Format", "Unknown")
        status = item.get("Status", "Unknown")
        by_type[fmt] = by_type.get(fmt, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if status == "Published" and item.get("Publish Date"):
            published_dates.append(item["Publish Date"])

    print(f"\n  Total Pieces: {len(items)}")
    print(f"\n  By Type:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"    {t:<15} {count:>3}  {bar}")
    print(f"\n  By Status:")
    for s in STATUS_FLOW:
        count = by_status.get(s, 0)
        if count:
            print(f"    {s:<15} {count:>3}")

    if len(published_dates) >= 2:
        published_dates.sort()
        first = datetime.strptime(published_dates[0], "%Y-%m-%d")
        last = datetime.strptime(published_dates[-1], "%Y-%m-%d")
        span_weeks = max((last - first).days / 7, 1)
        velocity = len(published_dates) / span_weeks
        print(f"\n  Publishing Velocity: {velocity:.1f} pieces/week")
    elif published_dates:
        print(f"\n  Publishing Velocity: {len(published_dates)} piece(s) published (need 2+ for velocity calc)")

    print(f"\n{'─' * 65}")
    log_task("Content Engine", "Content stats report", "Complete", "P3",
             f"{len(items)} total, {by_status.get('Published', 0)} published")


def idea_bank(args):
    """Generate content ideas from SEO keywords + prop-firm trending topics."""
    print("=" * 65)
    print("  💡 CONTENT IDEA BANK")
    print("=" * 65)

    # Pull SEO keywords for data-driven ideas
    seo_items = []
    try:
        seo_items = query_db("seo_keywords")
    except Exception:
        pass

    if seo_items:
        print(f"\n  SEO-Driven Ideas (from {len(seo_items)} tracked keywords):")
        for i, kw in enumerate(seo_items[:8], 1):
            keyword = kw.get("Keyword", kw.get("Title", "?"))
            volume = kw.get("Volume", kw.get("Search Volume", ""))
            vol_str = f" (vol: {volume})" if volume else ""
            print(f"    {i}. Blog/Guide: \"{keyword} — Complete Guide for Funded Traders\"{vol_str}")
    else:
        print("\n  ℹ  No SEO keywords tracked yet. Showing curated ideas.")

    print(f"\n  Prop-Firm Trending Topics:")
    for i, topic in enumerate(PROP_FIRM_TOPICS[:10], 1):
        print(f"    {i:>2}. {topic}")

    print(f"\n  Content Type Suggestions:")
    print(f"    • Tutorial video  → YouTube + repurpose to blog")
    print(f"    • Case study      → Website + LinkedIn thread")
    print(f"    • Quick tip       → Instagram reel + Twitter post")
    print(f"    • Deep dive guide → Website + email lead magnet")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", "Idea bank generated", "Complete", "P3",
             f"{len(seo_items)} SEO keywords + {len(PROP_FIRM_TOPICS)} curated topics")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Creator — Create & manage content pieces")
    parser.add_argument("--action", required=True,
                        choices=["create", "list-drafts", "update-status", "content-stats", "idea-bank"])
    parser.add_argument("--title")
    parser.add_argument("--type", choices=CONTENT_TYPES)
    parser.add_argument("--topic", default="")
    parser.add_argument("--target-segment", default="", dest="target_segment")
    parser.add_argument("--status", choices=STATUS_FLOW)
    args = parser.parse_args()
    {"create": create_content, "list-drafts": list_drafts, "update-status": update_status,
     "content-stats": content_stats, "idea-bank": idea_bank}[args.action](args)
