#!/usr/bin/env python3
"""
newsletter_manager.py — Marketing Agent Newsletter Management

Manage bi-weekly newsletter to prop-firm trader subscribers via Resend.
Plan editions, generate subject lines, track engagement, maintain list hygiene.

Usage:
    python newsletter_manager.py --action plan-edition --edition 12 --topic "Drawdown Protection Strategies" --content-links "https://hedge-edge.com/blog/dd-guide,https://hedge-edge.com/blog/ftmo-tips"
    python newsletter_manager.py --action subject-lines --edition 12
    python newsletter_manager.py --action send-stats
    python newsletter_manager.py --action list-hygiene
    python newsletter_manager.py --action edition-report --edition 12
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Marketing"
NEWSLETTER_CADENCE = "Bi-weekly"

# Subject line templates — prop-firm trading angles
SUBJECT_TEMPLATES = [
    # Fear/protection angle
    [
        "🛡️ {topic} — Don't Lose Your Funded Account",
        "Your Prop Firm Account Is at Risk. Here's the Fix.",
        "{topic}: The Strategy 87% of Traders Miss",
    ],
    # Curiosity/education angle
    [
        "How Top Traders Handle {topic}",
        "📊 {topic} — Data From 10,000 Challenges",
        "The {topic} Playbook (Free Inside)",
    ],
    # Urgency/FOMO angle
    [
        "⚠️ {topic} — Before Your Next Drawdown",
        "3 Traders Lost Their Accounts This Week. {topic} Could Have Saved Them.",
        "New: {topic} — Early Access for Subscribers",
    ],
    # Social proof angle
    [
        "How Mike Protected $200K Across 4 Prop Firms",
        "{topic} — What FTMO Traders Are Doing Differently",
        "🏆 Top 5% Traders All Use This {topic} Approach",
    ],
]


# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────

def plan_edition(args):
    """Plan a new newsletter edition in the campaigns DB."""
    links = [l.strip() for l in (args.content_links or "").split(",") if l.strip()]

    row = {
        "Name":           f"Newsletter #{args.edition}: {args.topic}",
        "Type":           "Newsletter",
        "Status":         "Planned",
        "Topic":          args.topic or "",
        "Edition":        args.edition,
        "Content Links":  ", ".join(links),
        "Subject Line A": "",
        "Subject Line B": "",
        "Subject Line C": "",
        "Send Date":      "",
        "Created":        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    add_row("campaigns", row)

    print("=" * 60)
    print(f"  📰 NEWSLETTER EDITION #{args.edition} PLANNED")
    print("=" * 60)
    print(f"\n  Topic:    {args.topic}")
    print(f"  Cadence:  {NEWSLETTER_CADENCE}")
    print(f"  Status:   Planned")
    if links:
        print(f"  Content Links:")
        for i, link in enumerate(links, 1):
            print(f"    {i}. {link}")
    print(f"\n  Next step: Run --action subject-lines --edition {args.edition}\n")

    log_task(AGENT, f"Newsletter #{args.edition} planned", "Complete", "P2",
             f"Topic: {args.topic}, {len(links)} content links")


def subject_lines(args):
    """Generate 3 subject line variants for an edition."""
    rows = query_db("campaigns", filter={
        "property": "Edition", "number": {"equals": args.edition}
    })
    if not rows:
        print(f"❌ Edition #{args.edition} not found. Run --action plan-edition first.")
        return

    edition = rows[0]
    topic = edition.get("Topic") or f"Edition #{args.edition}"

    # Pick a template set based on edition number for variety
    template_idx = (args.edition - 1) % len(SUBJECT_TEMPLATES)
    templates = SUBJECT_TEMPLATES[template_idx]
    generated = [t.format(topic=topic) for t in templates]

    update_row(edition["_id"], "campaigns", {
        "Subject Line A": generated[0],
        "Subject Line B": generated[1],
        "Subject Line C": generated[2],
        "Status":         "Subjects Ready",
    })

    print("=" * 65)
    print(f"  ✉️  SUBJECT LINES — Newsletter #{args.edition}")
    print("=" * 65)
    print(f"\n  Topic: {topic}\n")
    for i, subj in enumerate(generated, 1):
        label = chr(64 + i)  # A, B, C
        print(f"  {label}: {subj}")

    print(f"\n  All 3 variants saved to campaigns DB.")
    print(f"  Recommendation: A/B test Subject A vs B, hold C as backup.\n")

    log_task(AGENT, f"Newsletter #{args.edition} subjects generated", "Complete", "P2",
             f"3 subject line variants for: {topic}")


def send_stats(args):
    """Pull and display stats for recent newsletter sends."""
    sends = query_db("email_sends", sorts=[
        {"property": "Date", "direction": "descending"}
    ])

    print("=" * 70)
    print("  📊 NEWSLETTER SEND STATISTICS")
    print("=" * 70)

    if not sends:
        print("\n  No send records found in email_sends DB.\n")
        return

    # Show last 10 sends
    recent = sends[:10]

    print(f"\n  {'Date':<12} {'Subject':<35} {'Opens':>7} {'Clicks':>7} {'Unsubs':>7}")
    print(f"  {'─'*12} {'─'*35} {'─'*7} {'─'*7} {'─'*7}")

    total_sent = 0
    total_opens = 0
    total_clicks = 0
    total_unsubs = 0

    for s in recent:
        date = s.get("Date") or "?"
        subject = (s.get("Subject") or s.get("Name") or "?")[:35]
        sent = s.get("Sent") or s.get("Recipients") or 0
        opens = s.get("Opens") or 0
        clicks = s.get("Clicks") or 0
        unsubs = s.get("Unsubscribes") or 0

        open_rate = opens / sent * 100 if sent > 0 else 0
        click_rate = clicks / sent * 100 if sent > 0 else 0
        unsub_rate = unsubs / sent * 100 if sent > 0 else 0

        print(f"  {date:<12} {subject:<35} {open_rate:>6.1f}% {click_rate:>6.1f}% {unsub_rate:>6.1f}%")

        total_sent += sent
        total_opens += opens
        total_clicks += clicks
        total_unsubs += unsubs

    avg_open = total_opens / total_sent * 100 if total_sent > 0 else 0
    avg_click = total_clicks / total_sent * 100 if total_sent > 0 else 0
    avg_unsub = total_unsubs / total_sent * 100 if total_sent > 0 else 0

    print(f"\n  ─── Averages (last {len(recent)} sends) ───")
    print(f"  Open Rate:        {avg_open:.1f}%  {'✅' if avg_open >= 25 else '⚠️ Below 25% benchmark'}")
    print(f"  Click Rate:       {avg_click:.1f}%  {'✅' if avg_click >= 3 else '⚠️ Below 3% benchmark'}")
    print(f"  Unsubscribe Rate: {avg_unsub:.2f}%  {'✅' if avg_unsub <= 0.5 else '🔴 Above 0.5% threshold'}")
    print()

    log_task(AGENT, "Newsletter send stats", "Complete", "P3",
             f"Open={avg_open:.1f}% Click={avg_click:.1f}% Unsub={avg_unsub:.2f}% ({len(recent)} sends)")


def list_hygiene(args):
    """Report on subscriber list health — bounces, inactive, growth."""
    sends = query_db("email_sends", sorts=[
        {"property": "Date", "direction": "descending"}
    ])

    print("=" * 60)
    print("  🧹 SUBSCRIBER LIST HYGIENE REPORT")
    print("=" * 60)

    if not sends:
        print("\n  No send data available for analysis.\n")
        return

    total_sent = 0
    total_bounced = 0
    total_unsubs = 0
    inactive_count = 0
    ninety_days_ago = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    # Analyze engagement patterns
    subscriber_opens = {}  # Track last open per email/send
    for s in sends:
        sent = s.get("Sent") or s.get("Recipients") or 0
        bounced = s.get("Bounces") or 0
        unsubs = s.get("Unsubscribes") or 0
        opens = s.get("Opens") or 0
        date = s.get("Date") or ""

        total_sent += sent
        total_bounced += bounced
        total_unsubs += unsubs

        # Estimate inactive: sends with 0 opens that are older than 90 days
        if date and date < ninety_days_ago and opens == 0:
            inactive_count += 1

    bounce_rate = total_bounced / total_sent * 100 if total_sent > 0 else 0
    unsub_rate = total_unsubs / total_sent * 100 if total_sent > 0 else 0

    # Latest send size for current list estimate
    latest_size = sends[0].get("Sent") or sends[0].get("Recipients") or 0
    oldest_size = sends[-1].get("Sent") or sends[-1].get("Recipients") or 0 if sends else 0
    growth = latest_size - oldest_size

    print(f"\n  ─── List Overview ───")
    print(f"  Estimated List Size:   {latest_size:,}")
    print(f"  Growth ({len(sends)} sends):    {growth:+,}")
    print(f"  Total Sends Tracked:   {total_sent:,}")

    print(f"\n  ─── Health Metrics ───")
    bounce_ok = bounce_rate < 2
    unsub_ok = unsub_rate < 0.5
    print(f"  Bounce Rate:      {bounce_rate:.2f}%  {'✅ Healthy' if bounce_ok else '🔴 Clean your list (>2%)'}")
    print(f"  Unsubscribe Rate: {unsub_rate:.2f}%  {'✅ Healthy' if unsub_ok else '⚠️ Review content strategy (>0.5%)'}")
    print(f"  Inactive Sends:   {inactive_count} (sends with 0 opens, >90 days)")

    print(f"\n  ─── Recommendations ───")
    if not bounce_ok:
        print("  • Remove hard bounces immediately — damages sender reputation")
        print("  • Verify new email addresses before adding to list")
    if not unsub_ok:
        print("  • Review email frequency — bi-weekly may be too frequent")
        print("  • Improve content relevance for prop-firm traders")
    if inactive_count > 0:
        print(f"  • Consider re-engagement campaign for inactive subscribers")
        print(f"  • Sunset subscribers with no opens in 90+ days")
    if bounce_ok and unsub_ok and inactive_count == 0:
        print("  • ✅ List health is good — maintain current practices")

    # Health score
    health = 100
    if not bounce_ok:
        health -= 30
    if not unsub_ok:
        health -= 20
    if inactive_count > 3:
        health -= 15
    print(f"\n  📋 List Health Score: {health}/100 {'🟢' if health >= 80 else '🟡' if health >= 60 else '🔴'}\n")

    log_task(AGENT, "List hygiene report", "Complete", "P2",
             f"Bounces={bounce_rate:.2f}% Unsubs={unsub_rate:.2f}% Health={health}/100")


def edition_report(args):
    """Full report for a specific newsletter edition."""
    campaigns = query_db("campaigns", filter={
        "property": "Edition", "number": {"equals": args.edition}
    })
    if not campaigns:
        print(f"❌ Edition #{args.edition} not found in campaigns.")
        return

    campaign = campaigns[0]
    name = campaign.get("Name") or f"Edition #{args.edition}"
    topic = campaign.get("Topic") or "—"
    status = campaign.get("Status") or "?"
    sub_a = campaign.get("Subject Line A") or "—"
    sub_b = campaign.get("Subject Line B") or "—"
    sub_c = campaign.get("Subject Line C") or "—"
    links = campaign.get("Content Links") or "—"

    print("=" * 65)
    print(f"  📰 NEWSLETTER EDITION REPORT — #{args.edition}")
    print("=" * 65)
    print(f"\n  Campaign:  {name}")
    print(f"  Topic:     {topic}")
    print(f"  Status:    {status}")
    print(f"  Send Date: {campaign.get('Send Date') or 'Not scheduled'}")

    print(f"\n  ─── Subject Lines ───")
    print(f"  A: {sub_a}")
    print(f"  B: {sub_b}")
    print(f"  C: {sub_c}")

    print(f"\n  ─── Content ───")
    if links and links != "—":
        for i, link in enumerate(links.split(","), 1):
            print(f"  {i}. {link.strip()}")
    else:
        print("  No content links attached.")

    # Try to find matching send data
    sends = query_db("email_sends")
    edition_sends = [s for s in sends if str(args.edition) in (s.get("Name") or s.get("Subject") or "")]

    if edition_sends:
        print(f"\n  ─── Send Performance ───")
        for s in edition_sends:
            sent = s.get("Sent") or s.get("Recipients") or 0
            opens = s.get("Opens") or 0
            clicks = s.get("Clicks") or 0
            unsubs = s.get("Unsubscribes") or 0
            open_rate = opens / sent * 100 if sent > 0 else 0
            click_rate = clicks / sent * 100 if sent > 0 else 0

            print(f"  Sent To:       {sent:,}")
            print(f"  Opens:         {opens:,} ({open_rate:.1f}%)")
            print(f"  Clicks:        {clicks:,} ({click_rate:.1f}%)")
            print(f"  Unsubscribes:  {unsubs}")

            # Performance vs benchmarks
            print(f"\n  ─── vs. Benchmarks ───")
            print(f"  Open Rate:  {open_rate:.1f}% {'✅ Above' if open_rate >= 25 else '⚠️ Below'} 25% benchmark")
            print(f"  Click Rate: {click_rate:.1f}% {'✅ Above' if click_rate >= 3 else '⚠️ Below'} 3% benchmark")
    else:
        print(f"\n  ─── Send Performance ───")
        print(f"  No matching send data found for edition #{args.edition}.")
        if status == "Planned" or status == "Subjects Ready":
            print(f"  Edition is still in '{status}' stage.")

    print()
    log_task(AGENT, f"Newsletter #{args.edition} report", "Complete", "P3",
             f"Status: {status}, Topic: {topic}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Newsletter Management")
    parser.add_argument("--action", required=True,
                        choices=["plan-edition", "subject-lines", "send-stats",
                                 "list-hygiene", "edition-report"])
    parser.add_argument("--edition", type=int)
    parser.add_argument("--topic")
    parser.add_argument("--content-links", dest="content_links")

    args = parser.parse_args()
    {
        "plan-edition":   plan_edition,
        "subject-lines":  subject_lines,
        "send-stats":     send_stats,
        "list-hygiene":   list_hygiene,
        "edition-report": edition_report,
    }[args.action](args)
