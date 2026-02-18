"""
Hedge Edge — Shared Package
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Centralized API clients, access control, and utilities for all agents.

Clients:
    notion_client    — Notion ERP (26 databases, schema-wired, access-controlled)
    supabase_client  — Supabase auth, user data, subscriptions
    discord_client   — Discord bot messaging, channels, webhooks
    resend_client    — Resend email campaigns, audiences, contacts
    youtube_client   — YouTube uploads, analytics, channel stats
    instagram_client — Instagram posts, reels, carousels, insights
    linkedin_client  — LinkedIn posts, articles, images
    calcom_client    — Cal.com scheduling, bookings, availability
    github_client    — GitHub repos, issues, PRs, releases
    vercel_client    — Vercel deployments, domains, projects
    gsheets_client   — Google Sheets read/write/append
    gocardless_client — GoCardless payments, mandates, payouts
    creem_client     — Creem.io subscriptions, customers, checkouts
    railway_client   — Railway deployments, services, env vars, logs
    shortio_client   — Short.io link shortening, click analytics, QR codes
    cloudflare_client — Cloudflare DNS, CDN, cache, SSL, firewall, analytics

Registry & Security:
    api_registry     — Central API→Agent access control matrix
    access_guard     — Enforced access control with audit logging

Utilities:
    linkedin_refresh      — LinkedIn token auto-refresh
    scheduled_tasks       — Periodic maintenance (token refresh, health checks)
    dashboard             — Analytics dashboard aggregator (all services)
    setup_notion_schemas  — Notion ERP schema provisioning (run once)
    cloudflare_harden     — Cloudflare security audit & hardening checklist
"""
