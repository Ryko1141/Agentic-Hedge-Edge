#!/usr/bin/env python3
"""
qa_automator.py — Product Agent QA Automation & Quality Metrics

Manage QA test suites, track test runs, and monitor quality metrics
for the Hedge Edge prop-firm hedging tool.

Usage:
    python qa_automator.py --action add-test-case --name "Hedge engine opens opposite position" --category e2e --component hedge-engine --priority P1
    python qa_automator.py --action run-suite --suite smoke --passed 42 --failed 3 --skipped 1 --duration-mins 8.5
    python qa_automator.py --action quality-dashboard
    python qa_automator.py --action regression-check
    python qa_automator.py --action test-coverage
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Product"

CATEGORIES = ["unit", "integration", "e2e", "regression", "performance", "security"]
COMPONENTS = ["ea-core", "hedge-engine", "broker-connection", "ui-electron", "api-backend", "auth"]
SUITES = ["smoke", "regression", "full"]

COMPONENT_LABELS = {
    "ea-core":          "EA Core (MT5)",
    "hedge-engine":     "Hedge Engine",
    "broker-connection": "Broker Connection",
    "ui-electron":      "Electron UI",
    "api-backend":      "API Backend",
    "auth":             "Auth & Licensing",
}

# Quality thresholds
PASS_RATE_TARGET = 95.0      # %
COVERAGE_TARGET = 80.0       # % of components with tests
MTTR_THRESHOLD_DAYS = 3      # Mean time to resolve (days)


def _get_test_cases():
    """Fetch all test case rows from bug_tracker (Type=TestCase)."""
    rows = query_db("bug_tracker")
    return [r for r in rows if (r.get("Area") or "").lower() == "testcase"
            or (r.get("Status") or "").lower() == "testcase"
            or "test" in (r.get("Bug") or "").lower()[:10]]


def _get_test_case_rows():
    """More reliable: fetch test cases by convention — Bug title starts with [TC]."""
    rows = query_db("bug_tracker")
    return [r for r in rows if (r.get("Bug") or "").startswith("[TC]")]


def _get_suite_runs():
    """Fetch test suite run entries from kpi_snapshots."""
    rows = query_db("kpi_snapshots")
    return [r for r in rows if (r.get("Name") or "").startswith("[QA]")]


def _get_open_bugs():
    """Fetch open bugs (non-test-case) from bug_tracker."""
    rows = query_db("bug_tracker")
    return [r for r in rows
            if not (r.get("Bug") or "").startswith("[TC]")
            and (r.get("Status") or "Open") not in ("Resolved", "Closed")]


def add_test_case(args):
    """Add a QA test case to bug_tracker with [TC] prefix."""
    tc_name = f"[TC] {args.name}"
    row = {
        "Bug":         tc_name,
        "Severity":    args.priority or "P2",
        "Status":      "Active",
        "Area":        args.component or "ea-core",
        "Reported By": "QA Automation",
        "Steps":       f"Category: {args.category or 'unit'} | Auto-tracked by qa_automator.py",
        "Reported":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    add_row("bug_tracker", row)

    print("=" * 60)
    print("  🧪 TEST CASE REGISTERED")
    print("=" * 60)
    print(f"  Name:      {args.name}")
    print(f"  Category:  {args.category or 'unit'}")
    print(f"  Component: {COMPONENT_LABELS.get(args.component, args.component or 'ea-core')}")
    print(f"  Priority:  {args.priority or 'P2'}")
    print("─" * 60)

    log_task(AGENT, f"Test case added: {args.name}",
             "Complete", args.priority or "P2",
             f"category={args.category}, component={args.component}")


def run_suite(args):
    """Log a test suite execution run to kpi_snapshots."""
    total = args.passed + args.failed + args.skipped
    pass_rate = (args.passed / total * 100) if total > 0 else 0
    now = datetime.now(timezone.utc)

    row = {
        "Name":  f"[QA] {args.suite.title()} Suite — {now.strftime('%Y-%m-%d %H:%M')}",
        "Value": pass_rate,
        "Date":  now.strftime("%Y-%m-%d"),
    }
    add_row("kpi_snapshots", row)

    health = "PASS" if pass_rate >= PASS_RATE_TARGET else "WARN" if pass_rate >= 80 else "FAIL"
    health_icon = "✅" if health == "PASS" else "🟡" if health == "WARN" else "🔴"

    print("=" * 60)
    print(f"  🧪 TEST SUITE RUN — {args.suite.upper()}")
    print("=" * 60)
    print(f"\n  {'Metric':<20} {'Value':>10}")
    print(f"  {'─' * 35}")
    print(f"  {'Total Tests':<20} {total:>10}")
    print(f"  {'Passed':<20} {'✅ ' + str(args.passed):>10}")
    print(f"  {'Failed':<20} {'❌ ' + str(args.failed):>10}")
    print(f"  {'Skipped':<20} {'⏭️ ' + str(args.skipped):>10}")
    print(f"  {'Duration':<20} {args.duration_mins:>8.1f} min")
    print(f"  {'─' * 35}")
    print(f"  {'Pass Rate':<20} {pass_rate:>9.1f}%")
    print(f"  {'Target':<20} {PASS_RATE_TARGET:>9.1f}%")
    print(f"  {'Status':<20} {health_icon + ' ' + health:>10}")

    # Pass rate visual
    filled = int(pass_rate / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"\n  [{bar}] {pass_rate:.1f}%")

    if args.failed > 0:
        print(f"\n  ⚠️  {args.failed} test(s) failed — review failures before merge")
    print("─" * 60)

    log_task(AGENT, f"QA suite run: {args.suite}",
             "Complete", "P1",
             f"passed={args.passed}, failed={args.failed}, rate={pass_rate:.1f}%")


def quality_dashboard(args):
    """Show quality metrics: test cases, pass rate, bugs, MTTR."""
    test_cases = _get_test_case_rows()
    suite_runs = _get_suite_runs()
    open_bugs = _get_open_bugs()
    all_bugs = [r for r in query_db("bug_tracker") if not (r.get("Bug") or "").startswith("[TC]")]

    print("=" * 60)
    print("  📊 QUALITY DASHBOARD")
    print("=" * 60)

    # Test case summary
    tc_by_component = defaultdict(int)
    tc_by_category = defaultdict(int)
    for tc in test_cases:
        comp = tc.get("Area") or "unknown"
        tc_by_component[comp] += 1
        steps = tc.get("Steps") or ""
        cat = "unit"
        for c in CATEGORIES:
            if c in steps.lower():
                cat = c
                break
        tc_by_category[cat] += 1

    total_tc = len(test_cases)
    print(f"\n  TEST CASES: {total_tc}")
    print(f"  {'─' * 50}")
    if total_tc > 0:
        for comp in COMPONENTS:
            count = tc_by_component.get(comp, 0)
            label = COMPONENT_LABELS.get(comp, comp)
            bar = "█" * (count * 2) if count > 0 else ""
            print(f"    {label:<22} {count:>3}  {bar}")
    else:
        print("    No test cases tracked yet. Use --action add-test-case")

    # Latest suite run
    print(f"\n  LATEST SUITE RUNS:")
    print(f"  {'─' * 50}")
    if suite_runs:
        recent = sorted(suite_runs, key=lambda r: r.get("Date") or "", reverse=True)[:5]
        for run in recent:
            name = (run.get("Name") or "?").replace("[QA] ", "")
            rate = run.get("Value") or 0
            icon = "✅" if rate >= PASS_RATE_TARGET else "🟡" if rate >= 80 else "🔴"
            print(f"    {icon} {name:<35} {rate:>6.1f}%")
    else:
        print("    No suite runs logged yet. Use --action run-suite")

    # Bug metrics
    resolved_bugs = [b for b in all_bugs if b.get("Status") in ("Resolved", "Closed")]
    severity_counts = defaultdict(int)
    for bug in open_bugs:
        sev = bug.get("Severity") or "P3"
        severity_counts[sev] += 1

    print(f"\n  BUG METRICS:")
    print(f"  {'─' * 50}")
    print(f"    Open bugs:     {len(open_bugs)}")
    print(f"    Resolved:      {len(resolved_bugs)}")
    for sev in ["P0", "P1", "P2", "P3", "P4"]:
        count = severity_counts.get(sev, 0)
        if count > 0:
            icon = "🔴" if sev in ("P0", "P1") else "🟡" if sev == "P2" else "🟢"
            print(f"      {icon} {sev}: {count} open")

    # Mean time to resolve (MTTR)
    mttr_days = []
    for bug in resolved_bugs:
        reported = bug.get("Reported")
        resolved = bug.get("Resolved")
        if reported and resolved:
            try:
                d1 = datetime.strptime(reported[:10], "%Y-%m-%d")
                d2 = datetime.strptime(resolved[:10], "%Y-%m-%d")
                mttr_days.append((d2 - d1).days)
            except ValueError:
                pass

    avg_mttr = sum(mttr_days) / len(mttr_days) if mttr_days else 0
    mttr_icon = "✅" if avg_mttr <= MTTR_THRESHOLD_DAYS else "🟡" if avg_mttr <= 7 else "🔴"
    print(f"    MTTR:          {mttr_icon} {avg_mttr:.1f} days (target: ≤{MTTR_THRESHOLD_DAYS}d)")
    print("─" * 60)

    log_task(AGENT, "Quality dashboard review", "Complete", "P2",
             f"test_cases={total_tc}, open_bugs={len(open_bugs)}, mttr={avg_mttr:.1f}d")


def regression_check(args):
    """Compare latest test run against previous to flag regressions."""
    suite_runs = _get_suite_runs()

    print("=" * 60)
    print("  🔍 REGRESSION CHECK")
    print("=" * 60)

    if len(suite_runs) < 2:
        print("\n  Need at least 2 suite runs to compare.")
        print("  Log runs with --action run-suite first.")
        print("─" * 60)
        log_task(AGENT, "Regression check", "Complete", "P3", "Insufficient data")
        return

    sorted_runs = sorted(suite_runs, key=lambda r: r.get("Date") or "", reverse=True)
    latest = sorted_runs[0]
    previous = sorted_runs[1]

    latest_rate = latest.get("Value") or 0
    prev_rate = previous.get("Value") or 0
    delta = latest_rate - prev_rate

    regression = delta < -2.0  # >2% drop = regression

    print(f"\n  {'Run':<12} {'Date':<14} {'Pass Rate':>10}")
    print(f"  {'─' * 40}")
    print(f"  {'Latest':<12} {(latest.get('Date') or '?'):<14} {latest_rate:>9.1f}%")
    print(f"  {'Previous':<12} {(previous.get('Date') or '?'):<14} {prev_rate:>9.1f}%")
    print(f"  {'─' * 40}")
    print(f"  {'Delta':<12} {'':14} {delta:>+9.1f}%")

    if regression:
        print(f"\n  🔴 REGRESSION DETECTED — pass rate dropped {abs(delta):.1f}%")
        print(f"  Action: Review failed tests before deploying")
    elif delta < 0:
        print(f"\n  🟡 Minor decrease ({abs(delta):.1f}%) — monitor closely")
    elif delta == 0:
        print(f"\n  ─  No change in pass rate")
    else:
        print(f"\n  ✅ Improvement: +{delta:.1f}% pass rate increase")

    # Trend over last 5 runs
    if len(sorted_runs) >= 3:
        print(f"\n  TREND (last {min(5, len(sorted_runs))} runs):")
        print(f"  {'─' * 40}")
        for run in sorted_runs[:5]:
            rate = run.get("Value") or 0
            filled = int(rate / 5)
            bar = "█" * filled + "░" * (20 - filled)
            date_str = (run.get("Date") or "?")[:10]
            print(f"    {date_str}  [{bar}] {rate:.1f}%")

    print("─" * 60)

    status = "regression" if regression else "stable"
    log_task(AGENT, "Regression check", "Complete",
             "P1" if regression else "P3",
             f"latest={latest_rate:.1f}%, prev={prev_rate:.1f}%, delta={delta:+.1f}%, status={status}")


def test_coverage(args):
    """Show test coverage by component and identify gaps."""
    test_cases = _get_test_case_rows()

    # Count test cases per component
    coverage = defaultdict(lambda: defaultdict(int))
    for tc in test_cases:
        comp = tc.get("Area") or "unknown"
        steps = tc.get("Steps") or ""
        cat = "unit"
        for c in CATEGORIES:
            if c in steps.lower():
                cat = c
                break
        coverage[comp][cat] += 1

    print("=" * 60)
    print("  📋 TEST COVERAGE BY COMPONENT")
    print("=" * 60)

    # Header
    cat_short = {"unit": "Unit", "integration": "Intg", "e2e": "E2E",
                 "regression": "Regr", "performance": "Perf", "security": "Sec"}
    header = f"  {'Component':<22}"
    for cat in CATEGORIES:
        header += f" {cat_short[cat]:>5}"
    header += " Total"
    print(f"\n{header}")
    print(f"  {'─' * 58}")

    total_tests = 0
    components_with_tests = 0
    gaps = []

    for comp in COMPONENTS:
        label = COMPONENT_LABELS.get(comp, comp)
        comp_total = 0
        row_str = f"  {label:<22}"
        for cat in CATEGORIES:
            count = coverage.get(comp, {}).get(cat, 0)
            comp_total += count
            if count > 0:
                row_str += f" {count:>5}"
            else:
                row_str += f" {'─':>5}"
        row_str += f" {comp_total:>5}"
        print(row_str)

        total_tests += comp_total
        if comp_total > 0:
            components_with_tests += 1
        else:
            gaps.append(label)

    comp_coverage_pct = (components_with_tests / len(COMPONENTS) * 100) if COMPONENTS else 0

    print(f"  {'─' * 58}")
    print(f"  {'TOTAL':<22} {'':>35} {total_tests:>5}")

    # Coverage score
    print(f"\n  COVERAGE SCORE")
    print(f"  {'─' * 40}")
    cov_icon = "✅" if comp_coverage_pct >= COVERAGE_TARGET else "🟡" if comp_coverage_pct >= 50 else "🔴"
    print(f"  {cov_icon} Component coverage: {components_with_tests}/{len(COMPONENTS)} "
          f"({comp_coverage_pct:.0f}%) — target {COVERAGE_TARGET:.0f}%")

    filled = int(comp_coverage_pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"  [{bar}] {comp_coverage_pct:.0f}%")

    if gaps:
        print(f"\n  ⚠️  COVERAGE GAPS ({len(gaps)} components):")
        for gap in gaps:
            print(f"    ❌ {gap} — no test cases registered")

    # Recommendations
    print(f"\n  RECOMMENDATIONS:")
    print(f"  {'─' * 40}")
    if total_tests == 0:
        print("    1. Start with smoke tests for ea-core and hedge-engine")
        print("    2. Add integration tests for broker-connection")
        print("    3. Add e2e tests for critical user flows in ui-electron")
    elif gaps:
        print(f"    1. Add test cases for: {', '.join(gaps)}")
        if "Security" in [cat_short[c] for c in CATEGORIES if coverage.get("auth", {}).get(c, 0) == 0]:
            print("    2. Add security tests for auth & licensing")
    else:
        print("    ✅ All components have test cases — focus on depth")
    print("─" * 60)

    log_task(AGENT, "Test coverage analysis", "Complete", "P2",
             f"total_tests={total_tests}, coverage={comp_coverage_pct:.0f}%, gaps={len(gaps)}")


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Agent — QA Automation & Quality Metrics")
    parser.add_argument("--action", required=True,
                        choices=["add-test-case", "run-suite", "quality-dashboard",
                                 "regression-check", "test-coverage"])
    parser.add_argument("--name", help="Test case name")
    parser.add_argument("--category", choices=CATEGORIES, help="Test category")
    parser.add_argument("--component", choices=COMPONENTS, help="Product component")
    parser.add_argument("--priority", choices=["P1", "P2", "P3", "P4"])
    parser.add_argument("--suite", choices=SUITES, help="Test suite to run")
    parser.add_argument("--passed", type=int, default=0, help="Number of passed tests")
    parser.add_argument("--failed", type=int, default=0, help="Number of failed tests")
    parser.add_argument("--skipped", type=int, default=0, help="Number of skipped tests")
    parser.add_argument("--duration-mins", type=float, default=0, help="Suite duration in minutes")
    args = parser.parse_args()

    dispatch = {
        "add-test-case":      add_test_case,
        "run-suite":          run_suite,
        "quality-dashboard":  quality_dashboard,
        "regression-check":   regression_check,
        "test-coverage":      test_coverage,
    }
    dispatch[args.action](args)
