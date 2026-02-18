#!/usr/bin/env python3
"""
lead_generator.py — Marketing Agent Lead Generation

Ingest, score, segment, and route leads from multiple acquisition
channels into the leads_crm Notion database.

Usage:
    python lead_generator.py --action ingest --email "trader@gmail.com" --name "Mike Chen" --source landing_page
    python lead_generator.py --action score
    python lead_generator.py --action segment
    python lead_generator.py --action pipeline-report
    python lead_generator.py --action decay
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Marketing"
VALID_SOURCES = [
    "landing_page", "discord", "google_ads", "meta_ads",
    "organic", "ib_referral", "manual",
]

# Points-based lead scoring rules
SCORING_RULES = {
    "pricing_page":     20,   # Visited pricing page
    "trial_start":      40,   # Started free trial
    "discord_member":   15,   # Joined Discord community
    "email_opened":     10,   # Opened a marketing email
    "cta_clicked":      15,   # Clicked a CTA link
    "broker_affiliated": 20,  # Has an affiliated broker
    "multi_account":    30,   # 3+ prop-firm accounts
    "failed_challenge": 25,   # Previously failed a challenge (high intent)
}

DECAY_POINTS = 5       # Weekly decay for inactive leads
ARCHIVE_DAYS = 60      # Archive leads below 0 after this many days
SEGMENTS = {"Cold": (0, 29), "Warm": (30, 59), "Hot": (60, float("inf"))}


# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────

def ingest(args):
    """Add a new lead to leads_crm."""
    if args.source and args.source not in VALID_SOURCES:
        print(f"❌ Invalid source. Choose from: {', '.join(VALID_SOURCES)}")
        return

    # Check for duplicate
    existing = query_db("leads_crm", filter={
        "property": "Email", "email": {"equals": args.email}
    })
    if existing:
        print(f"⚠️  Lead already exists: {args.email} (skipping)")
        return

    row = {
        "Name":        args.name or "",
        "Email":       args.email,
        "Source":       args.source or "manual",
        "Score":        0,
        "Segment":      "Cold",
        "Status":       "New",
        "Signals":      "",
        "Last Active":  datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "Created":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    add_row("leads_crm", row)

    print("=" * 55)
    print("  📥 LEAD INGESTED")
    print("=" * 55)
    print(f"\n  Name:   {row['Name'] or '—'}")
    print(f"  Email:  {args.email}")
    print(f"  Source: {row['Source']}")
    print(f"  Score:  0 (Cold)")
    print(f"  Date:   {row['Created']}\n")

    log_task(AGENT, f"Lead ingested: {args.email}", "Complete", "P2",
             f"Source: {row['Source']}")


def score(args):
    """Score all unscored leads using the points-based system."""
    leads = query_db("leads_crm", filter={
        "property": "Status", "select": {"does_not_equal": "Archived"}
    })

    print("=" * 60)
    print("  📊 LEAD SCORING RUN")
    print("=" * 60)

    if not leads:
        print("\n  No leads to score.\n")
        return

    scored = 0
    for lead in leads:
        signals_raw = lead.get("Signals") or ""
        signals = [s.strip().lower() for s in signals_raw.split(",") if s.strip()]
        total = 0
        matched = []
        for signal_key, points in SCORING_RULES.items():
            if signal_key in signals:
                total += points
                matched.append(f"{signal_key}(+{points})")

        # Source bonus
        source = (lead.get("Source") or "").lower()
        if source == "ib_referral":
            total += 15
            matched.append("ib_referral_bonus(+15)")
        elif source in ("google_ads", "meta_ads"):
            total += 10
            matched.append(f"{source}_bonus(+10)")

        old_score = lead.get("Score") or 0
        new_score = max(total, old_score)  # Never decrease via scoring

        if new_score != old_score:
            update_row(lead["_id"], "leads_crm", {"Score": new_score})
            scored += 1
            name = lead.get("Name") or lead.get("Email") or "?"
            print(f"  {name:<30} {old_score:>3} → {new_score:>3}  [{', '.join(matched) or 'base'}]")

    print(f"\n  Scored {scored}/{len(leads)} leads updated")
    print(f"  Scoring rules: {len(SCORING_RULES)} signals evaluated\n")
    log_task(AGENT, "Lead scoring run", "Complete", "P2",
             f"{scored}/{len(leads)} leads updated")


def segment(args):
    """Segment leads by score into Cold / Warm / Hot."""
    leads = query_db("leads_crm", filter={
        "property": "Status", "select": {"does_not_equal": "Archived"}
    })

    print("=" * 55)
    print("  🎯 LEAD SEGMENTATION")
    print("=" * 55)

    if not leads:
        print("\n  No leads to segment.\n")
        return

    counts = {"Cold": 0, "Warm": 0, "Hot": 0}
    updated = 0

    for lead in leads:
        lead_score = lead.get("Score") or 0
        new_segment = "Cold"
        for seg_name, (lo, hi) in SEGMENTS.items():
            if lo <= lead_score <= hi:
                new_segment = seg_name
                break

        old_segment = lead.get("Segment") or ""
        counts[new_segment] += 1

        if new_segment != old_segment:
            update_row(lead["_id"], "leads_crm", {"Segment": new_segment})
            updated += 1
            name = lead.get("Name") or lead.get("Email") or "?"
            print(f"  {name:<30} Score: {lead_score:>3} │ {old_segment or '—'} → {new_segment}")

    print(f"\n  ─── Segment Distribution ───")
    total = len(leads)
    for seg, count in counts.items():
        bar = "█" * int(count / max(total, 1) * 30)
        pct = count / total * 100 if total > 0 else 0
        print(f"  {seg:<6} {count:>4} ({pct:>5.1f}%)  {bar}")

    print(f"\n  Updated: {updated} leads re-segmented\n")
    log_task(AGENT, "Lead segmentation", "Complete", "P2",
             f"Cold={counts['Cold']} Warm={counts['Warm']} Hot={counts['Hot']}")


def pipeline_report(args):
    """Show full lead pipeline report."""
    leads = query_db("leads_crm")

    print("=" * 65)
    print("  📈 LEAD PIPELINE REPORT")
    print("=" * 65)

    if not leads:
        print("\n  No leads in CRM.\n")
        return

    total = len(leads)
    segments = {"Cold": 0, "Warm": 0, "Hot": 0}
    sources = {}
    statuses = {}
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    new_this_week = 0

    for lead in leads:
        seg = lead.get("Segment") or "Cold"
        segments[seg] = segments.get(seg, 0) + 1

        src = lead.get("Source") or "unknown"
        sources[src] = sources.get(src, 0) + 1

        st = lead.get("Status") or "New"
        statuses[st] = statuses.get(st, 0) + 1

        created = lead.get("Created") or ""
        if created >= week_ago:
            new_this_week += 1

    print(f"\n  Total Leads:    {total}")
    print(f"  New This Week:  {new_this_week}")

    print(f"\n  ─── By Segment ───")
    for seg in ("Hot", "Warm", "Cold"):
        count = segments.get(seg, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = "█" * int(count / max(total, 1) * 25)
        print(f"  {seg:<6} {count:>4} ({pct:>5.1f}%)  {bar}")

    print(f"\n  ─── By Source ───")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        print(f"  {src:<20} {count:>4} ({pct:>5.1f}%)")

    print(f"\n  ─── By Status ───")
    for st, count in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"  {st:<20} {count:>4}")

    # Simple conversion funnel
    hot = segments.get("Hot", 0)
    warm = segments.get("Warm", 0)
    conv_rate = hot / total * 100 if total > 0 else 0
    qualified_rate = (hot + warm) / total * 100 if total > 0 else 0
    print(f"\n  ─── Conversion Funnel ───")
    print(f"  Total → Qualified (Warm+Hot): {qualified_rate:.1f}%")
    print(f"  Total → Hot:                  {conv_rate:.1f}%\n")

    log_task(AGENT, "Pipeline report", "Complete", "P3",
             f"Total={total} Hot={hot} Warm={warm} Cold={segments.get('Cold', 0)} NewWeek={new_this_week}")


def decay(args):
    """Apply weekly score decay to inactive leads, archive stale ones."""
    leads = query_db("leads_crm", filter={
        "property": "Status", "select": {"does_not_equal": "Archived"}
    })

    print("=" * 55)
    print("  🔻 LEAD SCORE DECAY")
    print("=" * 55)

    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    archive_cutoff = (now - timedelta(days=ARCHIVE_DAYS)).strftime("%Y-%m-%d")
    decayed = 0
    archived = 0

    for lead in leads:
        last_active = lead.get("Last Active") or ""
        created = lead.get("Created") or ""
        current_score = lead.get("Score") or 0
        name = lead.get("Name") or lead.get("Email") or "?"

        # Only decay if no activity in the last week
        if last_active and last_active >= week_ago:
            continue

        new_score = current_score - DECAY_POINTS
        updates = {"Score": max(new_score, -50)}  # Floor at -50

        # Archive if score < 0 and older than ARCHIVE_DAYS
        if new_score < 0 and created and created < archive_cutoff:
            updates["Status"] = "Archived"
            updates["Segment"] = "Cold"
            archived += 1
            print(f"  📦 {name:<25} score {current_score} → Archived")
        else:
            decayed += 1
            print(f"  ↘  {name:<25} {current_score:>3} → {max(new_score, -50):>3}")

        update_row(lead["_id"], "leads_crm", updates)

    print(f"\n  Decayed:  {decayed} leads (−{DECAY_POINTS} pts each)")
    print(f"  Archived: {archived} leads (score < 0, older than {ARCHIVE_DAYS}d)\n")

    log_task(AGENT, "Lead score decay", "Complete", "P2",
             f"Decayed={decayed} Archived={archived}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lead Generation & Scoring")
    parser.add_argument("--action", required=True,
                        choices=["ingest", "score", "segment",
                                 "pipeline-report", "decay"])
    parser.add_argument("--email")
    parser.add_argument("--name")
    parser.add_argument("--source", choices=VALID_SOURCES)

    args = parser.parse_args()
    {
        "ingest":          ingest,
        "score":           score,
        "segment":         segment,
        "pipeline-report": pipeline_report,
        "decay":           decay,
    }[args.action](args)
