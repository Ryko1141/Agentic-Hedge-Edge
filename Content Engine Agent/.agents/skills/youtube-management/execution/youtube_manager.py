#!/usr/bin/env python3
"""
youtube_manager.py — Content Engine Agent YouTube Management

Manage the full YouTube video production pipeline: idea → script → film → edit → publish → analyze.

Usage:
    python youtube_manager.py --action add-idea --title "How to Hedge a $200K FTMO Account" --category tutorial --priority P1
    python youtube_manager.py --action pipeline-view
    python youtube_manager.py --action update-stage --title "How to Hedge a $200K..." --stage Scripted
    python youtube_manager.py --action record-analytics --title "How to Hedge..." --views 3400 --watch-hours 128 --subs-gained 45 --ctr 8.2 --avg-view-duration 6.5
    python youtube_manager.py --action channel-report
"""

import sys, os, argparse, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

CATEGORIES = ["tutorial", "market-analysis", "product-demo", "trader-interview", "educational", "shorts"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
STAGES = ["Idea", "Scripted", "Filming", "Editing", "Review", "Published"]

STAGE_EMOJI = {
    "Idea": "💡",
    "Scripted": "📝",
    "Filming": "🎥",
    "Editing": "✂️",
    "Review": "👀",
    "Published": "🟢",
}


def add_idea(args):
    """Add a video idea to the video_pipeline database."""
    if args.category not in CATEGORIES:
        print(f"❌ Invalid category '{args.category}'. Choose from: {', '.join(CATEGORIES)}")
        return
    if args.priority not in PRIORITIES:
        print(f"❌ Invalid priority '{args.priority}'. Choose from: {', '.join(PRIORITIES)}")
        return
    row = {
        "Title":      args.title,
        "Stage":      "Idea",
        "Video Type": args.category.replace("-", " ").title(),
        "Priority":   args.priority,
        "Platform":   "YouTube",
        "Created":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    add_row("video_pipeline", row)
    print("=" * 65)
    print("  💡 VIDEO IDEA ADDED")
    print("=" * 65)
    print(f"\n  Title:    {args.title}")
    print(f"  Category: {args.category}")
    print(f"  Priority: {args.priority}")
    print(f"  Stage:    Idea")
    print(f"\n  Next step: Write script → --action update-stage --stage Scripted")
    print(f"\n{'─' * 65}")
    log_task("Content Engine", f"YT idea: {args.title}", "Complete", "P2",
             f"Category={args.category}, Priority={args.priority}")


def pipeline_view(args):
    """Show the video pipeline organized by production stage."""
    items = query_db("video_pipeline")
    print("=" * 65)
    print("  🎬 YOUTUBE VIDEO PIPELINE")
    print("=" * 65)
    if not items:
        print("\n  No videos in pipeline. Use --action add-idea to start.")
        return

    by_stage = {}
    for item in items:
        stage = item.get("Stage", "Unknown")
        by_stage.setdefault(stage, []).append(item)

    total_in_progress = 0
    for stage in STAGES:
        group = by_stage.get(stage, [])
        emoji = STAGE_EMOJI.get(stage, "•")
        if group:
            print(f"\n  {emoji} {stage} ({len(group)})")
            for item in group:
                title = item.get("Title", "Untitled")
                vtype = item.get("Video Type", "?")
                priority = item.get("Priority", "")
                views = item.get("Views", "")
                priority_str = f" [{priority}]" if priority else ""
                views_str = f" — {int(views):,} views" if views else ""
                print(f"    • {title} ({vtype}){priority_str}{views_str}")
            if stage != "Published":
                total_in_progress += len(group)

    print(f"\n{'─' * 65}")
    print(f"  Total: {len(items)} videos | In Progress: {total_in_progress} | Published: {len(by_stage.get('Published', []))}")

    # Show pipeline health
    if total_in_progress == 0 and not by_stage.get("Idea"):
        print(f"  ⚠  Pipeline empty — add new ideas to maintain publishing cadence")
    elif len(by_stage.get("Idea", [])) < 3:
        print(f"  ⚠  Low idea pool ({len(by_stage.get('Idea', []))}) — aim for 5+ ideas in backlog")

    log_task("Content Engine", "YT pipeline view", "Complete", "P3",
             f"{len(items)} videos across {len(by_stage)} stages")


def update_stage(args):
    """Move a video to the next production stage."""
    if args.stage not in STAGES:
        print(f"❌ Invalid stage '{args.stage}'. Choose from: {', '.join(STAGES)}")
        return
    items = query_db("video_pipeline", filter={
        "property": "Title", "title": {"equals": args.title}
    })
    if not items:
        # Try partial match
        items = query_db("video_pipeline", filter={
            "property": "Title", "title": {"contains": args.title}
        })
    if not items:
        print(f"❌ Video not found: {args.title}")
        return
    item = items[0]
    old_stage = item.get("Stage", "?")
    updates = {"Stage": args.stage}
    if args.stage == "Published":
        updates["Publish Date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    update_row(item["_id"], "video_pipeline", updates)
    old_emoji = STAGE_EMOJI.get(old_stage, "•")
    new_emoji = STAGE_EMOJI.get(args.stage, "•")
    print(f"✅ {item.get('Title', args.title)}")
    print(f"   {old_emoji} {old_stage} → {new_emoji} {args.stage}")

    # Suggest next step
    stage_idx = STAGES.index(args.stage) if args.stage in STAGES else -1
    if 0 <= stage_idx < len(STAGES) - 1:
        next_stage = STAGES[stage_idx + 1]
        print(f"   Next: --action update-stage --stage {next_stage}")

    log_task("Content Engine", f"YT stage: {args.title[:40]}", "Complete", "P2",
             f"{old_stage} → {args.stage}")


def record_analytics(args):
    """Record video performance analytics."""
    items = query_db("video_pipeline", filter={
        "property": "Title", "title": {"contains": args.title}
    })
    if not items:
        print(f"❌ Video not found: {args.title}")
        return
    item = items[0]

    updates = {}
    if args.views:              updates["Views"] = args.views
    if args.watch_hours:        updates["Watch Hours"] = args.watch_hours
    if args.subs_gained:        updates["Subs Gained"] = args.subs_gained
    if args.ctr:                updates["CTR %"] = args.ctr
    if args.avg_view_duration:  updates["Avg View Duration"] = args.avg_view_duration

    update_row(item["_id"], "video_pipeline", updates)
    print("=" * 65)
    print("  📊 VIDEO ANALYTICS RECORDED")
    print("=" * 65)
    print(f"\n  Video: {item.get('Title', '?')}")
    if args.views:              print(f"  Views:              {args.views:,}")
    if args.watch_hours:        print(f"  Watch Hours:        {args.watch_hours:,.1f}")
    if args.subs_gained:        print(f"  Subscribers Gained: {args.subs_gained:,}")
    if args.ctr:                print(f"  CTR:                {args.ctr:.1f}%")
    if args.avg_view_duration:  print(f"  Avg View Duration:  {args.avg_view_duration:.1f} min")

    # Performance assessment
    if args.ctr and args.ctr >= 8.0:
        print(f"\n  🟢 CTR above 8% — excellent thumbnail + title combo")
    elif args.ctr and args.ctr >= 5.0:
        print(f"\n  🟡 CTR 5-8% — decent, consider A/B testing thumbnail")
    elif args.ctr:
        print(f"\n  🔴 CTR below 5% — rework thumbnail and title")

    if args.avg_view_duration and args.avg_view_duration >= 8.0:
        print(f"  🟢 Great retention — viewers staying {args.avg_view_duration:.1f} min")
    elif args.avg_view_duration and args.avg_view_duration >= 4.0:
        print(f"  🟡 Average retention — tighten intro hook and pacing")
    elif args.avg_view_duration:
        print(f"  🔴 Low retention — restructure video format")

    print(f"\n{'─' * 65}")
    log_task("Content Engine", f"YT analytics: {args.title[:40]}", "Complete", "P3",
             f"Views={args.views or 0}, CTR={args.ctr or 0}%")


def channel_report(args):
    """Channel-level analytics summary."""
    items = query_db("video_pipeline")
    print("=" * 65)
    print("  📺 YOUTUBE CHANNEL REPORT")
    print("=" * 65)
    if not items:
        print("\n  No videos tracked yet.")
        return

    published = [i for i in items if i.get("Stage") == "Published"]
    total_views = sum(int(i.get("Views", 0) or 0) for i in items)
    total_watch = sum(float(i.get("Watch Hours", 0) or 0) for i in items)
    total_subs = sum(int(i.get("Subs Gained", 0) or 0) for i in items)
    ctrs = [float(i.get("CTR %", 0) or 0) for i in items if i.get("CTR %")]
    durations = [float(i.get("Avg View Duration", 0) or 0) for i in items if i.get("Avg View Duration")]

    print(f"\n  Channel Overview:")
    print(f"    Total Videos:      {len(items)} ({len(published)} published)")
    print(f"    Total Views:       {total_views:,}")
    print(f"    Total Watch Hours: {total_watch:,.1f}")
    print(f"    Subscribers Gained:{total_subs:,}")
    if ctrs:
        avg_ctr = sum(ctrs) / len(ctrs)
        print(f"    Avg CTR:           {avg_ctr:.1f}%")
    if durations:
        avg_dur = sum(durations) / len(durations)
        print(f"    Avg View Duration: {avg_dur:.1f} min")

    # Top performing videos
    scored = [(i, int(i.get("Views", 0) or 0)) for i in published]
    scored.sort(key=lambda x: -x[1])
    top = [s for s in scored if s[1] > 0][:5]
    if top:
        print(f"\n  Top Performing Videos:")
        for i, (item, views) in enumerate(top, 1):
            ctr = item.get("CTR %", "")
            ctr_str = f" | CTR: {ctr}%" if ctr else ""
            print(f"    {i}. {item.get('Title', '?')[:45]}")
            print(f"       {views:,} views{ctr_str}")

    # Content type breakdown
    by_type = {}
    for item in published:
        vtype = item.get("Video Type", "Unknown")
        views = int(item.get("Views", 0) or 0)
        by_type.setdefault(vtype, {"count": 0, "views": 0})
        by_type[vtype]["count"] += 1
        by_type[vtype]["views"] += views
    if by_type:
        print(f"\n  Content Type Breakdown:")
        for vtype, stats in sorted(by_type.items(), key=lambda x: -x[1]["views"]):
            avg_v = stats["views"] / stats["count"] if stats["count"] else 0
            print(f"    {vtype:<20} {stats['count']} videos | {stats['views']:,} views | avg: {avg_v:,.0f}")

    # Pipeline status
    in_progress = len(items) - len(published)
    if in_progress:
        print(f"\n  Pipeline Status:")
        for stage in STAGES[:-1]:
            stage_items = [i for i in items if i.get("Stage") == stage]
            if stage_items:
                emoji = STAGE_EMOJI.get(stage, "•")
                print(f"    {emoji} {stage}: {len(stage_items)}")

    # Monetization milestone check
    if total_watch >= 4000 and total_subs >= 1000:
        print(f"\n  🟢 YouTube Partner Program eligible! ({total_watch:,.0f} watch hrs, {total_subs:,} subs)")
    else:
        hrs_left = max(0, 4000 - total_watch)
        subs_left = max(0, 1000 - total_subs)
        print(f"\n  YPP Progress: {total_watch:,.0f}/4,000 watch hrs | {total_subs:,}/1,000 subs")
        if hrs_left:  print(f"    Need {hrs_left:,.0f} more watch hours")
        if subs_left: print(f"    Need {subs_left:,} more subscribers")

    print(f"\n{'─' * 65}")
    log_task("Content Engine", "YT channel report", "Complete", "P3",
             f"{len(published)} published, {total_views:,} views, {total_watch:,.1f} watch hrs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Manager — Full video pipeline management")
    parser.add_argument("--action", required=True,
                        choices=["add-idea", "pipeline-view", "update-stage", "record-analytics", "channel-report"])
    parser.add_argument("--title", default="")
    parser.add_argument("--category", default="tutorial", choices=CATEGORIES)
    parser.add_argument("--priority", default="P2", choices=PRIORITIES)
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--views", type=int, default=0)
    parser.add_argument("--watch-hours", type=float, default=0, dest="watch_hours")
    parser.add_argument("--subs-gained", type=int, default=0, dest="subs_gained")
    parser.add_argument("--ctr", type=float, default=0)
    parser.add_argument("--avg-view-duration", type=float, default=0, dest="avg_view_duration")
    args = parser.parse_args()
    {"add-idea": add_idea, "pipeline-view": pipeline_view, "update-stage": update_stage,
     "record-analytics": record_analytics, "channel-report": channel_report}[args.action](args)
