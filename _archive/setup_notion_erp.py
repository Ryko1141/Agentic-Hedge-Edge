"""
Hedge Edge ERP — Notion Database Setup Script
Creates all ~22 databases under the AGENTIC BUSINESS page.
Run once, then copy the database IDs into shared/notion_client.py.
"""
import os, json, sys, time
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
if not NOTION_TOKEN:
    # Fallback: read from mcp.json
    mcp_path = os.path.join(os.path.dirname(__file__), ".vscode", "mcp.json")
    if os.path.exists(mcp_path):
        with open(mcp_path) as f:
            mcp = json.load(f)
        NOTION_TOKEN = mcp.get("servers", {}).get("makenotion/notion-mcp-server", {}).get("env", {}).get("NOTION_TOKEN")

if not NOTION_TOKEN:
    print("ERROR: No Notion token found. Set NOTION_API_KEY in .env")
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN)

# Parent page: "AGENTIC BUSINESS"
PARENT_PAGE_ID = "2fb652ea-6c6d-80aa-b4fb-e40a1a8c5248"

# ──────────────────────────────────────────────
# Helper: Create a section page under AGENTIC BUSINESS
# ──────────────────────────────────────────────
def create_section_page(title: str, icon: str) -> str:
    """Create a child page as a section header, return its ID."""
    page = notion.pages.create(
        parent={"type": "page_id", "page_id": PARENT_PAGE_ID},
        icon={"type": "emoji", "emoji": icon},
        properties={"title": {"title": [{"text": {"content": title}}]}},
    )
    print(f"  📄 Section: {icon} {title} → {page['id']}")
    return page["id"]


# ──────────────────────────────────────────────
# Helper: Create a database under a section page
# ──────────────────────────────────────────────
def create_database(parent_page_id: str, title: str, icon: str, properties: dict) -> str:
    """Create a Notion database with given properties, return its ID."""
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"text": {"content": title}}],
        icon={"type": "emoji", "emoji": icon},
        properties=properties,
    )
    print(f"    📊 DB: {icon} {title} → {db['id']}")
    time.sleep(0.35)  # Rate limit safety
    return db["id"]


# ──────────────────────────────────────────────
# Database Schemas
# ──────────────────────────────────────────────

def build_all_databases():
    db_registry = {}

    # ═══════════════════════════════════════════
    # 1. STRATEGY & OKRs — Business Strategist Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Strategy & OKRs", "🎯")

    db_registry["okrs"] = create_database(section, "Quarterly OKRs", "🎯", {
        "Objective":     {"title": {}},
        "Quarter":       {"select": {"options": [
            {"name": "Q1 2026", "color": "blue"},
            {"name": "Q2 2026", "color": "green"},
            {"name": "Q3 2026", "color": "yellow"},
            {"name": "Q4 2026", "color": "red"},
        ]}},
        "Key Result":    {"rich_text": {}},
        "Progress %":    {"number": {"format": "percent"}},
        "Status":        {"select": {"options": [
            {"name": "On Track",  "color": "green"},
            {"name": "At Risk",   "color": "yellow"},
            {"name": "Off Track", "color": "red"},
            {"name": "Complete",  "color": "blue"},
        ]}},
        "Owner Agent":   {"select": {"options": [
            {"name": "Business Strategist", "color": "purple"},
            {"name": "Marketing",           "color": "pink"},
            {"name": "Sales",               "color": "orange"},
            {"name": "Finance",             "color": "green"},
            {"name": "Product",             "color": "blue"},
            {"name": "Content Engine",      "color": "yellow"},
        ]}},
        "Due Date":      {"date": {}},
        "Notes":         {"rich_text": {}},
    })

    db_registry["competitors"] = create_database(section, "Competitor Tracker", "🔍", {
        "Competitor":    {"title": {}},
        "Category":      {"select": {"options": [
            {"name": "Trade Copier",   "color": "blue"},
            {"name": "Hedge Tool",     "color": "green"},
            {"name": "Risk Manager",   "color": "yellow"},
            {"name": "Prop Firm Tool", "color": "red"},
        ]}},
        "Threat Level":  {"select": {"options": [
            {"name": "Critical", "color": "red"},
            {"name": "High",     "color": "orange"},
            {"name": "Medium",   "color": "yellow"},
            {"name": "Low",      "color": "green"},
            {"name": "Noise",    "color": "gray"},
        ]}},
        "Weighted Score": {"number": {"format": "number"}},
        "Pricing":       {"rich_text": {}},
        "Platforms":     {"multi_select": {"options": [
            {"name": "MT4", "color": "blue"},
            {"name": "MT5", "color": "green"},
            {"name": "cTrader", "color": "yellow"},
        ]}},
        "Key Strengths": {"rich_text": {}},
        "Key Weaknesses":{"rich_text": {}},
        "Last Updated":  {"date": {}},
        "URL":           {"url": {}},
    })

    db_registry["strategic_initiatives"] = create_database(section, "Strategic Initiatives", "🚀", {
        "Initiative":    {"title": {}},
        "Priority":      {"select": {"options": [
            {"name": "P0 - Critical", "color": "red"},
            {"name": "P1 - High",     "color": "orange"},
            {"name": "P2 - Medium",   "color": "yellow"},
            {"name": "P3 - Low",      "color": "green"},
        ]}},
        "Impact Score":  {"number": {"format": "number"}},
        "Effort Score":  {"number": {"format": "number"}},
        "Status":        {"select": {"options": [
            {"name": "Proposed",    "color": "gray"},
            {"name": "In Progress", "color": "blue"},
            {"name": "Complete",    "color": "green"},
            {"name": "Blocked",     "color": "red"},
        ]}},
        "Owner Agent":   {"rich_text": {}},
        "Target Date":   {"date": {}},
        "Outcome":       {"rich_text": {}},
    })

    # ═══════════════════════════════════════════
    # 2. FINANCE — Finance Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Finance", "💰")

    db_registry["mrr_tracker"] = create_database(section, "MRR/ARR Tracker", "📈", {
        "Date":          {"title": {}},
        "MRR":           {"number": {"format": "dollar"}},
        "ARR":           {"number": {"format": "dollar"}},
        "New Subs":      {"number": {"format": "number"}},
        "Churned Subs":  {"number": {"format": "number"}},
        "Net New":       {"number": {"format": "number"}},
        "Churn Rate":    {"number": {"format": "percent"}},
        "ARPU":          {"number": {"format": "dollar"}},
        "Free Users":    {"number": {"format": "number"}},
        "Paid Users":    {"number": {"format": "number"}},
        "Total Users":   {"number": {"format": "number"}},
    })

    db_registry["expense_log"] = create_database(section, "Expense Log", "💳", {
        "Description":   {"title": {}},
        "Amount":        {"number": {"format": "dollar"}},
        "Category":      {"select": {"options": [
            {"name": "Infrastructure", "color": "blue"},
            {"name": "Marketing",      "color": "pink"},
            {"name": "Tools & SaaS",   "color": "purple"},
            {"name": "Legal",          "color": "gray"},
            {"name": "Domains & DNS",  "color": "yellow"},
            {"name": "Other",          "color": "default"},
        ]}},
        "Date":          {"date": {}},
        "Recurring":     {"checkbox": {}},
        "Frequency":     {"select": {"options": [
            {"name": "Monthly",  "color": "blue"},
            {"name": "Annual",   "color": "green"},
            {"name": "One-off",  "color": "gray"},
        ]}},
        "Vendor":        {"rich_text": {}},
        "Notes":         {"rich_text": {}},
    })

    db_registry["ib_commissions"] = create_database(section, "IB Commission Log", "🏦", {
        "Period":        {"title": {}},
        "Broker":        {"select": {"options": [
            {"name": "Vantage",     "color": "blue"},
            {"name": "BlackBull",   "color": "green"},
            {"name": "IC Markets",  "color": "yellow"},
            {"name": "Pepperstone", "color": "red"},
            {"name": "VT Markets",  "color": "purple"},
        ]}},
        "Total Commission": {"number": {"format": "dollar"}},
        "Lots Traded":   {"number": {"format": "number"}},
        "Clients":       {"number": {"format": "number"}},
        "Avg $/Lot":     {"number": {"format": "dollar"}},
        "Date":          {"date": {}},
        "MoM Growth":    {"number": {"format": "percent"}},
        "Top Client":    {"rich_text": {}},
    })

    db_registry["pnl_snapshots"] = create_database(section, "P&L Snapshots", "📊", {
        "Period":        {"title": {}},
        "Revenue SaaS":  {"number": {"format": "dollar"}},
        "Revenue IB":    {"number": {"format": "dollar"}},
        "Total Revenue": {"number": {"format": "dollar"}},
        "Total Expenses":{"number": {"format": "dollar"}},
        "Net Profit":    {"number": {"format": "dollar"}},
        "Margin %":      {"number": {"format": "percent"}},
        "Cash Runway Months": {"number": {"format": "number"}},
        "Date":          {"date": {}},
    })

    # ═══════════════════════════════════════════
    # 3. SALES PIPELINE — Sales Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Sales Pipeline", "📈")

    db_registry["leads_crm"] = create_database(section, "Leads CRM", "👤", {
        "Name":          {"title": {}},
        "Email":         {"email": {}},
        "Source":        {"select": {"options": [
            {"name": "Discord",    "color": "purple"},
            {"name": "YouTube",    "color": "red"},
            {"name": "LinkedIn",   "color": "blue"},
            {"name": "Website",    "color": "green"},
            {"name": "Referral",   "color": "yellow"},
            {"name": "Reddit",     "color": "orange"},
            {"name": "Instagram",  "color": "pink"},
        ]}},
        "Stage":         {"select": {"options": [
            {"name": "New Lead",   "color": "gray"},
            {"name": "Contacted",  "color": "blue"},
            {"name": "Discovery",  "color": "yellow"},
            {"name": "Demo",       "color": "orange"},
            {"name": "Proposal",   "color": "purple"},
            {"name": "Negotiation","color": "red"},
            {"name": "Won",        "color": "green"},
            {"name": "Lost",       "color": "default"},
        ]}},
        "Deal Value":    {"number": {"format": "dollar"}},
        "Plan Interest": {"select": {"options": [
            {"name": "Starter",  "color": "blue"},
            {"name": "Pro",      "color": "green"},
            {"name": "Hedger",   "color": "purple"},
        ]}},
        "Contact Date":  {"date": {}},
        "Follow Up":     {"date": {}},
        "Notes":         {"rich_text": {}},
        "Score":         {"number": {"format": "number"}},
    })

    db_registry["demo_log"] = create_database(section, "Demo Log", "🎬", {
        "Lead Name":     {"title": {}},
        "Date":          {"date": {}},
        "Duration Min":  {"number": {"format": "number"}},
        "Outcome":       {"select": {"options": [
            {"name": "Converted",    "color": "green"},
            {"name": "Follow Up",    "color": "yellow"},
            {"name": "Not Interested","color": "red"},
            {"name": "No Show",      "color": "gray"},
        ]}},
        "Objections":    {"rich_text": {}},
        "Next Steps":    {"rich_text": {}},
        "Plan Selected": {"select": {"options": [
            {"name": "Starter",  "color": "blue"},
            {"name": "Pro",      "color": "green"},
            {"name": "Hedger",   "color": "purple"},
            {"name": "None",     "color": "gray"},
        ]}},
    })

    db_registry["proposals"] = create_database(section, "Proposals", "📝", {
        "Title":         {"title": {}},
        "Lead Name":     {"rich_text": {}},
        "Plan":          {"select": {"options": [
            {"name": "Starter",  "color": "blue"},
            {"name": "Pro",      "color": "green"},
            {"name": "Hedger",   "color": "purple"},
            {"name": "Custom",   "color": "yellow"},
        ]}},
        "Value":         {"number": {"format": "dollar"}},
        "Status":        {"select": {"options": [
            {"name": "Draft",    "color": "gray"},
            {"name": "Sent",     "color": "blue"},
            {"name": "Accepted", "color": "green"},
            {"name": "Rejected", "color": "red"},
        ]}},
        "Sent Date":     {"date": {}},
        "Expiry Date":   {"date": {}},
        "ROI Projection":{"rich_text": {}},
    })

    # ═══════════════════════════════════════════
    # 4. MARKETING — Marketing Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Marketing", "📣")

    db_registry["campaigns"] = create_database(section, "Campaigns", "📢", {
        "Campaign Name": {"title": {}},
        "Channel":       {"select": {"options": [
            {"name": "Meta Ads",   "color": "blue"},
            {"name": "Google Ads", "color": "green"},
            {"name": "YouTube",    "color": "red"},
            {"name": "LinkedIn",   "color": "blue"},
            {"name": "Reddit",     "color": "orange"},
            {"name": "Email",      "color": "yellow"},
            {"name": "SEO",        "color": "purple"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Planning",  "color": "gray"},
            {"name": "Active",    "color": "green"},
            {"name": "Paused",    "color": "yellow"},
            {"name": "Complete",  "color": "blue"},
        ]}},
        "Budget":        {"number": {"format": "dollar"}},
        "Spend":         {"number": {"format": "dollar"}},
        "Impressions":   {"number": {"format": "number"}},
        "Clicks":        {"number": {"format": "number"}},
        "Leads":         {"number": {"format": "number"}},
        "Conversions":   {"number": {"format": "number"}},
        "CAC":           {"number": {"format": "dollar"}},
        "Start Date":    {"date": {}},
        "End Date":      {"date": {}},
    })

    db_registry["email_sequences"] = create_database(section, "Email Sequences", "📧", {
        "Sequence Name": {"title": {}},
        "Type":          {"select": {"options": [
            {"name": "Welcome",       "color": "green"},
            {"name": "Nurture",       "color": "blue"},
            {"name": "Re-engagement", "color": "yellow"},
            {"name": "Onboarding",    "color": "purple"},
            {"name": "Launch",        "color": "red"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Draft",   "color": "gray"},
            {"name": "Active",  "color": "green"},
            {"name": "Paused",  "color": "yellow"},
        ]}},
        "Emails Count":  {"number": {"format": "number"}},
        "Open Rate":     {"number": {"format": "percent"}},
        "Click Rate":    {"number": {"format": "percent"}},
        "Conversion Rate":{"number": {"format": "percent"}},
        "Subscribers":   {"number": {"format": "number"}},
        "Last Updated":  {"date": {}},
    })

    db_registry["seo_keywords"] = create_database(section, "SEO Keyword Tracker", "🔑", {
        "Keyword":       {"title": {}},
        "Volume":        {"number": {"format": "number"}},
        "Difficulty":    {"number": {"format": "number"}},
        "Current Rank":  {"number": {"format": "number"}},
        "Target Rank":   {"number": {"format": "number"}},
        "Intent":        {"select": {"options": [
            {"name": "Informational", "color": "blue"},
            {"name": "Transactional", "color": "green"},
            {"name": "Navigational",  "color": "yellow"},
            {"name": "Commercial",    "color": "purple"},
        ]}},
        "Content URL":   {"url": {}},
        "Status":        {"select": {"options": [
            {"name": "Target",     "color": "gray"},
            {"name": "Ranking",    "color": "blue"},
            {"name": "Top 10",     "color": "green"},
            {"name": "Top 3",      "color": "purple"},
        ]}},
        "Last Checked":  {"date": {}},
    })

    db_registry["landing_page_tests"] = create_database(section, "Landing Page Tests", "🧪", {
        "Test Name":     {"title": {}},
        "Element":       {"select": {"options": [
            {"name": "Headline",   "color": "blue"},
            {"name": "CTA",        "color": "green"},
            {"name": "Hero Image", "color": "yellow"},
            {"name": "Pricing",    "color": "purple"},
            {"name": "Social Proof","color": "orange"},
        ]}},
        "Variant A":     {"rich_text": {}},
        "Variant B":     {"rich_text": {}},
        "Visitors":      {"number": {"format": "number"}},
        "Conversion A":  {"number": {"format": "percent"}},
        "Conversion B":  {"number": {"format": "percent"}},
        "Winner":        {"select": {"options": [
            {"name": "A",         "color": "blue"},
            {"name": "B",         "color": "green"},
            {"name": "No Diff",   "color": "gray"},
            {"name": "Running",   "color": "yellow"},
        ]}},
        "Start Date":    {"date": {}},
        "End Date":      {"date": {}},
    })

    # ═══════════════════════════════════════════
    # 5. CONTENT — Content Engine Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Content", "🎬")

    db_registry["content_calendar"] = create_database(section, "Content Calendar", "📅", {
        "Title":         {"title": {}},
        "Platform":      {"select": {"options": [
            {"name": "YouTube",    "color": "red"},
            {"name": "Instagram",  "color": "pink"},
            {"name": "LinkedIn",   "color": "blue"},
            {"name": "Blog",       "color": "green"},
            {"name": "Newsletter", "color": "yellow"},
            {"name": "TikTok",     "color": "default"},
        ]}},
        "Format":        {"select": {"options": [
            {"name": "Video",      "color": "red"},
            {"name": "Reel/Short", "color": "pink"},
            {"name": "Carousel",   "color": "blue"},
            {"name": "Article",    "color": "green"},
            {"name": "Thread",     "color": "yellow"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Idea",       "color": "gray"},
            {"name": "Scripted",   "color": "blue"},
            {"name": "In Production","color": "yellow"},
            {"name": "Review",     "color": "orange"},
            {"name": "Scheduled",  "color": "purple"},
            {"name": "Published",  "color": "green"},
        ]}},
        "Publish Date":  {"date": {}},
        "Topic":         {"rich_text": {}},
        "SEO Keyword":   {"rich_text": {}},
        "URL":           {"url": {}},
        "Repurposed From":{"rich_text": {}},
    })

    db_registry["video_pipeline"] = create_database(section, "Video Pipeline", "🎥", {
        "Title":         {"title": {}},
        "Status":        {"select": {"options": [
            {"name": "Idea",       "color": "gray"},
            {"name": "Scripted",   "color": "blue"},
            {"name": "Filming",    "color": "yellow"},
            {"name": "Editing",    "color": "orange"},
            {"name": "Thumbnail",  "color": "purple"},
            {"name": "Published",  "color": "green"},
        ]}},
        "Platform":      {"select": {"options": [
            {"name": "YouTube Long", "color": "red"},
            {"name": "YouTube Short","color": "pink"},
            {"name": "Instagram Reel","color": "purple"},
            {"name": "TikTok",      "color": "default"},
        ]}},
        "Script Link":   {"url": {}},
        "Publish Date":  {"date": {}},
        "Views":         {"number": {"format": "number"}},
        "Likes":         {"number": {"format": "number"}},
        "CTR":           {"number": {"format": "percent"}},
        "Watch Time Min":{"number": {"format": "number"}},
        "CTA":           {"rich_text": {}},
    })

    # ═══════════════════════════════════════════
    # 6. PRODUCT — Product Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Product", "🛠️")

    db_registry["feature_roadmap"] = create_database(section, "Feature Roadmap", "🗺️", {
        "Feature":       {"title": {}},
        "Priority":      {"select": {"options": [
            {"name": "P0 - Critical", "color": "red"},
            {"name": "P1 - High",     "color": "orange"},
            {"name": "P2 - Medium",   "color": "yellow"},
            {"name": "P3 - Low",      "color": "green"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Backlog",     "color": "gray"},
            {"name": "Planned",     "color": "blue"},
            {"name": "In Progress", "color": "yellow"},
            {"name": "Testing",     "color": "orange"},
            {"name": "Released",    "color": "green"},
        ]}},
        "Impact":        {"number": {"format": "number"}},
        "Effort":        {"number": {"format": "number"}},
        "Target Release":{"rich_text": {}},
        "Platform":      {"multi_select": {"options": [
            {"name": "MT5",     "color": "green"},
            {"name": "MT4",     "color": "blue"},
            {"name": "cTrader", "color": "yellow"},
            {"name": "Desktop", "color": "purple"},
        ]}},
        "Assigned To":   {"rich_text": {}},
        "Due Date":      {"date": {}},
    })

    db_registry["bug_tracker"] = create_database(section, "Bug Tracker", "🐛", {
        "Bug Title":     {"title": {}},
        "Severity":      {"select": {"options": [
            {"name": "Critical",  "color": "red"},
            {"name": "High",      "color": "orange"},
            {"name": "Medium",    "color": "yellow"},
            {"name": "Low",       "color": "green"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Open",        "color": "red"},
            {"name": "Investigating","color": "yellow"},
            {"name": "Fix In Progress","color": "blue"},
            {"name": "Resolved",    "color": "green"},
            {"name": "Won't Fix",   "color": "gray"},
        ]}},
        "Platform":      {"select": {"options": [
            {"name": "MT5",     "color": "green"},
            {"name": "MT4",     "color": "blue"},
            {"name": "cTrader", "color": "yellow"},
            {"name": "Desktop", "color": "purple"},
            {"name": "Web",     "color": "red"},
        ]}},
        "Repro Steps":   {"rich_text": {}},
        "Reporter":      {"rich_text": {}},
        "Reported Date": {"date": {}},
        "Resolved Date": {"date": {}},
    })

    db_registry["release_log"] = create_database(section, "Release Log", "📦", {
        "Version":       {"title": {}},
        "Release Date":  {"date": {}},
        "Type":          {"select": {"options": [
            {"name": "Major",   "color": "red"},
            {"name": "Minor",   "color": "yellow"},
            {"name": "Patch",   "color": "green"},
            {"name": "Hotfix",  "color": "orange"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Planning",  "color": "gray"},
            {"name": "In Dev",    "color": "blue"},
            {"name": "Testing",   "color": "yellow"},
            {"name": "Released",  "color": "green"},
        ]}},
        "Changelog":     {"rich_text": {}},
        "Features Count":{"number": {"format": "number"}},
        "Bugs Fixed":    {"number": {"format": "number"}},
    })

    # ═══════════════════════════════════════════
    # 7. COMMUNITY — Community Manager Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Community", "👥")

    db_registry["feedback"] = create_database(section, "Feedback & Requests", "💬", {
        "Title":         {"title": {}},
        "Type":          {"select": {"options": [
            {"name": "Feature Request", "color": "blue"},
            {"name": "Bug Report",      "color": "red"},
            {"name": "Improvement",     "color": "yellow"},
            {"name": "Question",        "color": "green"},
            {"name": "Complaint",       "color": "orange"},
        ]}},
        "Priority":      {"select": {"options": [
            {"name": "Critical", "color": "red"},
            {"name": "High",     "color": "orange"},
            {"name": "Medium",   "color": "yellow"},
            {"name": "Low",      "color": "green"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "New",          "color": "gray"},
            {"name": "Acknowledged", "color": "blue"},
            {"name": "Planned",      "color": "yellow"},
            {"name": "Shipped",      "color": "green"},
            {"name": "Won't Do",     "color": "default"},
        ]}},
        "Source":        {"select": {"options": [
            {"name": "Discord",    "color": "purple"},
            {"name": "Email",      "color": "blue"},
            {"name": "In-App",     "color": "green"},
            {"name": "Social",     "color": "pink"},
        ]}},
        "User":          {"rich_text": {}},
        "Votes":         {"number": {"format": "number"}},
        "Date":          {"date": {}},
        "Details":       {"rich_text": {}},
    })

    db_registry["support_tickets"] = create_database(section, "Support Tickets", "🎫", {
        "Subject":       {"title": {}},
        "Status":        {"select": {"options": [
            {"name": "Open",         "color": "red"},
            {"name": "In Progress",  "color": "yellow"},
            {"name": "Waiting User", "color": "blue"},
            {"name": "Resolved",     "color": "green"},
            {"name": "Closed",       "color": "gray"},
        ]}},
        "Priority":      {"select": {"options": [
            {"name": "Urgent",   "color": "red"},
            {"name": "High",     "color": "orange"},
            {"name": "Normal",   "color": "yellow"},
            {"name": "Low",      "color": "green"},
        ]}},
        "Category":      {"select": {"options": [
            {"name": "Setup",       "color": "blue"},
            {"name": "Bug",         "color": "red"},
            {"name": "Billing",     "color": "green"},
            {"name": "Feature Q",   "color": "yellow"},
            {"name": "Account",     "color": "purple"},
        ]}},
        "User":          {"rich_text": {}},
        "Channel":       {"select": {"options": [
            {"name": "Discord",  "color": "purple"},
            {"name": "Email",    "color": "blue"},
        ]}},
        "Created":       {"date": {}},
        "Resolved Date": {"date": {}},
        "Resolution":    {"rich_text": {}},
    })

    db_registry["community_events"] = create_database(section, "Community Events", "🎉", {
        "Event Name":    {"title": {}},
        "Type":          {"select": {"options": [
            {"name": "AMA",             "color": "blue"},
            {"name": "Trading Session", "color": "green"},
            {"name": "Challenge Watch", "color": "yellow"},
            {"name": "Tutorial",        "color": "purple"},
            {"name": "Launch Party",    "color": "red"},
        ]}},
        "Date":          {"date": {}},
        "Status":        {"select": {"options": [
            {"name": "Planned",   "color": "gray"},
            {"name": "Announced", "color": "blue"},
            {"name": "Live",      "color": "green"},
            {"name": "Complete",  "color": "purple"},
        ]}},
        "Attendees":     {"number": {"format": "number"}},
        "Platform":      {"select": {"options": [
            {"name": "Discord Voice", "color": "purple"},
            {"name": "Discord Text",  "color": "blue"},
            {"name": "YouTube Live",  "color": "red"},
        ]}},
        "Notes":         {"rich_text": {}},
    })

    # ═══════════════════════════════════════════
    # 8. ANALYTICS — Analytics Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Analytics", "📊")

    db_registry["kpi_snapshots"] = create_database(section, "KPI Snapshots", "📈", {
        "Week":          {"title": {}},
        "Date":          {"date": {}},
        "MRR":           {"number": {"format": "dollar"}},
        "Total Users":   {"number": {"format": "number"}},
        "Paid Users":    {"number": {"format": "number"}},
        "Conversion Rate":{"number": {"format": "percent"}},
        "Churn Rate":    {"number": {"format": "percent"}},
        "CAC":           {"number": {"format": "dollar"}},
        "LTV":           {"number": {"format": "dollar"}},
        "Discord Members":{"number": {"format": "number"}},
        "Website Visitors":{"number": {"format": "number"}},
        "IB Revenue":    {"number": {"format": "dollar"}},
    })

    db_registry["funnel_metrics"] = create_database(section, "Funnel Metrics", "🔄", {
        "Period":        {"title": {}},
        "Date":          {"date": {}},
        "Visitors":      {"number": {"format": "number"}},
        "Signups":       {"number": {"format": "number"}},
        "Activations":   {"number": {"format": "number"}},
        "Trial Starts":  {"number": {"format": "number"}},
        "Conversions":   {"number": {"format": "number"}},
        "Visitor→Signup":{"number": {"format": "percent"}},
        "Signup→Active": {"number": {"format": "percent"}},
        "Active→Paid":   {"number": {"format": "percent"}},
    })

    # ═══════════════════════════════════════════
    # 9. PARTNERSHIPS — Business Strategist Agent
    # ═══════════════════════════════════════════
    section = create_section_page("Partnerships", "🤝")

    db_registry["partnerships"] = create_database(section, "Broker IB Pipeline", "🏢", {
        "Broker":        {"title": {}},
        "Status":        {"select": {"options": [
            {"name": "Researching", "color": "gray"},
            {"name": "Contacted",   "color": "blue"},
            {"name": "Negotiating", "color": "yellow"},
            {"name": "Active",      "color": "green"},
            {"name": "Rejected",    "color": "red"},
        ]}},
        "Commission $/Lot":{"number": {"format": "dollar"}},
        "Platforms":     {"multi_select": {"options": [
            {"name": "MT4",     "color": "blue"},
            {"name": "MT5",     "color": "green"},
            {"name": "cTrader", "color": "yellow"},
        ]}},
        "Score":         {"number": {"format": "number"}},
        "Recommendation":{"select": {"options": [
            {"name": "Strong Pursue",  "color": "green"},
            {"name": "Pursue",         "color": "blue"},
            {"name": "Consider",       "color": "yellow"},
            {"name": "Pass",           "color": "red"},
        ]}},
        "Revenue/100 Users":{"number": {"format": "dollar"}},
        "Contact":       {"rich_text": {}},
        "Agreement URL": {"url": {}},
        "Notes":         {"rich_text": {}},
    })

    # ═══════════════════════════════════════════
    # 10. ORCHESTRATOR — Task Log
    # ═══════════════════════════════════════════
    section = create_section_page("Orchestrator", "🧠")

    db_registry["task_log"] = create_database(section, "Task Log", "📋", {
        "Task":          {"title": {}},
        "Agent":         {"select": {"options": [
            {"name": "Orchestrator",         "color": "gray"},
            {"name": "Business Strategist",  "color": "purple"},
            {"name": "Finance",              "color": "green"},
            {"name": "Sales",                "color": "orange"},
            {"name": "Marketing",            "color": "pink"},
            {"name": "Content Engine",       "color": "yellow"},
            {"name": "Product",              "color": "blue"},
            {"name": "Community Manager",    "color": "red"},
            {"name": "Analytics",            "color": "default"},
        ]}},
        "Status":        {"select": {"options": [
            {"name": "Queued",      "color": "gray"},
            {"name": "In Progress", "color": "blue"},
            {"name": "Complete",    "color": "green"},
            {"name": "Failed",      "color": "red"},
            {"name": "Blocked",     "color": "orange"},
        ]}},
        "Priority":      {"select": {"options": [
            {"name": "P0", "color": "red"},
            {"name": "P1", "color": "orange"},
            {"name": "P2", "color": "yellow"},
            {"name": "P3", "color": "green"},
        ]}},
        "Created":       {"date": {}},
        "Completed":     {"date": {}},
        "Duration Min":  {"number": {"format": "number"}},
        "Input Summary":  {"rich_text": {}},
        "Output Summary": {"rich_text": {}},
        "Error":          {"rich_text": {}},
    })

    return db_registry


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  HEDGE EDGE ERP — Notion Database Setup")
    print("=" * 60)
    print()

    registry = build_all_databases()

    print()
    print("=" * 60)
    print("  ALL DATABASES CREATED — Database ID Registry")
    print("=" * 60)
    print()

    # Output as Python dict for copy-paste into shared/notion_client.py
    print("DATABASES = {")
    for key, db_id in registry.items():
        print(f'    "{key}": "{db_id}",')
    print("}")

    # Also save to JSON
    output_path = os.path.join(os.path.dirname(__file__), "notion_db_registry.json")
    with open(output_path, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"\nRegistry saved to: {output_path}")
    print(f"\nTotal databases created: {len(registry)}")
