#!/usr/bin/env python3
"""
task_decomposer.py — Orchestrator Task Decomposition Engine

Breaks complex multi-domain user requests into atomic sub-tasks arranged
in a dependency DAG (Directed Acyclic Graph).  Each layer of the DAG can
execute in parallel; layers are sequential.  Plans are logged to Notion
task_log for auditability.

Usage:
    python task_decomposer.py --action decompose --request "Launch our new Challenge Shield plan with video, email sequence, and landing page"
    python task_decomposer.py --action show-plan --plan-id PLAN-20260218-143022
    python task_decomposer.py --action validate-plan --plan-id PLAN-20260218-143022
"""

import sys, os, argparse, json, hashlib
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

# ── Agent Domain Keywords (mirrors agent_router.py) ──────────────────

AGENT_KEYWORDS = {
    "Business Strategist": ["strategy", "growth", "pricing", "competition", "partnerships", "moats", "okr", "initiative", "swot"],
    "Content Engine":      ["video", "content", "social", "youtube", "instagram", "linkedin", "post", "script", "thumbnail", "shorts", "reel"],
    "Marketing":           ["email", "seo", "ads", "landing page", "newsletter", "lead magnet", "keywords", "funnel", "campaign", "sequence", "nurture"],
    "Sales":               ["lead", "demo", "call", "crm", "pipeline", "proposal", "close", "qualify", "follow-up", "prospect"],
    "Finance":             ["revenue", "mrr", "expense", "commission", "invoice", "tax", "p&l", "cash flow", "runway", "budget"],
    "Community":           ["discord", "community", "onboard", "support", "ticket", "feedback", "sentiment", "event"],
    "Analytics":           ["metrics", "dashboard", "funnel", "cohort", "churn", "attribution", "a/b test", "kpi", "report"],
    "Product":             ["feature", "bug", "release", "roadmap", "spec", "qa", "integration", "mt4", "ctrader", "deploy"],
}

# ── Task Templates by Agent ──────────────────────────────────────────
# Common atomic tasks each agent can perform

TASK_TEMPLATES = {
    "Business Strategist": [
        "Review strategic alignment with OKRs",
        "Competitive positioning analysis",
        "Validate pricing strategy for initiative",
    ],
    "Content Engine": [
        "Script and produce announcement video",
        "Create social media post set (LinkedIn, Instagram, X)",
        "Design thumbnails and visual assets",
        "Update content calendar with new entries",
    ],
    "Marketing": [
        "Build email nurture sequence",
        "Create/update landing page",
        "Set up campaign tracking and UTMs",
        "Define audience segments and targeting",
        "SEO keyword research for initiative",
    ],
    "Sales": [
        "Update CRM pipeline stages",
        "Prepare outreach scripts and talk tracks",
        "Schedule demo slots for campaign leads",
        "Create proposal template",
    ],
    "Finance": [
        "Forecast revenue impact",
        "Set up expense tracking for initiative",
        "Calculate expected IB commissions",
    ],
    "Community": [
        "Draft Discord announcement",
        "Update onboarding materials",
        "Prepare FAQ and support responses",
    ],
    "Analytics": [
        "Set up KPI tracking dashboard",
        "Configure funnel metrics and attribution",
        "Plan A/B test framework",
    ],
    "Product": [
        "Verify feature readiness and QA sign-off",
        "Update release log",
        "Document integration requirements",
    ],
}


def _generate_plan_id():
    return f"PLAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _detect_agents(request_text):
    """Detect which agents are needed based on keyword matching."""
    text_lower = request_text.lower()
    needed = {}
    for agent, keywords in AGENT_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            needed[agent] = matched
    # Always include Analytics for tracking if 2+ agents involved
    if len(needed) >= 2 and "Analytics" not in needed:
        needed["Analytics"] = ["tracking"]
    return needed


def _build_dag(agents_needed, request_text):
    """Build a dependency DAG of sub-tasks grouped into execution layers.

    Layer 0: Independent setup tasks (can run in parallel)
    Layer 1: Tasks depending on Layer 0 outputs
    Layer 2: Integration / launch tasks
    Layer 3: Monitoring and follow-up
    """
    tasks = []
    task_id = 0

    # Layer 0: Discovery & setup (all agents prepare independently)
    layer0_ids = []
    for agent in agents_needed:
        templates = TASK_TEMPLATES.get(agent, [])
        if templates:
            task_id += 1
            tasks.append({
                "id": task_id,
                "layer": 0,
                "agent": agent,
                "task": templates[0],  # First template is usually the setup/research task
                "depends_on": [],
                "status": "Ready",
            })
            layer0_ids.append(task_id)

    # Layer 1: Core execution (depends on respective setup)
    layer1_ids = []
    for agent in agents_needed:
        templates = TASK_TEMPLATES.get(agent, [])
        parent_ids = [t["id"] for t in tasks if t["agent"] == agent and t["layer"] == 0]
        for tmpl in templates[1:3]:  # Up to 2 execution tasks per agent
            task_id += 1
            tasks.append({
                "id": task_id,
                "layer": 1,
                "agent": agent,
                "task": tmpl,
                "depends_on": parent_ids,
                "status": "Blocked",
            })
            layer1_ids.append(task_id)

    # Layer 2: Integration (depends on all Layer 1 tasks)
    if len(agents_needed) >= 2:
        task_id += 1
        tasks.append({
            "id": task_id,
            "layer": 2,
            "agent": "Orchestrator",
            "task": "Cross-agent integration check and launch approval",
            "depends_on": layer1_ids,
            "status": "Blocked",
        })
        integration_id = task_id

        # Layer 3: Monitoring
        task_id += 1
        tasks.append({
            "id": task_id,
            "layer": 3,
            "agent": "Analytics",
            "task": "Post-launch monitoring and KPI tracking",
            "depends_on": [integration_id],
            "status": "Blocked",
        })

    return tasks


# ── Actions ───────────────────────────────────────────────────────────

def decompose(args):
    """Decompose a complex request into a DAG of sub-tasks."""
    request = args.request
    if not request:
        print("❌ --request is required for decompose action"); return

    agents_needed = _detect_agents(request)
    plan_id = _generate_plan_id()
    dag = _build_dag(agents_needed, request)

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              🧩  TASK DECOMPOSITION PLAN                       ║")
    print(f"║  Plan ID: {plan_id:<54}║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Request: {request[:54]:<54} ║")
    print(f"║  Agents detected: {len(agents_needed):<45}║")
    for agent, kws in agents_needed.items():
        print(f"║    • {agent:<20} matched: {', '.join(kws[:4]):<29}║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    # Print DAG by layer
    max_layer = max(t["layer"] for t in dag) if dag else 0
    for layer in range(max_layer + 1):
        layer_tasks = [t for t in dag if t["layer"] == layer]
        parallel_label = " (parallel)" if len(layer_tasks) > 1 else ""
        print(f"║                                                                  ║")
        print(f"║  ── Layer {layer}{parallel_label:<53}║")
        for t in layer_tasks:
            deps = f" ← [{','.join(str(d) for d in t['depends_on'])}]" if t["depends_on"] else ""
            icon = "🟢" if t["status"] == "Ready" else "🔒"
            print(f"║  {icon} T{t['id']:>2}: [{t['agent']:<18}] {t['task'][:30]:<30}║")
            if deps:
                print(f"║       depends on: T{',T'.join(str(d) for d in t['depends_on']):<44}║")

    # Critical path analysis
    critical_path_len = max_layer + 1
    total_tasks = len(dag)
    parallel_tasks = max(sum(1 for t in dag if t["layer"] == l) for l in range(max_layer + 1)) if dag else 0

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  📊 PLAN SUMMARY                                               ║")
    print(f"║     Total sub-tasks:    {total_tasks:<40}║")
    print(f"║     Execution layers:   {critical_path_len:<40}║")
    print(f"║     Max parallelism:    {parallel_tasks} tasks in parallel{' ' * 25}║")
    print(f"║     Critical path:      {critical_path_len} sequential steps{' ' * 26}║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    # Log plan to Notion
    plan_data = {
        "plan_id": plan_id,
        "request": request[:200],
        "agents": list(agents_needed.keys()),
        "total_tasks": total_tasks,
        "layers": critical_path_len,
        "dag": dag,
    }
    add_row("task_log", {
        "Name":           f"[{plan_id}] Decomposition plan",
        "Agent":          "Orchestrator",
        "Status":         "In Progress",
        "Priority":       "P1",
        "Timestamp":      datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "Output Summary": json.dumps({"plan_id": plan_id, "agents": list(agents_needed.keys()),
                                       "tasks": total_tasks, "layers": critical_path_len}),
    })

    # Log each sub-task
    for t in dag:
        add_row("task_log", {
            "Name":           f"[{plan_id}] T{t['id']}: {t['task'][:50]}",
            "Agent":          t["agent"],
            "Status":         t["status"],
            "Priority":       "P2",
            "Timestamp":      datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "Output Summary": json.dumps({"plan_id": plan_id, "task_id": t["id"],
                                           "layer": t["layer"], "depends_on": t["depends_on"]}),
        })

    log_task("Orchestrator", f"Decomposed: {plan_id}", "Complete", "P1",
             f"{total_tasks} tasks, {critical_path_len} layers, {len(agents_needed)} agents")
    return plan_id


def show_plan(args):
    """Show a previously created execution plan."""
    plan_id = args.plan_id
    if not plan_id:
        print("❌ --plan-id is required"); return

    items = query_db("task_log")
    plan_tasks = [t for t in items if plan_id in (t.get("Name", "") or "")]
    plan_tasks.sort(key=lambda x: x.get("Name", ""))

    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  📋  EXECUTION PLAN: {plan_id:<43}║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if not plan_tasks:
        print(f"║  ⚠️  No tasks found for plan {plan_id:<34}║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        return

    # Separate header row from sub-tasks
    header = None
    sub_tasks = []
    for t in plan_tasks:
        name = t.get("Name", "") or ""
        if "Decomposition plan" in name:
            header = t
        else:
            sub_tasks.append(t)

    if header:
        summary = header.get("Output Summary", "") or "{}"
        try:
            meta = json.loads(summary)
        except json.JSONDecodeError:
            meta = {}
        agents_str = ", ".join(meta.get("agents", [])[:5])
        print(f"║  Agents: {agents_str:<55}║")
        print(f"║  Total tasks: {meta.get('tasks', '?'):<12} Layers: {meta.get('layers', '?'):<22}║")
        print("╠══════════════════════════════════════════════════════════════════╣")

    # Group by layer
    layered = {}
    for t in sub_tasks:
        summary = t.get("Output Summary", "") or "{}"
        try:
            meta = json.loads(summary)
        except json.JSONDecodeError:
            meta = {}
        layer = meta.get("layer", 99)
        layered.setdefault(layer, []).append((t, meta))

    for layer_num in sorted(layered.keys()):
        layer_items = layered[layer_num]
        print(f"║                                                                  ║")
        print(f"║  ── Layer {layer_num} ({len(layer_items)} tasks){'─' * 43}    ║")
        for t, meta in layer_items:
            status = t.get("Status", "?")
            agent = t.get("Agent", "?")
            name = (t.get("Name", "") or "").replace(f"[{plan_id}] ", "")
            icon = "✅" if status == "Complete" else "🔵" if status in ("Ready", "Dispatched", "In Progress") else "🔒"
            deps = meta.get("depends_on", [])
            print(f"║  {icon} [{agent:<16}] {name[:36]:<36}║")
            if deps:
                print(f"║     └─ after: T{', T'.join(str(d) for d in deps):<48}║")

    # Progress
    completed = sum(1 for t in sub_tasks if t.get("Status") == "Complete")
    total = len(sub_tasks)
    pct = (completed / total * 100) if total else 0
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Progress: {bar} {pct:>5.1f}%                      ║")
    print(f"║  {completed}/{total} tasks complete                                          ║")
    print("╚══════════════════════════════════════════════════════════════════╝")


def validate_plan(args):
    """Validate a plan's DAG: check for cycles, missing inputs, agent access."""
    plan_id = args.plan_id
    if not plan_id:
        print("❌ --plan-id is required"); return

    items = query_db("task_log")
    plan_tasks = [t for t in items if plan_id in (t.get("Name", "") or "")
                  and "Decomposition plan" not in (t.get("Name", "") or "")]

    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  🔍  PLAN VALIDATION: {plan_id:<42}║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if not plan_tasks:
        print(f"║  ⚠️  No tasks found for plan {plan_id:<34}║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        return

    errors = []
    warnings = []

    # Parse task metadata
    parsed = []
    all_ids = set()
    for t in plan_tasks:
        summary = t.get("Output Summary", "") or "{}"
        try:
            meta = json.loads(summary)
        except json.JSONDecodeError:
            meta = {}
        tid = meta.get("task_id", 0)
        all_ids.add(tid)
        parsed.append({"id": tid, "layer": meta.get("layer", 0),
                        "depends_on": meta.get("depends_on", []),
                        "agent": t.get("Agent", "")})

    # Check 1: Cycle detection (topological sort)
    print("║  Check 1: Cycle detection (DAG integrity)                      ║")
    adj = {p["id"]: p["depends_on"] for p in parsed}
    visited, in_stack = set(), set()
    has_cycle = False

    def _dfs(node):
        nonlocal has_cycle
        if node in in_stack:
            has_cycle = True; return
        if node in visited:
            return
        visited.add(node); in_stack.add(node)
        for dep in adj.get(node, []):
            _dfs(dep)
        in_stack.discard(node)

    for node in all_ids:
        _dfs(node)

    if has_cycle:
        errors.append("Circular dependency detected — DAG has a cycle")
        print("║    ❌ FAIL — Circular dependency detected                       ║")
    else:
        print("║    ✅ PASS — No cycles, DAG is valid                            ║")

    # Check 2: Dangling dependencies
    print("║  Check 2: Dependency references                                ║")
    dangling = []
    for p in parsed:
        for dep in p["depends_on"]:
            if dep not in all_ids:
                dangling.append((p["id"], dep))
    if dangling:
        for tid, dep in dangling:
            errors.append(f"T{tid} depends on T{dep} which does not exist")
        print(f"║    ❌ FAIL — {len(dangling)} broken dependency reference(s)               ║")
    else:
        print("║    ✅ PASS — All dependencies resolve                           ║")

    # Check 3: Layer ordering consistency
    print("║  Check 3: Layer ordering consistency                           ║")
    layer_issues = 0
    id_to_layer = {p["id"]: p["layer"] for p in parsed}
    for p in parsed:
        for dep in p["depends_on"]:
            dep_layer = id_to_layer.get(dep, -1)
            if dep_layer >= p["layer"]:
                layer_issues += 1
                warnings.append(f"T{p['id']} (layer {p['layer']}) depends on T{dep} (layer {dep_layer})")
    if layer_issues:
        print(f"║    ⚠️  WARN — {layer_issues} cross-layer ordering issue(s)                ║")
    else:
        print("║    ✅ PASS — Layer ordering is consistent                       ║")

    # Check 4: Agent availability
    print("║  Check 4: Agent availability                                   ║")
    known_agents = set(AGENT_KEYWORDS.keys()) | {"Orchestrator"}
    unknown = set()
    for p in parsed:
        if p["agent"] not in known_agents:
            unknown.add(p["agent"])
    if unknown:
        for a in unknown:
            errors.append(f"Unknown agent: {a}")
        print(f"║    ❌ FAIL — Unknown agent(s): {', '.join(unknown):<31}  ║")
    else:
        print(f"║    ✅ PASS — All {len(set(p['agent'] for p in parsed))} agents are registered                    ║")

    # Check 5: Plan completeness (at least 1 task per detected agent)
    print("║  Check 5: Plan completeness                                    ║")
    agents_in_plan = set(p["agent"] for p in parsed)
    if len(agents_in_plan) < 2:
        warnings.append("Plan involves fewer than 2 agents — may be over-simplified")
        print("║    ⚠️  WARN — Only 1 agent involved, may need expansion         ║")
    else:
        print(f"║    ✅ PASS — {len(agents_in_plan)} agents with tasks assigned                  ║")

    # Summary
    print("╠══════════════════════════════════════════════════════════════════╣")
    if not errors and not warnings:
        print("║  🎉 PLAN IS VALID — Ready for execution                        ║")
    elif not errors:
        print(f"║  ⚠️  PLAN VALID WITH {len(warnings)} WARNING(S)                              ║")
        for w in warnings:
            print(f"║    ⚠️  {w[:57]:<57}║")
    else:
        print(f"║  ❌ PLAN HAS {len(errors)} ERROR(S) — Fix before executing                ║")
        for e in errors:
            print(f"║    ❌ {e[:58]:<58}║")
        if warnings:
            for w in warnings:
                print(f"║    ⚠️  {w[:57]:<57}║")

    print("╚══════════════════════════════════════════════════════════════════╝")

    status = "Valid" if not errors else "Invalid"
    log_task("Orchestrator", f"Validate plan: {plan_id}", "Complete", "P2",
             f"{status}: {len(errors)} errors, {len(warnings)} warnings, {len(parsed)} tasks")
    return len(errors) == 0


# ── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator Task Decomposition Engine")
    parser.add_argument("--action", required=True,
                        choices=["decompose", "show-plan", "validate-plan"])
    parser.add_argument("--request", help="Complex request text to decompose")
    parser.add_argument("--plan-id", help="Plan ID for show-plan or validate-plan")
    args = parser.parse_args()
    {"decompose": decompose, "show-plan": show_plan,
     "validate-plan": validate_plan}[args.action](args)
