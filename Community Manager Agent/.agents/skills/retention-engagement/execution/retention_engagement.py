#!/usr/bin/env python3
"""
retention_engagement.py — Community Manager Agent: Retention & Engagement

Monitor and improve community member retention and engagement.
Identify at-risk members, run re-engagement campaigns, track health scores.

Usage:
    python retention_engagement.py --action health-score
    python retention_engagement.py --action at-risk
    python retention_engagement.py --action engagement-campaigns --type win-back --target-segment inactive-14d
    python retention_engagement.py --action retention-report
    python retention_engagement.py --action leaderboard
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

CAMPAIGN_TYPES = ("win-back", "milestone-celebration", "feature-highlight", "challenge")
SEGMENT_PRESETS = {
    "inactive-14d": "Members with no activity in 14+ days",
    "inactive-30d": "Members with no activity in 30+ days",
    "new-members":  "Members who joined in the last 7 days",
    "power-users":  "Top 10% most active members",
    "free-tier":    "Members on free plan",
    "subscribers":  "Members on paid plans",
}


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def health_score(args):
    """Calculate community health score from multiple signals."""
    feedback = query_db("feedback")
    events = query_db("community_events")

    total_members_proxy = len({f.get("User") for f in feedback if f.get("User")})
    recent_30d = [f for f in feedback if f.get("Date", "") >= _days_ago(30)]
    recent_7d = [f for f in feedback if f.get("Date", "") >= _days_ago(7)]
    active_30d = len({f.get("User") for f in recent_30d if f.get("User")})
    active_7d = len({f.get("User") for f in recent_7d if f.get("User")})

    # Metrics
    dau_mau = (active_7d / active_30d * 100) if active_30d else 0
    msgs_per_member = len(recent_30d) / active_30d if active_30d else 0

    # Help thread resolution
    support_items = query_db("support_tickets")
    resolved = [t for t in support_items if t.get("Status") == "Resolved"]
    resolution_rate = (len(resolved) / len(support_items) * 100) if support_items else 100

    # Event engagement
    completed_events = [e for e in events if e.get("Status") == "Completed"]
    avg_event_score = 0
    if completed_events:
        scores = [int(e.get("Score", 0) or 0) for e in completed_events if int(e.get("Score", 0) or 0) > 0]
        avg_event_score = sum(scores) / len(scores) if scores else 0

    # Composite health score (0-100)
    score_dau = min(dau_mau / 0.4, 25)          # 40% DAU/MAU = perfect
    score_msgs = min(msgs_per_member / 5 * 25, 25)  # 5 msgs/member = perfect
    score_resolution = resolution_rate / 100 * 25
    score_events = avg_event_score / 5 * 25
    composite = score_dau + score_msgs + score_resolution + score_events

    # Grade
    if composite >= 80:
        grade, icon = "A", "🟢"
    elif composite >= 60:
        grade, icon = "B", "🟢"
    elif composite >= 40:
        grade, icon = "C", "🟡"
    elif composite >= 20:
        grade, icon = "D", "🟠"
    else:
        grade, icon = "F", "🔴"

    print("=" * 65)
    print("  💚 COMMUNITY HEALTH SCORE")
    print("=" * 65)
    print(f"\n  {icon} Overall Score: {composite:.0f}/100 (Grade: {grade})")
    print(f"\n  METRICS BREAKDOWN:")
    print(f"    DAU/MAU ratio:         {dau_mau:.1f}%    (score: {score_dau:.0f}/25)")
    print(f"    Messages/member (30d): {msgs_per_member:.1f}      (score: {score_msgs:.0f}/25)")
    print(f"    Help resolution rate:  {resolution_rate:.0f}%     (score: {score_resolution:.0f}/25)")
    print(f"    Avg event feedback:    {avg_event_score:.1f}/5   (score: {score_events:.0f}/25)")
    print(f"\n  RAW DATA:")
    print(f"    Known members:       {total_members_proxy}")
    print(f"    Active (7d):         {active_7d}")
    print(f"    Active (30d):        {active_30d}")
    print(f"    Support tickets:     {len(support_items)} ({len(resolved)} resolved)")
    print(f"    Events completed:    {len(completed_events)}")

    print(f"\n{'─' * 65}")

    # Log as event
    add_row("community_events", {
        "Event":       f"Health Score: {composite:.0f}/100 ({grade})",
        "Type":        "Metric",
        "Date":        _today(),
        "Platform":    "Discord",
        "Status":      "Completed",
        "Description": f"DAU/MAU {dau_mau:.1f}%, resolution {resolution_rate:.0f}%, event score {avg_event_score:.1f}",
    })
    log_task("Community", "Health score calculated", "Complete", "P3",
             f"Score: {composite:.0f}/100 ({grade})")


def at_risk(args):
    """Identify at-risk members who stopped engaging."""
    feedback = query_db("feedback")
    cutoff = _days_ago(14)

    # Build per-user last-seen
    user_last = {}
    for f in feedback:
        user = f.get("User")
        date = f.get("Date", "")
        if user and date:
            if user not in user_last or date > user_last[user]:
                user_last[user] = date

    # Previously active (had at least 2 interactions) but gone silent
    user_counts = {}
    for f in feedback:
        user = f.get("User")
        if user:
            user_counts[user] = user_counts.get(user, 0) + 1

    at_risk_users = []
    for user, last in user_last.items():
        if last < cutoff and user_counts.get(user, 0) >= 2:
            days_gone = (datetime.now(timezone.utc) - datetime.strptime(last, "%Y-%m-%d")).days
            at_risk_users.append({"user": user, "last_seen": last, "days_gone": days_gone,
                                  "interactions": user_counts[user]})

    at_risk_users.sort(key=lambda u: -u["days_gone"])

    print("=" * 65)
    print("  ⚠️ AT-RISK MEMBERS")
    print("=" * 65)
    print(f"  Cutoff: {cutoff} (14+ days inactive)")

    if not at_risk_users:
        print(f"\n  No at-risk members detected. 🎉")
        print(f"  All previously active users have recent activity.")
    else:
        print(f"\n  {len(at_risk_users)} member(s) at risk:\n")
        for u in at_risk_users[:20]:
            severity = "🔴" if u["days_gone"] >= 30 else "🟡"
            print(f"    {severity} {u['user']}")
            print(f"       Last seen: {u['last_seen']} ({u['days_gone']}d ago) | History: {u['interactions']} interactions")

        if len(at_risk_users) > 20:
            print(f"\n    ... and {len(at_risk_users) - 20} more")

    print(f"\n  RECOMMENDED ACTIONS:")
    print(f"    • Send personalized re-engagement DM")
    print(f"    • Highlight new features since last visit")
    print(f"    • Offer 1-on-1 hedging strategy session")
    print(f"\n{'─' * 65}")
    log_task("Community", "At-risk check", "Complete", "P2",
             f"{len(at_risk_users)} at-risk members")


def engagement_campaigns(args):
    """Create a re-engagement campaign and log to community_events."""
    ctype = args.type or "win-back"
    segment = args.target_segment or "inactive-14d"
    segment_desc = SEGMENT_PRESETS.get(segment, segment)

    campaign_configs = {
        "win-back": {
            "name": f"Win-Back Campaign: {segment}",
            "description": "Re-engage inactive members with personalized outreach, exclusive content preview, and limited-time challenge entry.",
            "actions": [
                "Send personalized DM with 'We miss you' message",
                "Share exclusive hedging strategy PDF",
                "Offer free week of Challenge Shield",
                "Invite to upcoming AMA",
            ],
        },
        "milestone-celebration": {
            "name": f"Milestone Celebration: {segment}",
            "description": "Celebrate community milestones to boost morale and engagement.",
            "actions": [
                "Create announcement post with stats",
                "Spotlight top contributors",
                "Run giveaway for active members",
                "Share community growth infographic",
            ],
        },
        "feature-highlight": {
            "name": f"Feature Highlight: {segment}",
            "description": "Showcase new or underused features to drive adoption and re-engagement.",
            "actions": [
                "Create video walkthrough of feature",
                "Pin tutorial in relevant channel",
                "Host live demo session",
                "Collect feedback via survey",
            ],
        },
        "challenge": {
            "name": f"Community Challenge: {segment}",
            "description": "Run a competitive challenge to drive daily engagement and attract new members.",
            "actions": [
                "Set clear rules and duration (7 days)",
                "Create dedicated challenge channel",
                "Daily leaderboard updates",
                "Prize: 1 month free Challenge Shield",
            ],
        },
    }

    config = campaign_configs.get(ctype, campaign_configs["win-back"])

    row = {
        "Event":       config["name"],
        "Type":        "Campaign",
        "Date":        _today(),
        "Platform":    "Discord",
        "Status":      "Planned",
        "Description": f"[{ctype}] Target: {segment_desc}. {config['description']}",
    }
    add_row("community_events", row)

    print("=" * 65)
    print("  🎯 ENGAGEMENT CAMPAIGN CREATED")
    print("=" * 65)
    print(f"\n  Campaign:  {config['name']}")
    print(f"  Type:      {ctype}")
    print(f"  Target:    {segment} — {segment_desc}")
    print(f"  Start:     {_today()}")
    print(f"\n  ACTION PLAN:")
    for i, action in enumerate(config["actions"], 1):
        print(f"    {i}. {action}")
    print(f"\n  EXPECTED OUTCOMES:")
    print(f"    • Re-engage 15-25% of target segment")
    print(f"    • Generate 50+ new messages in first week")
    print(f"    • Convert 5-10% of free users to trial")
    print(f"\n{'─' * 65}")
    log_task("Community", f"Campaign: {config['name']}", "Complete", "P2",
             f"Type: {ctype}, target: {segment}")


def retention_report(args):
    """Full retention analysis with cohort data."""
    feedback = query_db("feedback")

    # Build user signup dates and last activity
    user_first = {}
    user_last = {}
    for f in feedback:
        user = f.get("User")
        date = f.get("Date", "")
        if user and date:
            if user not in user_first or date < user_first[user]:
                user_first[user] = date
            if user not in user_last or date > user_last[user]:
                user_last[user] = date

    total_users = len(user_first)
    today = _today()

    # Retention by window
    windows = {"7-day": 7, "30-day": 30, "90-day": 90}
    retention_data = {}
    for label, days in windows.items():
        cutoff_signup = _days_ago(days)
        cohort = {u for u, d in user_first.items() if d <= cutoff_signup}
        active_cutoff = _days_ago(days)
        retained = {u for u in cohort if user_last.get(u, "") >= active_cutoff}
        rate = (len(retained) / len(cohort) * 100) if cohort else 0
        retention_data[label] = {"cohort": len(cohort), "retained": len(retained), "rate": rate}

    print("=" * 65)
    print("  📊 RETENTION ANALYSIS")
    print("=" * 65)
    print(f"\n  Total tracked users: {total_users}")
    print(f"  Analysis date:       {today}")

    print(f"\n  RETENTION RATES:")
    for label, data in retention_data.items():
        bar_len = int(data["rate"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        status = "🟢" if data["rate"] >= 50 else ("🟡" if data["rate"] >= 25 else "🔴")
        print(f"    {status} {label:<10} {data['rate']:5.1f}%  {bar}  ({data['retained']}/{data['cohort']})")

    # Churn reasons (from feedback tagged as churn)
    churn_items = [f for f in feedback if "churn" in (f.get("Category") or "").lower()
                   or "cancel" in (f.get("Feedback") or "").lower()
                   or "leaving" in (f.get("Feedback") or "").lower()]
    print(f"\n  CHURN SIGNALS:")
    if churn_items:
        for c in churn_items[:5]:
            print(f"    • {c.get('User', '?')}: {c.get('Feedback', '?')[:60]}")
    else:
        print(f"    No explicit churn feedback captured yet.")
        print(f"    Consider adding exit survey to cancellation flow.")

    # Monthly cohort summary
    monthly_cohorts = {}
    for u, d in user_first.items():
        mo = d[:7]
        monthly_cohorts.setdefault(mo, {"total": 0, "still_active": 0})
        monthly_cohorts[mo]["total"] += 1
        if user_last.get(u, "") >= _days_ago(30):
            monthly_cohorts[mo]["still_active"] += 1

    if monthly_cohorts:
        print(f"\n  MONTHLY COHORTS:")
        for mo in sorted(monthly_cohorts.keys())[-6:]:
            c = monthly_cohorts[mo]
            rate = c["still_active"] / c["total"] * 100 if c["total"] else 0
            print(f"    {mo}: {c['total']} joined, {c['still_active']} still active ({rate:.0f}%)")

    print(f"\n{'─' * 65}")
    log_task("Community", "Retention report", "Complete", "P2",
             f"{total_users} users tracked")


def leaderboard(args):
    """Generate member leaderboard for recognition program."""
    feedback = query_db("feedback")

    # Tally user contributions
    user_stats = {}
    for f in feedback:
        user = f.get("User")
        if not user:
            continue
        if user not in user_stats:
            user_stats[user] = {"messages": 0, "help": 0, "feedback": 0, "events": 0}
        ftype = (f.get("Type") or "").lower()
        if ftype == "support" or "help" in (f.get("Category") or "").lower():
            user_stats[user]["help"] += 1
        elif ftype == "feedback" or ftype == "suggestion":
            user_stats[user]["feedback"] += 1
        elif ftype == "event":
            user_stats[user]["events"] += 1
        user_stats[user]["messages"] += 1

    # Score: messages + 3x help + 2x feedback + 2x events
    for u in user_stats:
        s = user_stats[u]
        s["score"] = s["messages"] + s["help"] * 3 + s["feedback"] * 2 + s["events"] * 2

    ranked = sorted(user_stats.items(), key=lambda x: -x[1]["score"])

    print("=" * 65)
    print("  🏆 COMMUNITY LEADERBOARD")
    print("=" * 65)

    if not ranked:
        print("\n  No member activity data yet. Interactions are tracked via feedback DB.\n")
        return

    medals = ["🥇", "🥈", "🥉"]
    print(f"\n  {'Rank':<6} {'Member':<20} {'Score':>6} {'Msgs':>6} {'Help':>6} {'FB':>4}")
    print(f"  {'─' * 50}")

    for i, (user, stats) in enumerate(ranked[:15]):
        medal = medals[i] if i < 3 else f"  {i + 1}."
        print(f"  {medal:<6} {user:<20} {stats['score']:>6} {stats['messages']:>6} {stats['help']:>6} {stats['feedback']:>4}")

    print(f"\n  Total contributors: {len(ranked)}")
    if ranked:
        top = ranked[0]
        print(f"  Top contributor:    {top[0]} (score: {top[1]['score']})")

    print(f"\n  RECOGNITION IDEAS:")
    print(f"    • Monthly 'Community Champion' role on Discord")
    print(f"    • Feature top helpers in #announcements")
    print(f"    • Free month of Challenge Shield for top 3")
    print(f"\n{'─' * 65}")
    log_task("Community", "Leaderboard generated", "Complete", "P3",
             f"{len(ranked)} contributors ranked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retention & Engagement Manager")
    parser.add_argument("--action", required=True,
                        choices=["health-score", "at-risk", "engagement-campaigns",
                                 "retention-report", "leaderboard"])
    parser.add_argument("--type", choices=CAMPAIGN_TYPES)
    parser.add_argument("--target-segment", default="inactive-14d")
    args = parser.parse_args()
    {
        "health-score":         health_score,
        "at-risk":              at_risk,
        "engagement-campaigns": engagement_campaigns,
        "retention-report":     retention_report,
        "leaderboard":          leaderboard,
    }[args.action](args)
