#!/usr/bin/env python3
"""
seo_tracker.py — Marketing Agent SEO Strategy

Track keyword rankings and identify SEO opportunities.

Usage:
    python seo_tracker.py --action add-keyword --keyword "prop firm hedge tool" --volume 1200 --difficulty 35 --intent Transactional
    python seo_tracker.py --action update-rankings --keyword "prop firm hedge tool" --rank 15
    python seo_tracker.py --action seo-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_keyword(args):
    """Add a keyword to track."""
    row = {
        "Keyword":      args.keyword,
        "Volume":       args.volume or 0,
        "Difficulty":   args.difficulty or 50,
        "Current Rank": args.rank or 0,
        "Target Rank":  args.target or 10,
        "Intent":       args.intent or "Informational",
        "Content URL":  args.url or "",
        "Status":       "Target",
        "Last Checked": datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("seo_keywords", row)
    opp = row["Volume"] / max(row["Difficulty"], 1)
    print(f"✅ Keyword added: \"{args.keyword}\"")
    print(f"   Volume: {row['Volume']} | Difficulty: {row['Difficulty']} | Opportunity: {opp:.1f}")
    log_task("Marketing", f"SEO keyword: {args.keyword}", "Complete", "P2")


def update_rankings(args):
    """Update current rank for a keyword."""
    kws = query_db("seo_keywords", filter={
        "property": "Keyword", "title": {"equals": args.keyword}
    })
    if not kws:
        print(f"❌ Keyword not found: {args.keyword}")
        return
    kw = kws[0]
    old_rank = kw.get("Current Rank") or 0
    status = "Top 3" if args.rank <= 3 else "Top 10" if args.rank <= 10 else "Ranking"
    update_row(kw["_id"], "seo_keywords", {
        "Current Rank": args.rank,
        "Status": status,
        "Last Checked": datetime.now().strftime("%Y-%m-%d"),
    })
    direction = "📈" if args.rank < old_rank else "📉" if args.rank > old_rank else "➡️"
    print(f"{direction} \"{args.keyword}\": #{old_rank} → #{args.rank} [{status}]")
    log_task("Marketing", f"Rank update: {args.keyword}", "Complete", "P3",
             f"#{old_rank} → #{args.rank}")


def seo_report(args):
    """Print keywords sorted by opportunity score."""
    kws = query_db("seo_keywords")
    print("=" * 70)
    print("  🔑 SEO KEYWORD REPORT")
    print("=" * 70)
    if not kws:
        print("\n  No keywords tracked yet.")
        return

    for kw in kws:
        kw["_opp"] = (kw.get("Volume") or 0) / max(kw.get("Difficulty") or 1, 1)
    kws.sort(key=lambda x: -x["_opp"])

    print(f"\n  {'Keyword':<35} {'Vol':>6} {'Diff':>5} {'Rank':>5} {'Target':>7} {'Opp':>6} {'Status'}")
    print(f"  {'─'*35} {'─'*6} {'─'*5} {'─'*5} {'─'*7} {'─'*6} {'─'*10}")
    for kw in kws:
        print(f"  {kw.get('Keyword', '?'):<35} {kw.get('Volume', 0):>6} {kw.get('Difficulty', 0):>5} "
              f"#{kw.get('Current Rank', 0):>4} #{kw.get('Target Rank', 0):>6} {kw['_opp']:>6.1f} {kw.get('Status', '?')}")
    avg_rank = sum(k.get("Current Rank") or 0 for k in kws if k.get("Current Rank")) / max(sum(1 for k in kws if k.get("Current Rank")), 1)
    print(f"\n  Keywords: {len(kws)} | Avg rank: #{avg_rank:.0f}")
    log_task("Marketing", "SEO report", "Complete", "P3", f"{len(kws)} keywords tracked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEO Keyword Management")
    parser.add_argument("--action", required=True,
                        choices=["add-keyword", "update-rankings", "seo-report"])
    parser.add_argument("--keyword")
    parser.add_argument("--volume", type=int)
    parser.add_argument("--difficulty", type=int)
    parser.add_argument("--rank", type=int, default=0)
    parser.add_argument("--target", type=int, default=10)
    parser.add_argument("--intent", default="Informational")
    parser.add_argument("--url", default="")
    args = parser.parse_args()
    {"add-keyword": add_keyword, "update-rankings": update_rankings,
     "seo-report": seo_report}[args.action](args)
