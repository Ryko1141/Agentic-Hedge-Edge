"""
Hedge Edge — API Registry & Access Control
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Central mapping of which agents can access which APIs,
and what operations they're permitted to perform.

Usage:
    from shared.api_registry import get_agent_apis, can_access
"""

# ──────────────────────────────────────────────
# API → Agent Access Matrix
# ──────────────────────────────────────────────
# Each API lists the agents that may use it and their permission level.
# "full"  = read + write + admin operations
# "write" = read + write (create/update)
# "read"  = read-only queries

API_ACCESS = {
    "notion": {
        "orchestrator":        "full",
        "business_strategist": "full",
        "finance":             "full",
        "sales":               "full",
        "marketing":           "full",
        "content_engine":      "full",
        "product":             "full",
        "community_manager":   "full",
        "analytics":           "full",
    },
    "supabase": {
        "product":             "full",   # Schema, migrations, user management
        "analytics":           "read",   # Query user data, subscription metrics
        "sales":               "read",   # Lookup user subscriptions
        "community_manager":   "read",   # Verify user accounts for support
        "finance":             "read",   # Subscription revenue data
        "orchestrator":        "read",
    },
    "cal_com": {
        "sales":               "full",   # Create/manage event types, bookings
        "orchestrator":        "read",   # Check schedules
    },
    "discord": {
        "community_manager":   "full",   # Messages, moderation, channels
        "orchestrator":        "write",  # Post announcements
        "marketing":           "write",  # Post campaigns
        "product":             "write",  # Post release notes
        "content_engine":      "read",   # Read feedback for content ideas
    },
    "resend": {
        "marketing":           "full",   # Email campaigns, sequences
        "sales":               "write",  # Send follow-ups, proposals
        "community_manager":   "write",  # Welcome emails, support
        "orchestrator":        "read",   # Email analytics
    },
    "youtube": {
        "content_engine":      "full",   # Upload, manage, analytics
        "analytics":           "read",   # Channel performance
        "marketing":           "read",   # Campaign performance
    },
    "github": {
        "product":             "full",   # Repos, PRs, issues, releases
        "orchestrator":        "read",   # CI/CD status
        "analytics":           "read",   # Commit/PR metrics
    },
    "vercel": {
        "product":             "full",   # Deploy, rollback
        "marketing":           "write",  # Landing page updates
        "analytics":           "read",   # Deployment analytics
    },
    "google_sheets": {
        "finance":             "full",   # Financial models, P&L
        "analytics":           "full",   # Dashboards, reports
        "business_strategist": "read",   # Strategic data
        "sales":               "write",  # CRM exports
    },
    "gocardless": {
        "finance":             "full",   # Payments, mandates, refunds
        "analytics":           "read",   # Payment metrics
    },
    "creem": {
        "finance":             "full",   # Subscriptions, invoices, refunds
        "analytics":           "read",   # Revenue metrics
        "sales":               "read",   # Customer lookup
    },
    "linkedin": {
        "content_engine":      "full",   # Post articles, images
        "marketing":           "write",  # Sponsored content
        "business_strategist": "read",   # Company analytics
        "analytics":           "read",   # Engagement metrics
    },
    "instagram": {
        "content_engine":      "full",   # Posts, reels, stories
        "marketing":           "write",  # Promote content
        "analytics":           "read",   # IG insights
    },
    "railway": {
        "product":             "full",   # Deploy, redeploy, env vars, logs
        "orchestrator":        "read",   # Deployment status, health checks
        "analytics":           "read",   # Deployment metrics
    },
    "shortio": {
        "marketing":           "full",   # Create/manage campaign links, UTMs
        "content_engine":      "write",  # Create links for content distribution
        "sales":               "write",  # Create tracking links for outreach
        "analytics":           "read",   # Click stats, geo data, referrers
        "orchestrator":        "read",   # Link health monitoring
    },
    "cloudflare": {
        "product":             "full",   # DNS, SSL, cache, firewall, analytics
        "orchestrator":        "read",   # Zone health, deployment verification
        "analytics":           "read",   # Traffic analytics, threat data
    },
}


def get_agent_apis(agent: str) -> dict[str, str]:
    """Return {api_name: permission_level} for a given agent."""
    result = {}
    for api, agents in API_ACCESS.items():
        if agent in agents:
            result[api] = agents[agent]
    return result


def can_access(agent: str, api: str, operation: str = "read") -> bool:
    """
    Check if an agent can perform an operation on an API.

    Args:
        agent: Agent key (e.g., 'finance')
        api: API key (e.g., 'creem')
        operation: 'read', 'write', or 'full'
    """
    level = API_ACCESS.get(api, {}).get(agent)
    if not level:
        return False
    if operation == "read":
        return level in ("read", "write", "full")
    if operation == "write":
        return level in ("write", "full")
    if operation == "full":
        return level == "full"
    return False


def get_api_agents(api: str) -> dict[str, str]:
    """Return {agent_name: permission_level} for a given API."""
    return API_ACCESS.get(api, {})
