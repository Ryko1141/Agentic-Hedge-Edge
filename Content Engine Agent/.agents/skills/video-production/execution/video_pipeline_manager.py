#!/usr/bin/env python3
"""
video_pipeline_manager.py — Content Engine Agent Video Production

Track videos through the production pipeline: scripting → filming → editing → publishing.

Usage:
    python video_pipeline_manager.py --action add-video --title "Prop Trading Fee Comparison" --type Explainer
    python video_pipeline_manager.py --action update-status --title "Prop Trading..." --stage Editing
    python video_pipeline_manager.py --action update-metrics --title "Prop Trading..." --views 1200 --likes 94
    python video_pipeline_manager.py --action pipeline-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_video(args):
    row = {
        "Title":        args.title,
        "Stage":        "Script",
        "Video Type":   args.type or "Explainer",
        "Script URL":   args.script_url or "",
        "Platform":     args.platform or "YouTube",
        "Target Date":  args.target_date or "",
    }
    add_row("video_pipeline", row)
    print(f"✅ Video added: {args.title}")
    print(f"   Stage: Script | Type: {row['Video Type']} | Platform: {row['Platform']}")
    log_task("Content Engine", f"Video: {args.title}", "Complete", "P2")


def update_status(args):
    items = query_db("video_pipeline", filter={
        "property": "Title", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Video not found: {args.title}"); return
    item = items[0]
    old = item.get("Stage", "?")
    updates = {"Stage": args.stage}
    if args.stage == "Published":
        updates["Publish Date"] = datetime.now().strftime("%Y-%m-%d")
    if args.url:
        updates["URL"] = args.url
    update_row(item["_id"], "video_pipeline", updates)
    print(f"✅ {args.title}: {old} → {args.stage}")
    log_task("Content Engine", f"Video update: {args.title}", "Complete", "P3")


def update_metrics(args):
    items = query_db("video_pipeline", filter={
        "property": "Title", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Video not found: {args.title}"); return
    item = items[0]
    updates = {}
    if args.views:   updates["Views"] = args.views
    if args.likes:   updates["Likes"] = args.likes
    if args.ctr:     updates["CTR %"] = args.ctr
    update_row(item["_id"], "video_pipeline", updates)
    print(f"✅ Metrics updated for: {args.title}")
    if args.views: print(f"   Views: {args.views}")
    if args.likes: print(f"   Likes: {args.likes}")
    if args.ctr:   print(f"   CTR:   {args.ctr}%")
    log_task("Content Engine", f"Video metrics: {args.title}", "Complete", "P3")


def pipeline_report(args):
    items = query_db("video_pipeline")
    print("=" * 65)
    print("  🎬 VIDEO PIPELINE REPORT")
    print("=" * 65)
    if not items:
        print("\n  No videos in pipeline."); return

    stages = ["Script", "Filming", "Editing", "Review", "Scheduled", "Published"]
    by_stage = {}
    for item in items:
        s = item.get("Stage", "Unknown")
        by_stage.setdefault(s, []).append(item)

    for stage in stages:
        group = by_stage.get(stage, [])
        if group:
            print(f"\n  {stage} ({len(group)})")
            for item in group:
                views = item.get("Views", "")
                extra = f" — {views} views" if views else ""
                print(f"    • {item.get('Title', '?')} [{item.get('Video Type', '?')}]{extra}")
    print(f"\n{'─' * 65}")
    print(f"  Total: {len(items)} videos in pipeline")
    published = len(by_stage.get("Published", []))
    if published:
        total_views = sum(int(v.get("Views", 0) or 0) for v in by_stage["Published"])
        print(f"  Published: {published} | Total views: {total_views:,}")
    log_task("Content Engine", "Pipeline report", "Complete", "P3",
             f"{len(items)} videos, {published} published")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Pipeline Management")
    parser.add_argument("--action", required=True,
                        choices=["add-video", "update-status", "update-metrics", "pipeline-report"])
    parser.add_argument("--title")
    parser.add_argument("--type", default="Explainer")
    parser.add_argument("--stage")
    parser.add_argument("--platform", default="YouTube")
    parser.add_argument("--script-url", default="", dest="script_url")
    parser.add_argument("--target-date", default="", dest="target_date")
    parser.add_argument("--url", default="")
    parser.add_argument("--views", type=int)
    parser.add_argument("--likes", type=int)
    parser.add_argument("--ctr", type=float)
    args = parser.parse_args()
    {"add-video": add_video, "update-status": update_status,
     "update-metrics": update_metrics, "pipeline-report": pipeline_report}[args.action](args)
