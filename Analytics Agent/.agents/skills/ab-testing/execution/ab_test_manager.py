#!/usr/bin/env python3
"""
ab_test_manager.py — Analytics Agent A/B Test Management

Design, monitor, and analyze A/B tests with statistical rigor
for Hedge Edge prop-firm hedging software.

Usage:
    python ab_test_manager.py --action design --name "CTA Button Color" --hypothesis "Red CTA increases signup rate" --metric signup_rate --baseline-rate 0.03 --mde 0.005 --daily-traffic 500
    python ab_test_manager.py --action monitor --test-name "CTA Button Color"
    python ab_test_manager.py --action analyze --test-name "CTA Button Color"
    python ab_test_manager.py --action active-tests
    python ab_test_manager.py --action test-history
"""

import sys, os, argparse, json, math
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Analytics"

VALID_METRICS = ["signup_rate", "ctr", "checkout_rate", "bounce_rate"]

# z-values for common significance levels
Z_ALPHA = 1.96   # 95% confidence (two-tailed)
Z_BETA = 0.84    # 80% power


def _required_sample_size(baseline: float, mde: float) -> int:
    """Calculate per-variant sample size using z-test formula.

    n = (Z_α/2 + Z_β)² × [p1(1-p1) + p2(1-p2)] / (p2 - p1)²
    """
    p1 = baseline
    p2 = baseline + mde
    numerator = (Z_ALPHA + Z_BETA) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))
    denominator = (p2 - p1) ** 2
    if denominator == 0:
        return 999999
    return math.ceil(numerator / denominator)


def _z_score(p1: float, p2: float, n1: int, n2: int) -> float:
    """Two-proportion z-test statistic."""
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2) if (n1 + n2) > 0 else 0
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / max(n1, 1) + 1 / max(n2, 1)))
    return (p2 - p1) / se if se > 0 else 0


def _p_value(z: float) -> float:
    """Approximate two-tailed p-value from z-score using error-function approx."""
    return math.erfc(abs(z) / math.sqrt(2))


def _confidence_interval(p: float, n: int, z: float = 1.96) -> tuple:
    """Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    se = math.sqrt(p * (1 - p) / n)
    return (max(0, p - z * se), min(1, p + z * se))


def design(args):
    """Design a new A/B test with calculated sample size and duration."""
    n_per_variant = _required_sample_size(args.baseline_rate, args.mde)
    total_needed = n_per_variant * 2
    days_needed = math.ceil(total_needed / max(args.daily_traffic, 1))

    print("=" * 65)
    print("  🧪 A/B TEST DESIGN")
    print("=" * 65)
    print(f"\n  Test Name:   {args.name}")
    print(f"  Hypothesis:  {args.hypothesis}")
    print(f"  Metric:      {args.metric}")
    print(f"\n  Baseline Rate:          {args.baseline_rate:.2%}")
    print(f"  Min Detectable Effect:  {args.mde:.2%}")
    print(f"  Expected Variant Rate:  {args.baseline_rate + args.mde:.2%}")
    print(f"\n  Significance Level:     95% (α = 0.05)")
    print(f"  Statistical Power:      80% (β = 0.20)")
    print(f"\n{'─' * 65}")
    print(f"  Required Sample Size:   {n_per_variant:,} per variant")
    print(f"  Total Participants:     {total_needed:,}")
    print(f"  Daily Traffic:          {args.daily_traffic:,} visitors")
    print(f"  Estimated Duration:     {days_needed} days")
    est_end = datetime.now(timezone.utc) + timedelta(days=days_needed)
    print(f"  Estimated End Date:     {est_end.strftime('%Y-%m-%d')}")
    print("─" * 65)

    add_row("kpi_snapshots", {
        "Name": f"AB Test: {args.name}",
        "Metric": args.metric,
        "Value": args.baseline_rate,
        "Target": args.baseline_rate + args.mde,
        "Notes": json.dumps({
            "hypothesis": args.hypothesis,
            "sample_per_variant": n_per_variant,
            "daily_traffic": args.daily_traffic,
            "days_needed": days_needed,
            "status": "running",
        }),
        "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })

    log_task(AGENT, f"Designed A/B test: {args.name}",
             "Complete", "P2",
             f"n={n_per_variant}/variant, {days_needed}d, metric={args.metric}")


def monitor(args):
    """Monitor a running A/B test for SRM and peek warnings."""
    tests = query_db("landing_page_tests")
    matching = [t for t in tests if args.test_name.lower() in (t.get("Name", "") or "").lower()]

    print("=" * 65)
    print(f"  📊 MONITORING: {args.test_name}")
    print("=" * 65)

    if not matching:
        print(f"\n  ⚠️  No test data found for '{args.test_name}'")
        print("  Ensure landing_page_tests has entries for this experiment.")
        print("─" * 65)
        return

    control_rows = [r for r in matching if "control" in (r.get("Variant", "") or "").lower()]
    variant_rows = [r for r in matching if "control" not in (r.get("Variant", "") or "").lower()]

    n_control = sum(int(r.get("Visitors", 0) or 0) for r in control_rows) or len(control_rows)
    n_variant = sum(int(r.get("Visitors", 0) or 0) for r in variant_rows) or len(variant_rows)
    conv_control = sum(int(r.get("Conversions", 0) or 0) for r in control_rows)
    conv_variant = sum(int(r.get("Conversions", 0) or 0) for r in variant_rows)

    rate_control = conv_control / n_control if n_control > 0 else 0
    rate_variant = conv_variant / n_variant if n_variant > 0 else 0

    # Sample Ratio Mismatch check (expected 50/50)
    total = n_control + n_variant
    expected_ratio = 0.5
    actual_ratio = n_control / total if total > 0 else 0
    srm_warning = abs(actual_ratio - expected_ratio) > 0.03

    print(f"\n  {'Variant':<15} {'Visitors':>10} {'Conversions':>12} {'Rate':>8}")
    print(f"  {'─' * 50}")
    print(f"  {'Control':<15} {n_control:>10,} {conv_control:>12,} {rate_control:>8.2%}")
    print(f"  {'Treatment':<15} {n_variant:>10,} {conv_variant:>12,} {rate_variant:>8.2%}")
    print(f"\n  Sample Ratio: {actual_ratio:.1%} / {1 - actual_ratio:.1%}")
    if srm_warning:
        print(f"  🚨 SRM WARNING: Traffic split deviates >3% from 50/50!")
        print(f"     Check randomization — results may be invalid.")
    else:
        print(f"  ✅ Sample ratio within expected range")

    print(f"\n  ⚠️  WARNING: Do NOT peek at results to make early decisions!")
    print(f"     Peeking inflates false-positive rate. Wait for full sample.")
    print(f"     Current total: {total:,} visitors")
    print("─" * 65)

    log_task(AGENT, f"Monitored A/B test: {args.test_name}",
             "Complete", "P3",
             f"ctrl={rate_control:.2%}, var={rate_variant:.2%}, n={total}")


def analyze(args):
    """Analyze a completed A/B test for statistical significance."""
    tests = query_db("landing_page_tests")
    matching = [t for t in tests if args.test_name.lower() in (t.get("Name", "") or "").lower()]

    print("=" * 65)
    print(f"  🔬 A/B TEST ANALYSIS: {args.test_name}")
    print("=" * 65)

    if not matching:
        print(f"\n  ❌ No data found for '{args.test_name}'")
        print("─" * 65)
        return

    control_rows = [r for r in matching if "control" in (r.get("Variant", "") or "").lower()]
    variant_rows = [r for r in matching if "control" not in (r.get("Variant", "") or "").lower()]

    n_c = sum(int(r.get("Visitors", 0) or 0) for r in control_rows) or len(control_rows)
    n_v = sum(int(r.get("Visitors", 0) or 0) for r in variant_rows) or len(variant_rows)
    conv_c = sum(int(r.get("Conversions", 0) or 0) for r in control_rows)
    conv_v = sum(int(r.get("Conversions", 0) or 0) for r in variant_rows)

    p_c = conv_c / n_c if n_c > 0 else 0
    p_v = conv_v / n_v if n_v > 0 else 0

    z = _z_score(p_c, p_v, n_c, n_v)
    p_val = _p_value(z)
    uplift = (p_v - p_c) / p_c * 100 if p_c > 0 else 0
    ci_c = _confidence_interval(p_c, n_c)
    ci_v = _confidence_interval(p_v, n_v)

    significant = p_val < 0.05
    winner = "Treatment" if significant and p_v > p_c else "Control" if significant else "Inconclusive"

    print(f"\n  {'Metric':<22} {'Control':>12} {'Treatment':>12}")
    print(f"  {'─' * 50}")
    print(f"  {'Visitors':<22} {n_c:>12,} {n_v:>12,}")
    print(f"  {'Conversions':<22} {conv_c:>12,} {conv_v:>12,}")
    print(f"  {'Conv. Rate':<22} {p_c:>12.3%} {p_v:>12.3%}")
    print(f"  {'95% CI':<22} {'[{:.3%},{:.3%}]'.format(*ci_c):>12} {'[{:.3%},{:.3%}]'.format(*ci_v):>12}")
    print(f"\n  Z-Score:       {z:+.4f}")
    print(f"  P-Value:       {p_val:.6f}")
    print(f"  Uplift:        {uplift:+.2f}%")
    print(f"  Significant:   {'✅ Yes (p < 0.05)' if significant else '❌ No (p ≥ 0.05)'}")
    print(f"\n  🏆 Winner: {winner}")
    print("─" * 65)

    # Update test records with result
    for row in matching:
        if row.get("_id"):
            update_row(row["_id"], "landing_page_tests", {
                "Notes": f"Result: {winner} | z={z:.3f} p={p_val:.4f} uplift={uplift:+.1f}%",
            })

    log_task(AGENT, f"Analyzed A/B test: {args.test_name}",
             "Complete", "P1",
             f"Winner={winner}, z={z:.3f}, p={p_val:.4f}, uplift={uplift:+.1f}%")


def active_tests(args):
    """List all currently running A/B tests."""
    snapshots = query_db("kpi_snapshots")
    active = [s for s in snapshots if (s.get("Name", "") or "").startswith("AB Test:")]

    print("=" * 65)
    print("  🧪 ACTIVE A/B TESTS")
    print("=" * 65)

    if not active:
        print("\n  No active A/B tests found.")
        print("  Use --action design to create a new test.")
        print("─" * 65)
        return

    for test in active:
        name = (test.get("Name", "") or "").replace("AB Test: ", "")
        notes = {}
        try:
            notes = json.loads(test.get("Notes", "") or "{}")
        except (json.JSONDecodeError, TypeError):
            pass

        status = notes.get("status", "unknown")
        days_needed = notes.get("days_needed", "?")
        start_date = test.get("Date", "?")
        metric = test.get("Metric", "?")

        icon = "🟢" if status == "running" else "✅" if status == "complete" else "⏸️"
        print(f"\n  {icon} {name}")
        print(f"    Metric: {metric} | Started: {start_date}")
        print(f"    Duration: {days_needed} days | Status: {status}")
        print(f"    Sample needed: {notes.get('sample_per_variant', '?'):,}/variant")

    print(f"\n{'─' * 65}")
    print(f"  Total active tests: {len(active)}")
    print("─" * 65)

    log_task(AGENT, "Listed active A/B tests", "Complete", "P3",
             f"{len(active)} tests")


def test_history(args):
    """Show history of all experiments with outcomes."""
    tests = query_db("landing_page_tests")

    print("=" * 65)
    print("  📜 A/B TEST HISTORY")
    print("=" * 65)

    if not tests:
        print("\n  No experiment history found.")
        print("─" * 65)
        return

    wins, losses, inconclusive = 0, 0, 0
    seen_names = set()
    for test in tests:
        name = test.get("Name", "Unnamed")
        if name in seen_names:
            continue
        seen_names.add(name)

        notes = test.get("Notes", "") or ""
        if "Winner" in notes or "Treatment" in notes:
            icon = "✅"
            wins += 1
        elif "Control" in notes:
            icon = "❌"
            losses += 1
        else:
            icon = "⬜"
            inconclusive += 1

        variant = test.get("Variant", "?")
        visitors = test.get("Visitors", 0) or 0
        print(f"\n  {icon} {name}")
        print(f"    Variant: {variant} | Visitors: {visitors:,}")
        if notes:
            print(f"    Result: {notes[:80]}")

    total = wins + losses + inconclusive
    win_pct = wins / total * 100 if total > 0 else 0

    print(f"\n{'─' * 65}")
    print(f"  Experiments: {total} | Wins: {wins} | Losses: {losses} | Inconclusive: {inconclusive}")
    print(f"  Win Rate: {win_pct:.0f}%")
    print("─" * 65)

    log_task(AGENT, "Reviewed test history", "Complete", "P3",
             f"{total} tests, {win_pct:.0f}% win rate")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="A/B Test Manager — Analytics Agent")
    p.add_argument("--action", required=True,
                   choices=["design", "monitor", "analyze", "active-tests", "test-history"])
    p.add_argument("--name", help="Test name")
    p.add_argument("--hypothesis", help="Test hypothesis")
    p.add_argument("--metric", choices=VALID_METRICS, help="Primary metric to measure")
    p.add_argument("--baseline-rate", type=float, help="Current baseline conversion rate")
    p.add_argument("--mde", type=float, help="Minimum detectable effect (absolute)")
    p.add_argument("--daily-traffic", type=int, default=500, help="Estimated daily visitor traffic")
    p.add_argument("--test-name", help="Name of test to monitor/analyze")

    args = p.parse_args()
    actions = {
        "design": design,
        "monitor": monitor,
        "analyze": analyze,
        "active-tests": active_tests,
        "test-history": test_history,
    }
    actions[args.action](args)
