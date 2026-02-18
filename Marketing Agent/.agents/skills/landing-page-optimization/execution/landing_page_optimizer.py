#!/usr/bin/env python3
"""
landing_page_optimizer.py — Marketing Agent Landing Page Optimization

Manage A/B tests on the hedge-edge.com landing page (Vercel-hosted).
Track experiments, record results, analyze conversion rates.

Usage:
    python landing_page_optimizer.py --action create-test --name "Hero CTA v2" --hypothesis "Protect My Accounts CTA > Start Free Trial" --variant-a "Start Free Trial" --variant-b "Protect My Accounts" --metric trial_signup_rate
    python landing_page_optimizer.py --action record-result --test-name "Hero CTA v2" --variant A --visitors 1200 --conversions 96
    python landing_page_optimizer.py --action active-tests
    python landing_page_optimizer.py --action test-report --test-name "Hero CTA v2"
    python landing_page_optimizer.py --action page-speed --lcp 2.1 --fid 45 --cls 0.08 --perf-score 91
"""

import sys, os, argparse, json, math
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Marketing"
VALID_METRICS = ["trial_signup_rate", "bounce_rate", "cta_click_rate", "checkout_rate"]
TARGET_CONVERSION = 0.08  # 8% visitor-to-trial target


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _z_test(conv_a, n_a, conv_b, n_b):
    """Two-proportion z-test. Returns (z_score, p_value, significant)."""
    if n_a == 0 or n_b == 0:
        return 0.0, 1.0, False
    p_a = conv_a / n_a
    p_b = conv_b / n_b
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) if p_pool > 0 else 1
    z = (p_b - p_a) / se if se > 0 else 0
    # Approximate two-tailed p-value using normal CDF
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p_value, p_value < 0.05


def _find_test(name):
    """Look up an A/B test row by name."""
    rows = query_db("landing_page_tests", filter={
        "property": "Name", "title": {"equals": name}
    })
    return rows[0] if rows else None


# ──────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────

def create_test(args):
    """Create a new landing page A/B test."""
    if args.metric and args.metric not in VALID_METRICS:
        print(f"❌ Invalid metric. Choose from: {', '.join(VALID_METRICS)}")
        return

    row = {
        "Name":           args.name,
        "Hypothesis":     args.hypothesis or "",
        "Variant A":      args.variant_a or "Control",
        "Variant B":      args.variant_b or "Challenger",
        "Metric":         args.metric or "trial_signup_rate",
        "Status":         "Active",
        "Visitors A":     0,
        "Conversions A":  0,
        "Visitors B":     0,
        "Conversions B":  0,
        "Created":        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    add_row("landing_page_tests", row)

    print("=" * 60)
    print("  🧪 NEW A/B TEST CREATED")
    print("=" * 60)
    print(f"\n  Test:       {args.name}")
    print(f"  Hypothesis: {row['Hypothesis']}")
    print(f"  Variant A:  {row['Variant A']}")
    print(f"  Variant B:  {row['Variant B']}")
    print(f"  Metric:     {row['Metric']}")
    print(f"  Status:     Active")
    print(f"  Target:     {TARGET_CONVERSION:.0%} visitor-to-trial\n")

    log_task(AGENT, f"A/B test created: {args.name}", "Complete", "P2",
             f"Metric: {row['Metric']} | {row['Variant A']} vs {row['Variant B']}")


def record_result(args):
    """Record visitors + conversions for a test variant."""
    test = _find_test(args.test_name)
    if not test:
        print(f"❌ Test not found: {args.test_name}")
        return

    variant = args.variant.upper()
    if variant not in ("A", "B"):
        print("❌ --variant must be A or B")
        return

    vis_key = f"Visitors {variant}"
    conv_key = f"Conversions {variant}"
    new_visitors = (test.get(vis_key) or 0) + args.visitors
    new_conversions = (test.get(conv_key) or 0) + args.conversions
    rate = new_conversions / new_visitors if new_visitors > 0 else 0

    update_row(test["_id"], "landing_page_tests", {
        vis_key: new_visitors,
        conv_key: new_conversions,
    })

    status_icon = "🟢" if rate >= TARGET_CONVERSION else "🟡" if rate >= 0.05 else "🔴"
    print(f"  {status_icon} Variant {variant} updated for \"{args.test_name}\"")
    print(f"     Visitors: {new_visitors:,} | Conversions: {new_conversions:,} | Rate: {rate:.2%}")

    log_task(AGENT, f"A/B result: {args.test_name} variant {variant}", "Complete", "P3",
             f"{args.visitors} visitors, {args.conversions} conversions ({rate:.2%})")


def active_tests(args):
    """List all active A/B tests."""
    tests = query_db("landing_page_tests", filter={
        "property": "Status", "select": {"equals": "Active"}
    })

    print("=" * 70)
    print("  🧪 ACTIVE LANDING PAGE TESTS")
    print("=" * 70)

    if not tests:
        print("\n  No active tests. Create one with --action create-test\n")
        return

    print(f"\n  {'Test':<30} {'Metric':<20} {'A Rate':>8} {'B Rate':>8} {'Created'}")
    print(f"  {'─'*30} {'─'*20} {'─'*8} {'─'*8} {'─'*10}")

    for t in tests:
        va = (t.get("Conversions A") or 0) / max(t.get("Visitors A") or 1, 1)
        vb = (t.get("Conversions B") or 0) / max(t.get("Visitors B") or 1, 1)
        print(f"  {t.get('Name', '?'):<30} {t.get('Metric', '?'):<20} {va:>7.2%} {vb:>7.2%} {t.get('Created', '?')}")

    print(f"\n  Total active tests: {len(tests)}\n")
    log_task(AGENT, "Active A/B tests listed", "Complete", "P3",
             f"{len(tests)} active tests")


def test_report(args):
    """Generate full report for a specific A/B test."""
    test = _find_test(args.test_name)
    if not test:
        print(f"❌ Test not found: {args.test_name}")
        return

    va_vis = test.get("Visitors A") or 0
    va_conv = test.get("Conversions A") or 0
    vb_vis = test.get("Visitors B") or 0
    vb_conv = test.get("Conversions B") or 0
    rate_a = va_conv / va_vis if va_vis > 0 else 0
    rate_b = vb_conv / vb_vis if vb_vis > 0 else 0
    uplift = ((rate_b - rate_a) / rate_a * 100) if rate_a > 0 else 0
    z, p_val, significant = _z_test(va_conv, va_vis, vb_conv, vb_vis)

    winner = None
    if significant:
        winner = "B" if rate_b > rate_a else "A"

    print("=" * 65)
    print(f"  📊 A/B TEST REPORT: {args.test_name}")
    print("=" * 65)
    print(f"\n  Hypothesis: {test.get('Hypothesis', '—')}")
    print(f"  Metric:     {test.get('Metric', '?')}")
    print(f"  Status:     {test.get('Status', '?')}")

    print(f"\n  {'Variant':<25} {'Visitors':>10} {'Conversions':>12} {'Rate':>8}")
    print(f"  {'─'*25} {'─'*10} {'─'*12} {'─'*8}")
    label_a = test.get("Variant A") or "A"
    label_b = test.get("Variant B") or "B"
    print(f"  A: {label_a:<20} {va_vis:>10,} {va_conv:>12,} {rate_a:>7.2%}")
    print(f"  B: {label_b:<20} {vb_vis:>10,} {vb_conv:>12,} {rate_b:>7.2%}")

    print(f"\n  ─── Statistical Analysis ───")
    print(f"  Uplift (B vs A): {uplift:+.1f}%")
    print(f"  Z-score:         {z:.3f}")
    print(f"  P-value:         {p_val:.4f}")
    print(f"  Significant:     {'✅ Yes (p < 0.05)' if significant else '⏳ Not yet (p ≥ 0.05)'}")

    if winner:
        print(f"\n  🏆 WINNER: Variant {winner} — {'B: ' + label_b if winner == 'B' else 'A: ' + label_a}")
        meets_target = (rate_b if winner == "B" else rate_a) >= TARGET_CONVERSION
        print(f"  Target ({TARGET_CONVERSION:.0%}): {'✅ Met' if meets_target else '⚠️ Below target'}")
    else:
        total = va_vis + vb_vis
        print(f"\n  ⏳ Need more data. Current sample: {total:,} visitors.")
        if total < 1000:
            print(f"     Recommend at least 1,000 visitors per variant for significance.")

    print()
    log_task(AGENT, f"A/B report: {args.test_name}", "Complete", "P2",
             f"A={rate_a:.2%} B={rate_b:.2%} uplift={uplift:+.1f}% sig={significant}")


def page_speed(args):
    """Log a Core Web Vitals / page speed audit to kpi_snapshots."""
    lcp_ok = args.lcp <= 2.5
    fid_ok = args.fid <= 100
    cls_ok = args.cls <= 0.1
    score = args.perf_score

    row = {
        "Name":  f"Page Speed Audit {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "Date":  datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "LCP":   args.lcp,
        "FID":   args.fid,
        "CLS":   args.cls,
        "Perf Score": score,
    }
    add_row("kpi_snapshots", row)

    print("=" * 55)
    print("  ⚡ PAGE SPEED AUDIT — hedge-edge.com")
    print("=" * 55)
    print(f"\n  LCP  (Largest Contentful Paint):  {args.lcp:.1f}s  {'✅' if lcp_ok else '🔴 > 2.5s'}")
    print(f"  FID  (First Input Delay):         {args.fid}ms   {'✅' if fid_ok else '🔴 > 100ms'}")
    print(f"  CLS  (Cumulative Layout Shift):   {args.cls:.3f}  {'✅' if cls_ok else '🔴 > 0.10'}")
    print(f"  Perf Score:                       {score}/100 {'🟢' if score >= 90 else '🟡' if score >= 50 else '🔴'}")

    passed = sum([lcp_ok, fid_ok, cls_ok])
    print(f"\n  Core Web Vitals: {passed}/3 passing")
    if not lcp_ok:
        print("  💡 Tip: Optimize hero image, enable lazy loading, check Vercel edge caching.")
    if not cls_ok:
        print("  💡 Tip: Set explicit width/height on images, avoid dynamic content injection.")
    print()

    log_task(AGENT, "Page speed audit logged", "Complete", "P3",
             f"LCP={args.lcp}s FID={args.fid}ms CLS={args.cls} Score={score}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Landing Page A/B Test Optimizer")
    parser.add_argument("--action", required=True,
                        choices=["create-test", "record-result", "active-tests",
                                 "test-report", "page-speed"])
    parser.add_argument("--name")
    parser.add_argument("--hypothesis")
    parser.add_argument("--variant-a", dest="variant_a")
    parser.add_argument("--variant-b", dest="variant_b")
    parser.add_argument("--metric", choices=VALID_METRICS)
    parser.add_argument("--test-name", dest="test_name")
    parser.add_argument("--variant")
    parser.add_argument("--visitors", type=int, default=0)
    parser.add_argument("--conversions", type=int, default=0)
    parser.add_argument("--lcp", type=float, default=0)
    parser.add_argument("--fid", type=float, default=0)
    parser.add_argument("--cls", type=float, default=0)
    parser.add_argument("--perf-score", type=int, default=0, dest="perf_score")

    args = parser.parse_args()
    {
        "create-test":   create_test,
        "record-result": record_result,
        "active-tests":  active_tests,
        "test-report":   test_report,
        "page-speed":    page_speed,
    }[args.action](args)
