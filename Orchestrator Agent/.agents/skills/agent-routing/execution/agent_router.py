#!/usr/bin/env python3
"""
agent_router.py — Orchestrator Agent Intent Classification & Routing

Classifies user requests by matching intent keywords to specialist agent
domains, returns routing decisions with confidence scores, and tracks
routing accuracy over time via the Notion task_log.

Usage:
    python agent_router.py --action classify --request "I need help with my YouTube content schedule"
    python agent_router.py --action classify --request "Our MRR dropped and we need to cut expenses"
    python agent_router.py --action route-history
    python agent_router.py --action agent-map
"""

import sys, os, argparse, json, re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task

# ── Agent Domain Registry ────────────────────────────────────────────
AGENT_DOMAINS = {
    "business_strategist": {
        "label": "Business Strategist Agent",
        "keywords": [
            "strategy", "growth", "pricing", "competition", "partnerships",
            "moats", "competitive", "market research", "OKR", "initiative",
            "strategic", "partner", "SWOT", "positioning", "differentiation",
        ],
        "databases": ["okrs", "competitors", "strategic_initiatives", "partnerships"],
    },
    "content_engine": {
        "label": "Content Engine Agent",
        "keywords": [
            "video", "content", "social", "youtube", "instagram", "linkedin",
            "post", "script", "thumbnail", "reel", "shorts", "tiktok",
            "schedule", "editorial", "calendar", "caption", "hook",
        ],
        "databases": ["content_calendar", "video_pipeline"],
    },
    "marketing": {
        "label": "Marketing Agent",
        "keywords": [
            "email", "seo", "ads", "landing page", "newsletter", "lead magnet",
            "keywords", "funnel", "campaign", "nurture", "sequence", "subject line",
            "open rate", "click rate", "paid", "organic", "PPC", "retarget",
        ],
        "databases": ["campaigns", "email_sequences", "email_sends", "seo_keywords", "landing_page_tests"],
    },
    "sales": {
        "label": "Sales Agent",
        "keywords": [
            "lead", "demo", "call", "crm", "pipeline", "proposal", "close",
            "qualify", "follow-up", "deal", "prospect", "objection", "pricing call",
            "trial", "onboard", "sign up", "conversion",
        ],
        "databases": ["leads_crm", "demo_log", "proposals"],
    },
    "finance": {
        "label": "Finance Agent",
        "keywords": [
            "revenue", "mrr", "expense", "commission", "invoice", "tax",
            "p&l", "cash flow", "runway", "burn rate", "ib", "payout",
            "budget", "profit", "loss", "gocardless", "pnl",
        ],
        "databases": ["mrr_tracker", "expense_log", "ib_commissions", "pnl_snapshots"],
    },
    "community_manager": {
        "label": "Community Manager Agent",
        "keywords": [
            "discord", "community", "onboard", "support", "ticket", "feedback",
            "sentiment", "member", "event", "welcome", "engagement", "moderation",
        ],
        "databases": ["support_tickets", "feedback", "community_events"],
    },
    "analytics": {
        "label": "Analytics Agent",
        "keywords": [
            "metrics", "dashboard", "funnel", "cohort", "churn", "attribution",
            "a/b test", "kpi", "report", "retention", "ltv", "cac", "arpu",
            "conversion rate", "drop-off", "segment",
        ],
        "databases": ["kpi_snapshots", "funnel_metrics"],
    },
    "product": {
        "label": "Product Agent",
        "keywords": [
            "feature", "bug", "release", "roadmap", "spec", "qa", "integration",
            "mt4", "ctrader", "prop firm", "platform", "api", "webhook", "deploy",
        ],
        "databases": ["feature_roadmap", "bug_tracker", "release_log"],
    },
}


def _score_request(request_text):
    """Score each agent domain against the request text.  Returns sorted list of (agent_key, score, matched_keywords)."""
    text_lower = request_text.lower()
    scores = []
    for key, domain in AGENT_DOMAINS.items():
        matched = [kw for kw in domain["keywords"] if kw in text_lower]
        score = len(matched) / len(domain["keywords"]) if domain["keywords"] else 0
        if matched:
            scores.append((key, round(score * 100, 1), matched))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ── Actions ───────────────────────────────────────────────────────────

def classify(args):
    """Classify user intent and output routing decision."""
    request = args.request
    if not request:
        print("❌ --request is required for classify action"); return

    scores = _score_request(request)

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              🧭  INTENT CLASSIFICATION RESULT                  ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Request: {request[:54]:<54} ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if not scores:
        print("║  ⚠️  No matching agent found — routing to Orchestrator        ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        log_task("Orchestrator", f"Route: unclassified", "Complete", "P3",
                 f"No match for: {request[:80]}")
        return

    primary = scores[0]
    domain_info = AGENT_DOMAINS[primary[0]]
    print(f"║  🎯 PRIMARY ROUTE: {domain_info['label']:<43} ║")
    print(f"║     Confidence: {primary[1]:>5.1f}%  |  Matched: {', '.join(primary[2][:4]):<22} ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if len(scores) > 1:
        print("║  Secondary routes:                                              ║")
        for agent_key, score, matched in scores[1:4]:
            label = AGENT_DOMAINS[agent_key]["label"]
            kws = ", ".join(matched[:3])
            print(f"║    • {label:<28} {score:>5.1f}%  [{kws:<17}] ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

    # Multi-agent routing recommendation
    multi = [s for s in scores if s[1] >= 20.0]
    if len(multi) > 1:
        agents_str = " + ".join(AGENT_DOMAINS[s[0]]["label"] for s in multi[:3])
        print(f"║  🔀 MULTI-AGENT: {agents_str:<45} ║")
    else:
        print(f"║  🔀 SINGLE-AGENT dispatch sufficient                           ║")

    print("╚══════════════════════════════════════════════════════════════════╝")

    # Log routing decision to Notion
    routing_data = {
        "primary": domain_info["label"],
        "confidence": primary[1],
        "secondary": [AGENT_DOMAINS[s[0]]["label"] for s in scores[1:3]],
    }
    log_task("Orchestrator", f"Route: {domain_info['label']}", "Complete", "P3",
             json.dumps(routing_data))

    # Return structured result for programmatic use
    return {"primary": primary[0], "confidence": primary[1],
            "all_scores": scores, "multi_agent": len(multi) > 1}


def route_history(args):
    """Query task_log for recent routing decisions and show stats."""
    items = query_db("task_log", filter={
        "property": "Agent", "select": {"equals": "Orchestrator"}
    })
    routes = [t for t in items if (t.get("Task", "") or "").startswith("Route:")]
    routes.sort(key=lambda x: x.get("Timestamp", ""), reverse=True)

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              📊  ROUTING HISTORY & ACCURACY                    ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if not routes:
        print("║  No routing decisions logged yet.                              ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        return

    # Tally routes by target agent
    tally = {}
    for r in routes:
        target = (r.get("Task", "") or "").replace("Route: ", "")
        tally[target] = tally.get(target, 0) + 1

    total = len(routes)
    for agent_name, count in sorted(tally.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"║  {agent_name:<26} {bar} {count:>3} ({pct:>5.1f}%) ║")

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Total routing decisions: {total:<37} ║")
    print(f"║  Unique agents targeted:  {len(tally):<37} ║")

    # Show last 5 routes
    print("╠══════════════════════════════════════════════════════════════════╣")
    print("║  Recent routes:                                                 ║")
    for r in routes[:5]:
        ts = (r.get("Timestamp", "") or "")[:16]
        task = (r.get("Task", "") or "")[:40]
        print(f"║    {ts}  {task:<42} ║")

    print("╚══════════════════════════════════════════════════════════════════╝")
    log_task("Orchestrator", "Route history reviewed", "Complete", "P3",
             f"{total} routes across {len(tally)} agents")


def agent_map(args):
    """Print the full agent capability map."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              🗺️  AGENT CAPABILITY MAP                          ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    for key, domain in AGENT_DOMAINS.items():
        label = domain["label"]
        kw_str = ", ".join(domain["keywords"][:6])
        db_str = ", ".join(domain["databases"][:4])
        print(f"║                                                                  ║")
        print(f"║  🤖 {label:<59}║")
        print(f"║     Keywords: {kw_str:<49}║")
        print(f"║     Databases: {db_str:<48}║")
        print(f"║{'─' * 66}║")

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Total agents: {len(AGENT_DOMAINS)}  |  Total domains: {sum(len(d['keywords']) for d in AGENT_DOMAINS.values())} keywords     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")


# ── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator Agent Router — Intent Classification & Dispatch")
    parser.add_argument("--action", required=True,
                        choices=["classify", "route-history", "agent-map"])
    parser.add_argument("--request", help="User request text to classify")
    args = parser.parse_args()
    {"classify": classify, "route-history": route_history,
     "agent-map": agent_map}[args.action](args)
