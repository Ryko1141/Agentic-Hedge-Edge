#!/usr/bin/env python3
"""
instagram_manager.py — Content Engine Agent Instagram Management

Manage Instagram content scheduling, posting pipeline, and engagement tracking.

Usage:
    python instagram_manager.py --action plan-post --caption "Stop losing funded accounts to drawdown 🛡️" --type reel --scheduled-date 2026-02-25 --hashtags "#proptrading #hedging #fundedtrader"
    python instagram_manager.py --action queue
    python instagram_manager.py --action post-stats --post-id "IG-20260218" --likes 342 --comments 28 --shares 15 --saves 89 --reach 4200
    python instagram_manager.py --action engagement-report
    python instagram_manager.py --action hashtag-research
"""

import sys, os, argparse, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

POST_TYPES = ["feed", "reel", "story", "carousel"]

HASHTAG_SETS = {
    "hedging": [
        "#hedging", "#riskmanagement", "#drawdownprotection", "#tradingtools",
        "#proptrading", "#fundedtrader", "#forexhedging", "#hedgeedge",
        "#protectyouraccount", "#tradingtech",
    ],
    "prop-firm": [
        "#propfirm", "#fundedaccount", "#ftmo", "#myfundedfx", "#thetradingpit",
        "#propfirmchallenge", "#propfirmtrader", "#fundedtrading",
        "#challengepassed", "#propfirmlife",
    ],
    "trading-education": [
        "#tradingeducation", "#forexeducation", "#tradingmindset",
        "#tradingpsychology", "#tradingtips", "#learntrading",
        "#mt5", "#mt4", "#metatrader", "#tradingstrategy",
    ],
    "lifestyle": [
        "#traderlife", "#financialfreedom", "#tradinglifestyle",
        "#daytrader", "#forextrader", "#tradingmotivation",
        "#workfromanywhere", "#passiveincome",
    ],
}


def plan_post(args):
    """Plan an Instagram post and add it to the content calendar."""
    if args.type not in POST_TYPES:
        print(f"❌ Invalid type '{args.type}'. Choose from: {', '.join(POST_TYPES)}")
        return
    row = {
        "Title":          args.caption[:80] + ("..." if len(args.caption) > 80 else ""),
        "Platform":       "Instagram",
        "Format":         args.type.capitalize(),
        "Status":         "Scheduled",
        "Publish Date":   args.scheduled_date or "",
        "Topic":          args.caption,
        "SEO Keyword":    args.hashtags or "",
    }
    add_row("content_calendar", row)
    print("=" * 65)
    print("  📸 INSTAGRAM POST PLANNED")
    print("=" * 65)
    print(f"\n  Type:      {args.type}")
    print(f"  Caption:   {args.caption[:100]}{'...' if len(args.caption) > 100 else ''}")
    print(f"  Scheduled: {args.scheduled_date or 'TBD'}")
    if args.hashtags:
        print(f"  Hashtags:  {args.hashtags}")
    print(f"  Status:    Scheduled")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", f"IG post planned: {row['Title']}", "Complete", "P2",
             f"Type={args.type}, Date={args.scheduled_date or 'TBD'}")


def queue(args):
    """Show the Instagram posting queue (upcoming scheduled posts)."""
    items = query_db("content_calendar", filter={
        "and": [
            {"property": "Platform", "select": {"equals": "Instagram"}},
            {"property": "Status", "select": {"does_not_equal": "Published"}},
        ]
    })
    print("=" * 65)
    print("  📋 INSTAGRAM POSTING QUEUE")
    print("=" * 65)
    if not items:
        print("\n  No upcoming Instagram posts in queue.")
        print("  Use --action plan-post to schedule content.")
        return
    items.sort(key=lambda x: x.get("Publish Date", "9999-12-31"))
    for i, item in enumerate(items, 1):
        title = item.get("Title", "Untitled")
        date = item.get("Publish Date", "TBD")
        fmt = item.get("Format", "?")
        status = item.get("Status", "?")
        print(f"\n  {i}. [{fmt}] {title}")
        print(f"     Date: {date} | Status: {status}")
    print(f"\n{'─' * 65}")
    print(f"  Total queued: {len(items)} posts")
    log_task("Content Engine", "IG queue viewed", "Complete", "P3",
             f"{len(items)} posts in queue")


def post_stats(args):
    """Record engagement stats for an Instagram post."""
    items = query_db("content_calendar", filter={
        "and": [
            {"property": "Platform", "select": {"equals": "Instagram"}},
        ]
    })
    # Find by post-id convention or most recent
    target = None
    for item in items:
        if args.post_id and args.post_id in (item.get("Title", ""), item.get("URL", "")):
            target = item
            break
    if not target and items:
        target = items[-1]  # default to most recent
    if not target:
        print(f"❌ No Instagram posts found. Plan a post first.")
        return

    updates = {}
    engagement_total = 0
    if args.likes:    updates["Likes"] = args.likes;    engagement_total += args.likes
    if args.comments: updates["Comments"] = args.comments; engagement_total += args.comments
    if args.shares:   updates["Shares"] = args.shares;  engagement_total += args.shares
    if args.saves:    updates["Saves"] = args.saves;    engagement_total += args.saves
    if args.reach:    updates["Reach"] = args.reach

    engagement_rate = (engagement_total / args.reach * 100) if args.reach else 0
    updates["Engagement Rate"] = round(engagement_rate, 2)

    update_row(target["_id"], "content_calendar", updates)
    print("=" * 65)
    print("  📊 POST ENGAGEMENT RECORDED")
    print("=" * 65)
    print(f"\n  Post:       {target.get('Title', '?')}")
    if args.likes:    print(f"  Likes:      {args.likes:,}")
    if args.comments: print(f"  Comments:   {args.comments:,}")
    if args.shares:   print(f"  Shares:     {args.shares:,}")
    if args.saves:    print(f"  Saves:      {args.saves:,}")
    if args.reach:    print(f"  Reach:      {args.reach:,}")
    print(f"  Eng. Rate:  {engagement_rate:.2f}%")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", f"IG stats: {target.get('Title', '?')}", "Complete", "P3",
             f"Reach={args.reach or 0}, ER={engagement_rate:.2f}%")


def engagement_report(args):
    """Aggregate Instagram engagement metrics across all posts."""
    items = query_db("content_calendar", filter={
        "property": "Platform", "select": {"equals": "Instagram"}
    })
    print("=" * 65)
    print("  📈 INSTAGRAM ENGAGEMENT REPORT")
    print("=" * 65)
    if not items:
        print("\n  No Instagram content tracked yet.")
        return

    total = len(items)
    published = [i for i in items if i.get("Status") == "Published"]
    total_likes = sum(int(i.get("Likes", 0) or 0) for i in items)
    total_comments = sum(int(i.get("Comments", 0) or 0) for i in items)
    total_reach = sum(int(i.get("Reach", 0) or 0) for i in items)
    total_saves = sum(int(i.get("Saves", 0) or 0) for i in items)
    total_shares = sum(int(i.get("Shares", 0) or 0) for i in items)

    tracked = [i for i in items if i.get("Reach")]
    avg_likes = total_likes / len(tracked) if tracked else 0
    avg_comments = total_comments / len(tracked) if tracked else 0
    avg_reach = total_reach / len(tracked) if tracked else 0

    print(f"\n  Total Posts:    {total}")
    print(f"  Published:      {len(published)}")
    print(f"\n  Engagement Totals:")
    print(f"    Likes:        {total_likes:,}")
    print(f"    Comments:     {total_comments:,}")
    print(f"    Shares:       {total_shares:,}")
    print(f"    Saves:        {total_saves:,}")
    print(f"    Total Reach:  {total_reach:,}")
    if tracked:
        print(f"\n  Averages (per tracked post):")
        print(f"    Avg Likes:    {avg_likes:,.1f}")
        print(f"    Avg Comments: {avg_comments:,.1f}")
        print(f"    Avg Reach:    {avg_reach:,.1f}")

    # Best performing post type
    by_type = {}
    for item in items:
        fmt = item.get("Format", "Unknown")
        eng = int(item.get("Likes", 0) or 0) + int(item.get("Comments", 0) or 0)
        by_type.setdefault(fmt, []).append(eng)
    if by_type:
        print(f"\n  By Post Type:")
        for fmt, engagements in sorted(by_type.items(), key=lambda x: -sum(x[1])):
            avg_e = sum(engagements) / len(engagements)
            print(f"    {fmt:<12} {len(engagements)} posts | avg engagement: {avg_e:,.1f}")

    print(f"\n  Optimal Posting Times (prop-firm niche):")
    print(f"    • Tue/Thu 7-9 AM EST  — Pre-market traders scrolling")
    print(f"    • Sun 6-8 PM EST      — Weekend planning session")
    print(f"    • Fri 12-2 PM EST     — End-of-week wind-down")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", "IG engagement report", "Complete", "P3",
             f"{total} posts, {total_reach:,} total reach")


def hashtag_research(args):
    """Generate relevant hashtag sets for prop-firm / hedging content."""
    print("=" * 65)
    print("  #️⃣  HASHTAG RESEARCH — PROP-FIRM / HEDGING NICHE")
    print("=" * 65)

    for category, tags in HASHTAG_SETS.items():
        print(f"\n  {category.replace('-', ' ').title()} ({len(tags)} tags):")
        print(f"    {' '.join(tags)}")

    # Build a recommended mix
    recommended = []
    for tags in HASHTAG_SETS.values():
        recommended.extend(tags[:3])
    print(f"\n  Recommended Mix (copy-paste ready):")
    print(f"    {' '.join(recommended[:15])}")

    print(f"\n  Tips:")
    print(f"    • Use 20-25 hashtags per post (IG sweet spot)")
    print(f"    • Mix high-volume (#trading) with niche (#propfirmchallenge)")
    print(f"    • Rotate sets every 2-3 posts to avoid shadowban")
    print(f"    • Always include #hedgeedge for brand tracking")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", "IG hashtag research", "Complete", "P3",
             f"{sum(len(v) for v in HASHTAG_SETS.values())} hashtags across {len(HASHTAG_SETS)} categories")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram Manager — Plan, track, and analyze IG content")
    parser.add_argument("--action", required=True,
                        choices=["plan-post", "queue", "post-stats", "engagement-report", "hashtag-research"])
    parser.add_argument("--caption", default="")
    parser.add_argument("--type", choices=POST_TYPES, default="feed")
    parser.add_argument("--scheduled-date", default="", dest="scheduled_date")
    parser.add_argument("--hashtags", default="")
    parser.add_argument("--post-id", default="", dest="post_id")
    parser.add_argument("--likes", type=int, default=0)
    parser.add_argument("--comments", type=int, default=0)
    parser.add_argument("--shares", type=int, default=0)
    parser.add_argument("--saves", type=int, default=0)
    parser.add_argument("--reach", type=int, default=0)
    args = parser.parse_args()
    {"plan-post": plan_post, "queue": queue, "post-stats": post_stats,
     "engagement-report": engagement_report, "hashtag-research": hashtag_research}[args.action](args)
