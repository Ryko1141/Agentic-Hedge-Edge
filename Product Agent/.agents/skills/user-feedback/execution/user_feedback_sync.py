#!/usr/bin/env python3
"""
user_feedback_sync.py — Product Agent User Feedback Pipeline

Collect, categorize, and action user feedback from multiple channels
into product decisions for the Hedge Edge prop-firm hedging tool.

Usage:
    python user_feedback_sync.py --action ingest --source discord --category feature-request --summary "Add MT4 support" --priority P1
    python user_feedback_sync.py --action categorize
    python user_feedback_sync.py --action feature-requests
    python user_feedback_sync.py --action sentiment-report
    python user_feedback_sync.py --action feedback-to-roadmap --top-n 5
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Product"

SOURCES = ["discord", "email", "in-app", "support-ticket", "review", "interview"]
CATEGORIES = ["bug", "feature-request", "ux-issue", "praise", "complaint"]

SOURCE_ICONS = {
    "discord": "💬", "email": "📧", "in-app": "📱",
    "support-ticket": "🎫", "review": "⭐", "interview": "🎤",
}

CATEGORY_ICONS = {
    "bug": "🐛", "feature-request": "💡", "ux-issue": "🎨",
    "praise": "🌟", "complaint": "😤",
}

# Keyword classifiers for auto-categorization
CATEGORY_KEYWORDS = {
    "bug":             ["broken", "error", "crash", "not working", "bug", "fails",
                        "exception", "404", "500", "timeout", "disconnect", "freeze"],
    "feature-request": ["would be nice", "please add", "wish", "can you", "feature",
                        "request", "add support", "implement", "suggestion", "integrate"],
    "ux-issue":        ["confusing", "hard to find", "unclear", "difficult", "ux",
                        "ui", "layout", "navigation", "unintuitive", "slow to load"],
    "praise":          ["love", "great", "amazing", "awesome", "excellent", "works well",
                        "thank you", "perfect", "fantastic", "best"],
    "complaint":       ["terrible", "worst", "hate", "unacceptable", "frustrated",
                        "disappointed", "waste", "refund", "cancel", "unsubscribe"],
}

# Sentiment scoring
POSITIVE_WORDS = {"love", "great", "amazing", "awesome", "excellent", "perfect",
                  "fantastic", "best", "helpful", "works", "good", "nice", "happy"}
NEGATIVE_WORDS = {"broken", "error", "crash", "bug", "terrible", "hate", "worst",
                  "frustrated", "disappointed", "confusing", "difficult", "slow",
                  "fail", "useless", "cancel", "refund", "waste"}


def _get_feedback():
    """Fetch all feedback from the feedback DB."""
    return query_db("feedback")


def _get_support_tickets():
    """Fetch support tickets for cross-referencing."""
    return query_db("support_tickets")


def _get_roadmap():
    """Fetch feature roadmap for status checking."""
    return query_db("feature_roadmap")


def _score_sentiment(text):
    """Simple keyword-based sentiment score: -1 to +1."""
    if not text:
        return 0
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0
    return (pos - neg) / total


def ingest(args):
    """Record user feedback into the feedback database."""
    now = datetime.now(timezone.utc)
    source_label = args.source.replace("-", " ").title()
    cat_label = args.category.replace("-", " ").title()

    row = {
        "Name":     f"[{source_label}] {args.summary[:80]}",
        "Source":   source_label,
        "Category": cat_label,
        "Status":   "New",
        "Priority": args.priority or "P3",
        "Date":     now.strftime("%Y-%m-%d"),
        "Notes":    args.summary,
    }
    if args.user_email:
        row["Email"] = args.user_email

    add_row("feedback", row)

    print("=" * 60)
    print("  📝 FEEDBACK RECORDED")
    print("=" * 60)
    print(f"  Source:    {SOURCE_ICONS.get(args.source, '?')} {source_label}")
    print(f"  Category: {CATEGORY_ICONS.get(args.category, '?')} {cat_label}")
    print(f"  Priority: {args.priority or 'P3'}")
    print(f"  Summary:  {args.summary[:100]}")
    if args.user_email:
        print(f"  User:     {args.user_email}")
    print(f"  Date:     {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("─" * 60)

    log_task(AGENT, f"Feedback ingested: {args.source}/{args.category}",
             "Complete", args.priority or "P3",
             f"source={args.source}, category={args.category}")


def categorize(args):
    """Auto-categorize uncategorized feedback based on keyword matching."""
    feedback = _get_feedback()
    uncategorized = [f for f in feedback
                     if not f.get("Category")
                     or (f.get("Category") or "").lower() in ("", "uncategorized", "new", "unknown")]

    print("=" * 60)
    print("  🏷️ AUTO-CATEGORIZATION")
    print("=" * 60)

    if not uncategorized:
        all_count = len(feedback)
        print(f"\n  All {all_count} feedback items are already categorized.")
        print("─" * 60)
        log_task(AGENT, "Feedback auto-categorize", "Complete", "P3",
                 f"all {all_count} already categorized")
        return

    categorized_count = 0
    results = defaultdict(int)

    for item in uncategorized:
        text = ((item.get("Name") or "") + " " + (item.get("Notes") or "")).lower()
        best_category = None
        best_score = 0

        for cat, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_category = cat

        if best_category and best_score > 0:
            cat_label = best_category.replace("-", " ").title()
            update_row(item["_id"], "feedback", {"Category": cat_label, "Status": "Categorized"})
            results[best_category] += 1
            categorized_count += 1
            name = (item.get("Name") or "?")[:40]
            print(f"  {CATEGORY_ICONS.get(best_category, '?')} {name:<42} → {cat_label}")
        else:
            name = (item.get("Name") or "?")[:40]
            print(f"  ❓ {name:<42} → Could not classify")

    print(f"\n  {'─' * 50}")
    print(f"  Categorized: {categorized_count}/{len(uncategorized)} items")
    for cat, count in sorted(results.items(), key=lambda x: -x[1]):
        icon = CATEGORY_ICONS.get(cat, "?")
        print(f"    {icon} {cat.replace('-', ' ').title()}: {count}")
    print("─" * 60)

    log_task(AGENT, "Feedback auto-categorization", "Complete", "P2",
             f"categorized={categorized_count}/{len(uncategorized)}")


def feature_requests(args):
    """List feature requests ranked by frequency and user demand."""
    feedback = _get_feedback()
    fr_items = [f for f in feedback
                if (f.get("Category") or "").lower() in ("feature request", "feature-request")]

    print("=" * 60)
    print("  💡 FEATURE REQUESTS — RANKED BY DEMAND")
    print("=" * 60)

    if not fr_items:
        print("\n  No feature requests found in feedback DB.")
        print("  Ingest feedback with --action ingest --category feature-request")
        print("─" * 60)
        log_task(AGENT, "Feature requests review", "Complete", "P3", "No requests")
        return

    # Group by summary keywords (simplified dedup)
    request_groups = defaultdict(list)
    for item in fr_items:
        summary = (item.get("Notes") or item.get("Name") or "Unknown").strip()
        # Normalize to first 50 chars as grouping key
        key = summary[:50].lower().strip()
        request_groups[key].append(item)

    # Sort by count (most requested first)
    ranked = sorted(request_groups.items(), key=lambda x: -len(x[1]))

    # Cross-reference roadmap
    roadmap = _get_roadmap()
    roadmap_features = {(r.get("Feature") or "").lower(): r for r in roadmap}

    print(f"\n  {'#':>3}  {'Request':<38} {'Count':>5} {'Prio':>5} {'Roadmap':>10}")
    print(f"  {'─' * 65}")

    for rank, (key, items) in enumerate(ranked[:15], 1):
        count = len(items)
        display = (items[0].get("Notes") or items[0].get("Name") or "?")[:38]
        priorities = [i.get("Priority") or "P3" for i in items]
        top_prio = min(priorities, key=lambda p: int(p[1]) if len(p) == 2 else 9)
        sources = set(i.get("Source") or "?" for i in items)

        # Check if on roadmap
        on_roadmap = "─"
        for rf_key, rf_val in roadmap_features.items():
            if any(word in rf_key for word in key.split()[:3] if len(word) > 3):
                on_roadmap = rf_val.get("Status") or "Tracked"
                break

        bar = "█" * min(count, 10)
        print(f"  {rank:>3}. {display:<38} {count:>5} {top_prio:>5} {on_roadmap:>10}")
        if count > 1:
            print(f"       Sources: {', '.join(sources)}  {bar}")

    total_requests = len(fr_items)
    unique_requests = len(ranked)
    print(f"\n  {'─' * 65}")
    print(f"  Total feedback items: {total_requests}")
    print(f"  Unique requests:      {unique_requests}")
    print("─" * 60)

    log_task(AGENT, "Feature requests ranking", "Complete", "P2",
             f"total={total_requests}, unique={unique_requests}")


def sentiment_report(args):
    """Analyze feedback sentiment: positive/negative/neutral ratio and trends."""
    feedback = _get_feedback()

    print("=" * 60)
    print("  😊 FEEDBACK SENTIMENT REPORT")
    print("=" * 60)

    if not feedback:
        print("\n  No feedback to analyze.")
        print("─" * 60)
        log_task(AGENT, "Sentiment report", "Complete", "P3", "No feedback")
        return

    # Score each item
    sentiments = {"positive": [], "negative": [], "neutral": []}
    category_sentiment = defaultdict(list)
    source_sentiment = defaultdict(list)

    for item in feedback:
        text = (item.get("Notes") or "") + " " + (item.get("Name") or "")
        score = _score_sentiment(text)
        bucket = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        sentiments[bucket].append(item)
        cat = item.get("Category") or "Unknown"
        category_sentiment[cat].append(score)
        src = item.get("Source") or "Unknown"
        source_sentiment[src].append(score)

    total = len(feedback)
    pos_count = len(sentiments["positive"])
    neg_count = len(sentiments["negative"])
    neu_count = len(sentiments["neutral"])

    pos_pct = pos_count / total * 100
    neg_pct = neg_count / total * 100
    neu_pct = neu_count / total * 100

    print(f"\n  OVERALL SENTIMENT ({total} items)")
    print(f"  {'─' * 50}")
    print(f"    😊 Positive:  {pos_count:>4} ({pos_pct:>5.1f}%)")
    print(f"    😐 Neutral:   {neu_count:>4} ({neu_pct:>5.1f}%)")
    print(f"    😤 Negative:  {neg_count:>4} ({neg_pct:>5.1f}%)")

    # Visual ratio bar
    pos_bar = "🟢" * max(1, round(pos_pct / 10)) if pos_count > 0 else ""
    neu_bar = "🟡" * max(1, round(neu_pct / 10)) if neu_count > 0 else ""
    neg_bar = "🔴" * max(1, round(neg_pct / 10)) if neg_count > 0 else ""
    print(f"    [{pos_bar}{neu_bar}{neg_bar}]")

    # Net Promoter-style score
    nps_like = ((pos_count - neg_count) / total * 100) if total > 0 else 0
    nps_icon = "✅" if nps_like > 20 else "🟡" if nps_like > 0 else "🔴"
    print(f"\n    Net sentiment score: {nps_icon} {nps_like:+.0f}")

    # Sentiment by source
    print(f"\n  SENTIMENT BY SOURCE:")
    print(f"  {'─' * 50}")
    for src, scores in sorted(source_sentiment.items()):
        avg = sum(scores) / len(scores) if scores else 0
        icon = SOURCE_ICONS.get(src.lower().replace(" ", "-"), "?")
        sentiment_icon = "😊" if avg > 0.1 else "😤" if avg < -0.1 else "😐"
        print(f"    {icon} {src:<20} {sentiment_icon} avg={avg:+.2f} ({len(scores)} items)")

    # Top pain points (most negative items)
    print(f"\n  TOP PAIN POINTS:")
    print(f"  {'─' * 50}")
    negative_items = sentiments["negative"]
    if negative_items:
        # Sort by most negative (estimated from category)
        for item in negative_items[:5]:
            name = (item.get("Name") or "?")[:45]
            cat = item.get("Category") or "?"
            src = item.get("Source") or "?"
            print(f"    🔴 {name}")
            print(f"       {cat} via {src}")
    else:
        print("    ✅ No strongly negative feedback — excellent!")

    print("─" * 60)

    log_task(AGENT, "Sentiment report", "Complete", "P2",
             f"positive={pos_pct:.0f}%, negative={neg_pct:.0f}%, nps={nps_like:+.0f}")


def feedback_to_roadmap(args):
    """Convert top feature requests into roadmap items."""
    feedback = _get_feedback()
    fr_items = [f for f in feedback
                if (f.get("Category") or "").lower() in ("feature request", "feature-request")]

    top_n = args.top_n or 5

    print("=" * 60)
    print(f"  🗺️ FEEDBACK → ROADMAP (top {top_n})")
    print("=" * 60)

    if not fr_items:
        print("\n  No feature requests to convert.")
        print("─" * 60)
        log_task(AGENT, "Feedback to roadmap", "Complete", "P3", "No requests")
        return

    # Group and rank
    request_groups = defaultdict(list)
    for item in fr_items:
        summary = (item.get("Notes") or item.get("Name") or "").strip()
        key = summary[:50].lower().strip()
        request_groups[key].append(item)

    ranked = sorted(request_groups.items(), key=lambda x: -len(x[1]))[:top_n]

    # Check existing roadmap to avoid duplicates
    roadmap = _get_roadmap()
    existing = {(r.get("Feature") or "").lower() for r in roadmap}

    created = 0
    skipped = 0

    for key, items in ranked:
        display = (items[0].get("Notes") or items[0].get("Name") or "?")[:60]
        count = len(items)
        priorities = [i.get("Priority") or "P3" for i in items]
        top_prio = min(priorities, key=lambda p: int(p[1]) if len(p) == 2 else 9)
        sources = list(set(i.get("Source") or "?" for i in items))

        # Dedup check against roadmap
        feature_title = display.replace("[", "").replace("]", "").strip()
        if any(word in feat for feat in existing for word in feature_title.lower().split()[:3] if len(word) > 4):
            print(f"  ⏭️ Already on roadmap: {feature_title[:50]}")
            skipped += 1
            continue

        # Create roadmap entry
        add_row("feature_roadmap", {
            "Feature":    feature_title,
            "Status":     "Backlog",
            "Priority":   top_prio,
            "Category":   "User Requested",
            "Owner":      "Product Team",
            "User Story": f"Requested {count}x via {', '.join(sources[:3])}. Source: user-feedback pipeline.",
        })
        created += 1
        print(f"  ✅ Created: {feature_title[:50]}")
        print(f"     Demand: {count} requests | Priority: {top_prio} | Sources: {', '.join(sources[:3])}")

    print(f"\n  {'─' * 50}")
    print(f"  Created:  {created} roadmap items")
    print(f"  Skipped:  {skipped} (already on roadmap)")
    print(f"  Total FR: {len(fr_items)} feedback items processed")
    print("─" * 60)

    log_task(AGENT, f"Feedback to roadmap: {created} created",
             "Complete", "P1",
             f"created={created}, skipped={skipped}, from={len(fr_items)} requests")


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Agent — User Feedback Pipeline")
    parser.add_argument("--action", required=True,
                        choices=["ingest", "categorize", "feature-requests",
                                 "sentiment-report", "feedback-to-roadmap"])
    parser.add_argument("--source", choices=SOURCES, help="Feedback source channel")
    parser.add_argument("--category", choices=CATEGORIES, help="Feedback category")
    parser.add_argument("--summary", help="Feedback summary text")
    parser.add_argument("--user-email", help="Optional user email")
    parser.add_argument("--priority", choices=["P1", "P2", "P3", "P4"])
    parser.add_argument("--top-n", type=int, default=5, help="Number of top requests to convert")
    args = parser.parse_args()

    dispatch = {
        "ingest":             ingest,
        "categorize":         categorize,
        "feature-requests":   feature_requests,
        "sentiment-report":   sentiment_report,
        "feedback-to-roadmap": feedback_to_roadmap,
    }
    dispatch[args.action](args)
