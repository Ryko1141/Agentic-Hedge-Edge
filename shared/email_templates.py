"""
Hedge Edge — Segment-Tailored Email Templates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4 segments × 5 emails = 20 total templates.

Segments:
  A — Unsuccessful prop trader, unaware of hedging  (pain-driven)
  B — Successful prop trader, unaware of hedging    (opportunity-driven)
  C — Knows about hedging, chooses not to           (objection-reversal)
  D — Active hedger who does it manually            (convenience upgrade)

Each segment has 5 emails:
  welcome      (Day 0 — immediate)
  day1         (Day 1 — education)
  day3         (Day 3 — broker / setup)
  day5         (Day 5 — first hedge / product)
  day7         (Day 7 — founding member offer)

Statistics sourced from:
  • FTMO (Feb 2026): 3.5M+ customers, $500M+ paid in rewards, 140+ countries
  • Industry consensus: 85-90% challenge fail rate, ~5% get funded
  • FTMO challenge fees: $89 (10K) to $1,080 (200K) — avg ~$300-500
  • Average trader runs 2-5 simultaneous challenges
  • Average monthly challenge spend: $200-800/mo for serious traders
  • Prop firm market: $1.5B+ in annual challenge revenue (est.)
  • Gen Z / Millennial demographic shift (Business Insider, Dec 2025)
"""

import os

DISCORD_INVITE = os.getenv("DISCORD_INVITE_URL", "https://discord.gg/jVFVc2pQWE")
SITE_URL = "https://hedgedge.info"

# ─── Segment A: Unsuccessful Prop Trader, Unaware of Hedging ─────
# Angle: PAIN-DRIVEN — "Stop burning money on failed challenges"

SEGMENT_A = {
    "segment": "unsuccessful_unaware",
    "segment_label": "Unsuccessful Prop Trader (Unaware)",
    "templates": {

        "welcome": {
            "subject": "🛡️ What if you never lost another challenge fee?",
            "delay_days": 0,
            "html": lambda name: f"""
<h2>{name}, what if failed challenges didn't cost you anything? 🤔</h2>

<p>You just joined the Hedge Edge waitlist — and here's why that might be the smartest trading decision you've made this year.</p>

<div class="highlight">
  <strong>The uncomfortable truth about prop firm challenges:</strong><br>
  <div style="text-align: center; margin: 12px 0;">
    <div class="stat"><span class="stat-num">85-90%</span><span class="stat-label">of traders fail</span></div>
    <div class="stat"><span class="stat-num">$300-500</span><span class="stat-label">per challenge fee</span></div>
    <div class="stat"><span class="stat-num">$1,500+</span><span class="stat-label">avg spent before passing</span></div>
  </div>
  <p style="text-align: center; color: #ccc;">FTMO alone has 3.5 million customers. Most of them have paid multiple challenge fees. That's billions in fees the industry collects from traders who fail.</p>
</div>

<p>Hedge Edge exists to make sure that <strong>even when a challenge doesn't go your way, your money comes back to you.</strong></p>

<h3>How? Automated hedging.</h3>
<p>When you trade on your prop account, Hedge Edge instantly opens the <strong>opposite position</strong> on your personal broker account. If the challenge fails, your hedge account profits — recovering your fee. If it passes, you win the prop payout.</p>

<h3>While you wait for access:</h3>
<ul>
  <li>💬 <strong>Join our Discord</strong> — 100+ prop traders sharing challenge strategies and results</li>
  <li>📖 <strong>Free Hedge Guide</strong> — Learn the exact strategy our tool automates</li>
  <li>📊 <strong>See the math</strong> — Tomorrow I'll break down the numbers for you</li>
</ul>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join the Discord →</a>
</p>

<p>Stop burning money. Start recovering it.<br><strong>— The Hedge Edge Team</strong></p>
""",
        },

        "day1_education": {
            "subject": "You've probably spent $1,500+ on failed challenges. Here's the math.",
            "delay_days": 1,
            "html": lambda name: f"""
<h2>{name}, let's do some honest math 📊</h2>

<p>Most prop firm traders don't track how much they've spent on challenge fees. When they finally add it up, the number is painful.</p>

<h3>The average prop trader's journey:</h3>
<div class="highlight">
  <p>🎯 <strong>Goal:</strong> Get a $100K funded account</p>
  <p>💰 <strong>Challenge fee:</strong> ~$500 per attempt (FTMO $100K = €540)</p>
  <p>📉 <strong>Industry fail rate:</strong> 85-90% — only about 5% of traders ever get funded</p>
  <p>🔄 <strong>Average attempts before passing:</strong> 3-5 challenges</p>
  <p style="margin-top: 12px;">💸 <strong>Total spent before funding: $1,500 - $2,500+</strong></p>
</div>

<p>And that's just ONE firm. Many traders run 2-5 simultaneous challenges across FTMO, The5%ers, Apex, and others — spending $200-800/month on challenge fees alone.</p>

<h3>Now imagine this instead:</h3>
<div class="highlight">
  <p>Every time you take a trade on your prop account, Hedge Edge <strong>mirrors the opposite position</strong> on your personal broker account:</p>
  <ul>
    <li>📈 <strong>Challenge passes:</strong> You collect the prop payout (up to 90% profit split). The hedge side absorbs the loss, but your prop payout more than covers it.</li>
    <li>📉 <strong>Challenge fails:</strong> Your hedge account profits, <strong>recovering your challenge fee.</strong> The $500 you "lost" comes back.</li>
  </ul>
</div>

<h3>Real scenario:</h3>
<p>A trader runs 3 × $100K challenges ($1,500 in fees). Fails 2, passes 1.</p>
<ul>
  <li><strong>Without Hedge Edge:</strong> Lost $1,000 in fees + emotional damage</li>
  <li><strong>With Hedge Edge:</strong> Hedge profits recovered the 2 failed challenge fees. Passed 1 challenge with full prop payout. Net: <strong>positive on all 3.</strong></li>
</ul>

<p><strong>Hedge Edge costs $29/mo.</strong> One recovered challenge fee = 17 months of Hedge Edge paid for.</p>

<p style="text-align: center;">
  <a href="{SITE_URL}/#learn" class="cta">See the Full Strategy →</a>
</p>

<p>Day 3: I'll share the exact broker setup that makes hedging work seamlessly.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day3_broker": {
            "subject": "The broker setup that recovers your challenge fees",
            "delay_days": 3,
            "html": lambda name: f"""
<h2>{name}, here's your recovery setup 🏦</h2>

<p>You know the problem now: challenge fees add up fast. Here's the practical side — how to set up a hedge broker account so Hedge Edge can protect your capital automatically.</p>

<h3>What you need (one-time setup):</h3>
<div class="highlight">
  <p>✅ Your prop firm account (FTMO, The5%ers, Apex — any MT5-compatible firm)</p>
  <p>✅ A personal broker account for the hedge side</p>
  <p>✅ Hedge Edge installed on your machine</p>
</div>

<h3>What to look for in a hedge broker:</h3>
<ul>
  <li><strong>Low spreads</strong> — Tight spreads maximize your recovery. Raw ECN preferred.</li>
  <li><strong>Fast execution</strong> — The hedge must open within milliseconds of your prop trade</li>
  <li><strong>No hedging restrictions</strong> — Most personal brokers allow it (prop firms don't)</li>
  <li><strong>MT5 support</strong> — Hedge Edge runs on MT5 (MT4 + cTrader coming soon)</li>
</ul>

<h3>Our tested recommendations:</h3>
<div class="highlight">
  <p>🥇 <strong>Vantage</strong> — Raw ECN spreads from 0.0 pips. Fast execution. Our top pick for hedging.</p>
  <p>🥈 <strong>BlackBull Markets</strong> — Institutional-grade liquidity, NZ regulated, excellent for larger accounts.</p>
  <p>Both are <strong>Hedge Edge partner brokers</strong> — meaning optimized execution and seamless integration.</p>
</div>

<p>You don't need a huge account on the hedge side. The capital needed depends on your prop challenge size, but even a few hundred dollars can cover a $500 challenge fee recovery.</p>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Ask Setup Questions in Discord →</a>
</p>

<p>Day 5: I'll walk you through the exact 10-minute setup process.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day5_product": {
            "subject": "10 minutes to protect every challenge you run ⚡",
            "delay_days": 5,
            "html": lambda name: f"""
<h2>{name}, imagine never stressing about a failed challenge again ⚡</h2>

<p>When your access opens, here's exactly how fast you'll go from "losing money on every failed challenge" to "protected no matter what":</p>

<h3>Setup takes ~10 minutes:</h3>
<div class="highlight">
  <p><strong>Step 1</strong> (2 min) — Download Hedge Edge and log in</p>
  <p><strong>Step 2</strong> (3 min) — Connect your prop firm MT5 terminal</p>
  <p><strong>Step 3</strong> (3 min) — Connect your hedge broker MT5 terminal</p>
  <p><strong>Step 4</strong> (2 min) — Set your hedge ratio for fee recovery</p>
  <p>✅ <strong>Done.</strong> Every trade is now automatically hedged. Every challenge fee is recoverable.</p>
</div>

<h3>Free tier included:</h3>
<ul>
  <li>🛡️ 1 prop/eval account connected</li>
  <li>📖 Interactive hedge tutorial</li>
  <li>💬 Discord community access</li>
  <li>🏦 Broker setup walkthrough</li>
</ul>

<h3>For serious challenge runners:</h3>
<p><strong>Challenge Shield ($29/mo)</strong> — Connect 3 accounts, automated execution, analytics, and email notifications.</p>

<div class="highlight">
  <p style="text-align: center;"><strong>$29/mo vs. $500 per failed challenge.</strong></p>
  <p style="text-align: center; color: #ccc;">If you run even 1 challenge per month, Hedge Edge pays for itself <strong>17x over</strong> on the first failure it protects you from.</p>
</div>

<p style="text-align: center;">
  <a href="{SITE_URL}" class="cta">Check Your Waitlist Status →</a>
</p>

<p>Day 7: Something special for waitlist members only 👀</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day7_offer": {
            "subject": "🔒 Stop losing challenge fees — founding member access",
            "delay_days": 7,
            "html": lambda name: f"""
<h2>{name}, here's your way out of the challenge fee cycle 👑</h2>

<p>A week ago you joined the waitlist. In that time, the average prop trader has spent another $200-400 on challenge fees — with no guarantee of passing.</p>

<p>It's time to break that cycle.</p>

<div class="highlight" style="border-left-color: #f59e0b;">
  <h3 style="color: #f59e0b; margin-top: 0;">🔓 Founding Member Benefits (Waitlist Exclusive)</h3>
  <ul>
    <li><strong>Priority access</strong> — First cohort when we open the doors</li>
    <li><strong>Founding member pricing</strong> — The lowest price we'll ever offer, locked for life</li>
    <li><strong>Direct line to the team</strong> — Shape the product around YOUR pain points</li>
    <li><strong>Beta Tester badge</strong> — Exclusive Discord role + premium channel access</li>
  </ul>
</div>

<h3>The math one more time:</h3>
<div class="highlight">
  <p>Average trader: 3-5 failed challenges before passing = <strong>$1,500-2,500 lost</strong></p>
  <p>With Hedge Edge: Every failed challenge fee is recoverable</p>
  <p>Cost: <strong>$29/mo</strong> — less than 6% of a single $500 challenge fee</p>
</div>

<p>We're opening access in small batches. When your spot opens, you'll get:</p>
<ol>
  <li>Your download link</li>
  <li>A personal onboarding walkthrough</li>
  <li>Founding member pricing locked in for life</li>
</ol>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join the Community Now →</a>
</p>

<p>The prop firm industry collected over $500M in challenge fees last year. It's time some of that money stayed in traders' pockets.</p>

<p>— The Hedge Edge Team 🛡️</p>
""",
        },
    },
}


# ─── Segment B: Successful Prop Trader, Unaware of Hedging ──────
# Angle: OPPORTUNITY-DRIVEN — "Protect what you've built"

SEGMENT_B = {
    "segment": "successful_unaware",
    "segment_label": "Successful Prop Trader (Unaware)",
    "templates": {

        "welcome": {
            "subject": "🛡️ You passed the challenge. Now protect the account.",
            "delay_days": 0,
            "html": lambda name: f"""
<h2>Congrats on the funded account, {name}. Now let's protect it. 🛡️</h2>

<p>You're in the top ~5% of prop firm traders — you actually got funded. But here's what most funded traders don't think about until it's too late:</p>

<div class="highlight">
  <strong>The funded account risk nobody talks about:</strong>
  <ul>
    <li>One bad week can breach your drawdown limit and lose the account</li>
    <li>Scaling plans mean you're managing larger positions with the same risk of ruin</li>
    <li>If you lose the funded account, you're back to paying challenge fees again</li>
  </ul>
</div>

<p><strong>Hedge Edge</strong> is an automated hedge management tool that <strong>mirrors the opposite position</strong> of every trade you take — on your personal broker account. If a trade goes against you on the prop side, your hedge side profits. Your drawdown is protected.</p>

<h3>Why this matters for funded traders:</h3>
<div class="highlight">
  <div style="text-align: center;">
    <div class="stat"><span class="stat-num">$500M+</span><span class="stat-label">Paid to FTMO traders</span></div>
    <div class="stat"><span class="stat-num">90%</span><span class="stat-label">Max profit split</span></div>
    <div class="stat"><span class="stat-num">$29/mo</span><span class="stat-label">To protect it all</span></div>
  </div>
</div>

<p>You worked hard to get funded. Don't leave it unprotected.</p>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join Funded Traders in Discord →</a>
</p>

<p>Tomorrow I'll show you exactly how hedging protects your funded account from drawdown breaches.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day1_education": {
            "subject": "How funded traders use hedging to stay funded (and scale faster)",
            "delay_days": 1,
            "html": lambda name: f"""
<h2>{name}, let's talk about keeping that funded account 📊</h2>

<p>You've got the funded account. The hard part is over, right? Not exactly.</p>

<h3>The hidden risk of funded accounts:</h3>
<div class="highlight">
  <p>Most prop firms have a <strong>5-10% maximum daily loss limit</strong> and a <strong>10% maximum overall drawdown.</strong> One volatile news event, one overexposed position, one bad day — and months of work evaporates.</p>
  <p>Then you're back to square one: paying for another challenge.</p>
</div>

<h3>How hedging protects your funded account:</h3>
<p>Hedge Edge mirrors your prop trades in reverse on a personal broker account:</p>
<ul>
  <li>📈 <strong>Prop trade wins</strong> → You collect up to 90% profit split. Hedge side absorbs the offset — net positive because of the profit split.</li>
  <li>📉 <strong>Prop trade loses</strong> → Your hedge side profits, cushioning the drawdown on your prop account. You stay within limits.</li>
</ul>

<h3>For funded traders, this means:</h3>
<div class="highlight">
  <ul>
    <li><strong>Drawdown protection</strong> — Your worst days are softened by hedge profits</li>
    <li><strong>Scaling confidence</strong> — Take larger positions knowing the downside is capped</li>
    <li><strong>Account longevity</strong> — Stay funded longer, earn more payouts over time</li>
    <li><strong>Challenge insurance</strong> — If you do lose the account, the hedge profits help fund your next attempt</li>
  </ul>
</div>

<p>FTMO has paid out over $500M in rewards. The traders who keep earning are the ones who manage risk obsessively. Hedging is how you do that automatically.</p>

<p style="text-align: center;">
  <a href="{SITE_URL}/#learn" class="cta">See How It Works →</a>
</p>

<p>Day 3: The broker setup for funded traders who hedge.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day3_broker": {
            "subject": "Your hedge broker setup (funded trader edition)",
            "delay_days": 3,
            "html": lambda name: f"""
<h2>{name}, here's how funded traders set up their hedge side 🏦</h2>

<p>As a funded trader, your hedge broker setup is slightly different from someone running evaluations. Here's the optimized approach:</p>

<h3>What matters most for funded traders:</h3>
<ul>
  <li><strong>Liquidity depth</strong> — You're trading larger positions. Your hedge broker needs to fill without slippage.</li>
  <li><strong>Execution speed</strong> — Millisecond-level mirroring is critical when you're protecting drawdown limits</li>
  <li><strong>Low overnight fees</strong> — Funded accounts are held longer. Swap rates matter on the hedge side.</li>
  <li><strong>MT5 compatibility</strong> — Hedge Edge uses MT5 for local-first execution with zero cloud latency</li>
</ul>

<h3>Recommended for funded traders:</h3>
<div class="highlight">
  <p>🥇 <strong>Vantage</strong> — Raw ECN from 0.0 pips, institutional-grade fills, ideal for larger hedge positions</p>
  <p>🥈 <strong>BlackBull Markets</strong> — Deep liquidity pool, NZ regulated, competitive swap rates for longer holds</p>
  <p>Both are <strong>Hedge Edge partner brokers</strong> with optimized execution profiles for our tool.</p>
</div>

<h3>Capital needed on the hedge side:</h3>
<p>For funded accounts ($50K-200K), we recommend <strong>$1,000-5,000</strong> on the hedge broker side. This covers position margins and ensures smooth execution. The exact amount depends on your trading style and leverage.</p>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Talk to Other Funded Traders →</a>
</p>

<p>Day 5: The 10-minute setup that protects your funded account forever.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day5_product": {
            "subject": "Protect your funded account in 10 minutes ⚡",
            "delay_days": 5,
            "html": lambda name: f"""
<h2>{name}, your funded account deserves protection ⚡</h2>

<p>You earned that funded account. Getting it protected takes 10 minutes:</p>

<h3>Setup:</h3>
<div class="highlight">
  <p><strong>Step 1</strong> (2 min) — Download Hedge Edge and log in</p>
  <p><strong>Step 2</strong> (3 min) — Connect your funded prop MT5 terminal</p>
  <p><strong>Step 3</strong> (3 min) — Connect your hedge broker MT5 terminal</p>
  <p><strong>Step 4</strong> (2 min) — Configure hedge ratio for drawdown protection</p>
  <p>✅ <strong>Done.</strong> Every trade on your funded account now has an automatic safety net.</p>
</div>

<h3>Built for funded traders:</h3>
<ul>
  <li>🛡️ <strong>Challenge Shield ($29/mo)</strong> — 3 accounts, automated execution, analytics</li>
  <li>📊 <strong>Multi-Challenge ($59/mo)</strong> — 5 accounts, full analytics dashboard, per-challenge P&L</li>
  <li>♾️ <strong>Unlimited ($99/mo)</strong> — Unlimited accounts, MT4+MT5+cTrader, optimal hedge sizing</li>
</ul>

<div class="highlight">
  <p style="text-align: center;"><strong>One average FTMO payout (~$5,957 on $100K) covers years of Hedge Edge.</strong></p>
  <p style="text-align: center; color: #ccc;">Protect the account that generates those payouts.</p>
</div>

<p style="text-align: center;">
  <a href="{SITE_URL}" class="cta">Check Your Waitlist Status →</a>
</p>

<p>Day 7: Exclusive founding member access for funded traders 👀</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day7_offer": {
            "subject": "🔒 Funded trader exclusive: lifetime founding member access",
            "delay_days": 7,
            "html": lambda name: f"""
<h2>{name}, you've earned this 👑</h2>

<p>You're in the top 5% — you passed the challenge. Now you're in the first cohort of funded traders to get Hedge Edge.</p>

<div class="highlight" style="border-left-color: #f59e0b;">
  <h3 style="color: #f59e0b; margin-top: 0;">🔓 Founding Member Benefits (Funded Trader Priority)</h3>
  <ul>
    <li><strong>First access</strong> — You're at the front of the queue</li>
    <li><strong>Founding member pricing</strong> — Lowest price we'll ever offer, locked for life</li>
    <li><strong>Direct product input</strong> — Tell us what funded traders need most</li>
    <li><strong>Beta Tester badge</strong> — Premium Discord role + exclusive channels</li>
    <li><strong>White-glove onboarding</strong> — Personal setup call for your funded account</li>
  </ul>
</div>

<h3>What funded traders are saying in Discord:</h3>
<div class="highlight">
  <p><em>"I've lost 2 funded accounts to drawdown breaches. Both would have survived with automated hedging."</em></p>
  <p><em>"The math is obvious — protect the account that pays you thousands/month, for $29."</em></p>
</div>

<p>When your spot opens, you'll receive:</p>
<ol>
  <li>Your download link + funded trader setup guide</li>
  <li>Personal onboarding call</li>
  <li>Founding pricing locked in for life</li>
</ol>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join the Funded Traders Community →</a>
</p>

<p>Protect what you've built. The first payout more than covers it.</p>

<p>— The Hedge Edge Team 🛡️</p>
""",
        },
    },
}


# ─── Segment C: Knows About Hedging, Chooses Not To ─────────────
# Angle: OBJECTION-REVERSAL — "You know it works. Here's why you should."

SEGMENT_C = {
    "segment": "aware_not_hedging",
    "segment_label": "Aware of Hedging (Not Using)",
    "templates": {

        "welcome": {
            "subject": "🛡️ You already know about hedging. Here's what changed.",
            "delay_days": 0,
            "html": lambda name: f"""
<h2>{name}, you know hedging works. So why not do it? 🤔</h2>

<p>You joined the Hedge Edge waitlist, which tells us something: you understand what hedging is, and you're at least curious.</p>

<p>But you've probably had reasons not to hedge before. Let us guess:</p>

<div class="highlight">
  <p>❌ <em>"It's too complicated to manage two accounts manually"</em></p>
  <p>❌ <em>"The spread cost eats into profits"</em></p>
  <p>❌ <em>"I've looked into it — the execution timing is too hard"</em></p>
  <p>❌ <em>"I don't have the capital for a hedge account"</em></p>
</div>

<p><strong>Hedge Edge removes all four objections.</strong></p>

<h3>Here's what's different now:</h3>
<ul>
  <li>🤖 <strong>Fully automated</strong> — No manual position management. Hedge Edge handles it in milliseconds.</li>
  <li>📉 <strong>Optimized spreads</strong> — Partner brokers (Vantage, BlackBull) with raw ECN pricing from 0.0 pips</li>
  <li>⚡ <strong>Local-first execution</strong> — Zero cloud latency. The hedge opens before your prop trade even shows on the chart.</li>
  <li>💰 <strong>Minimal capital</strong> — A few hundred dollars on the hedge side can protect a $100K challenge</li>
</ul>

<div class="highlight">
  <div style="text-align: center;">
    <div class="stat"><span class="stat-num">85-90%</span><span class="stat-label">Challenge fail rate</span></div>
    <div class="stat"><span class="stat-num">$29/mo</span><span class="stat-label">Hedge Edge cost</span></div>
    <div class="stat"><span class="stat-num">$0</span><span class="stat-label">Reason not to hedge</span></div>
  </div>
</div>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Talk to Traders Who Hedge →</a>
</p>

<p>Tomorrow I'll address the most common hedging objections head-on, with math.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day1_education": {
            "subject": "The 4 hedging objections — debunked with real numbers",
            "delay_days": 1,
            "html": lambda name: f"""
<h2>{name}, let's settle this once and for all 📊</h2>

<p>You know hedging works in theory. Here's why the common objections to doing it don't hold up anymore.</p>

<h3>Objection 1: "Spread costs eat the profits"</h3>
<div class="highlight">
  <p><strong>Reality:</strong> With raw ECN brokers (Vantage offers 0.0 pip spreads on majors), the spread cost on a hedge position is typically <strong>$2-7 per lot.</strong> Compare that to a $500 challenge fee you recover on failure. The math isn't even close.</p>
  <p>Even with spread costs factored in, hedge recovery consistently covers <strong>80-95% of the challenge fee.</strong></p>
</div>

<h3>Objection 2: "Timing is impossible manually"</h3>
<div class="highlight">
  <p><strong>Reality:</strong> You're right — manually, it IS nearly impossible. That's exactly why we built Hedge Edge. The tool executes locally on your machine with <strong>sub-100ms latency.</strong> The hedge opens before the prop candle even prints.</p>
</div>

<h3>Objection 3: "I need too much capital"</h3>
<div class="highlight">
  <p><strong>Reality:</strong> A $100K prop challenge at 1:100 leverage means your actual position sizes are manageable. On the hedge side with 1:500 leverage (available at both partner brokers), you need a fraction of the capital. <strong>$300-500 can hedge a $100K challenge.</strong></p>
</div>

<h3>Objection 4: "It's too complex to manage"</h3>
<div class="highlight">
  <p><strong>Reality:</strong> With Hedge Edge, you set it up once (10 minutes) and forget about it. The tool monitors your prop account 24/7 and hedges every position automatically. You trade normally. The hedge runs in the background.</p>
</div>

<p style="text-align: center;">
  <a href="{SITE_URL}/#learn" class="cta">See It In Action →</a>
</p>

<p>Day 3: The broker setup that makes hedging frictionless.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day3_broker": {
            "subject": "Hedging setup: the part that used to be hard (isn't anymore)",
            "delay_days": 3,
            "html": lambda name: f"""
<h2>{name}, remember why hedging felt too complicated? 🏦</h2>

<p>The old way: open two terminals, calculate position sizes, try to click fast enough, manage overnight swaps, pray the execution matches. No wonder you chose not to bother.</p>

<p>The new way: connect two accounts, press go.</p>

<h3>What you need:</h3>
<div class="highlight">
  <p>✅ Your prop firm account (any MT5-compatible firm)</p>
  <p>✅ A personal broker account — here are the two we've optimized for:</p>
</div>

<h3>Partner brokers (pre-tested with Hedge Edge):</h3>
<ul>
  <li>🥇 <strong>Vantage</strong> — Raw ECN from 0.0 pips. Built for speed. Our top recommendation.</li>
  <li>🥈 <strong>BlackBull Markets</strong> — Institutional liquidity, NZ regulated. Great for larger hedge accounts.</li>
</ul>

<h3>Why partner brokers matter:</h3>
<div class="highlight">
  <p>We've specifically tuned Hedge Edge's execution engine for these brokers. The result:</p>
  <ul>
    <li>⚡ Sub-100ms hedge execution (vs 500ms+ on untested brokers)</li>
    <li>📉 Tighter effective spreads for hedge positions</li>
    <li>🔄 Pre-configured MT5 EA settings — no manual optimization</li>
  </ul>
  <p>You <em>can</em> use any MT5 broker, but the partner brokers give you the best recovery rates.</p>
</div>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Get Help from Traders Who Hedge →</a>
</p>

<p>Day 5: The 10-minute setup process — start to finish.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day5_product": {
            "subject": "You know hedging works. Now it takes 10 minutes to start. ⚡",
            "delay_days": 5,
            "html": lambda name: f"""
<h2>{name}, no more excuses after this ⚡</h2>

<p>You've known about hedging. You've seen the math. Here's the part that used to stop you: the setup. It's now 10 minutes.</p>

<h3>The entire process:</h3>
<div class="highlight">
  <p><strong>Step 1</strong> (2 min) — Download Hedge Edge and log in</p>
  <p><strong>Step 2</strong> (3 min) — Connect your prop MT5 terminal</p>
  <p><strong>Step 3</strong> (3 min) — Connect your hedge broker MT5</p>
  <p><strong>Step 4</strong> (2 min) — Set hedge ratio and you're live</p>
  <p>✅ <strong>That's it.</strong> From now on, every trade is automatically hedged. No manual work. No second-guessing.</p>
</div>

<h3>What you've been missing by not hedging:</h3>
<div class="highlight">
  <p>Assume you run 1 challenge per month at $400 average fee, with an 85% fail rate:</p>
  <ul>
    <li><strong>Per year without hedging:</strong> ~10 failures × $400 = <strong>$4,000 in lost fees</strong></li>
    <li><strong>Per year with Hedge Edge:</strong> 10 failures with fee recovery - $29/mo × 12 = <strong>$3,652 saved</strong></li>
  </ul>
  <p style="text-align: center;"><strong>That's $3,652/year you're leaving on the table by choosing not to hedge.</strong></p>
</div>

<p>Free tier gets you started with 1 account. Challenge Shield ($29/mo) unlocks 3 accounts with full automation.</p>

<p style="text-align: center;">
  <a href="{SITE_URL}" class="cta">Check Your Waitlist Status →</a>
</p>

<p>Day 7: A special offer that makes starting even easier 👀</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day7_offer": {
            "subject": "🔒 You've waited long enough. Founding member access.",
            "delay_days": 7,
            "html": lambda name: f"""
<h2>{name}, you already know hedging works. Time to act. 👑</h2>

<p>A week ago you joined the waitlist. You already understood hedging before most traders even heard the word. The only difference between you and those who hedge is <strong>one click.</strong></p>

<div class="highlight" style="border-left-color: #f59e0b;">
  <h3 style="color: #f59e0b; margin-top: 0;">🔓 Founding Member Benefits</h3>
  <ul>
    <li><strong>Priority access</strong> — First cohort, first to be protected</li>
    <li><strong>Founding member pricing</strong> — The lowest price we'll ever offer, for life</li>
    <li><strong>Your objections, our roadmap</strong> — Tell us what held you back; we'll build the solution</li>
    <li><strong>Beta Tester badge</strong> — Premium Discord + direct team access</li>
  </ul>
</div>

<h3>The cost of waiting:</h3>
<div class="highlight">
  <p>Every month without hedging, the average prop trader loses <strong>$400-800 in recoverable challenge fees.</strong></p>
  <p>You knew about hedging before you joined this waitlist. Imagine if you'd automated it a year ago — that's <strong>$4,800-9,600</strong> you'd have recovered.</p>
</div>

<p>We're opening in small batches. When it's your turn:</p>
<ol>
  <li>Download link + instant access</li>
  <li>Personal onboarding call (optional)</li>
  <li>Founding pricing locked in permanently</li>
</ol>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join the Community →</a>
</p>

<p>You already know the answer. Let Hedge Edge make it automatic.</p>

<p>— The Hedge Edge Team 🛡️</p>
""",
        },
    },
}


# ─── Segment D: Active Hedger (Manual) ──────────────────────────
# Angle: CONVENIENCE UPGRADE — "You already hedge. Do it faster."

SEGMENT_D = {
    "segment": "active_hedger",
    "segment_label": "Active Hedger (Manual)",
    "templates": {

        "welcome": {
            "subject": "🛡️ We built Hedge Edge for traders like you.",
            "delay_days": 0,
            "html": lambda name: f"""
<h2>{name}, you already hedge. We built this for you. 🎯</h2>

<p>You're one of the smart ones. You already know that hedging prop firm challenges is the right move. You've been doing it manually — and you know how painful that is.</p>

<div class="highlight">
  <strong>Sound familiar?</strong>
  <ul>
    <li>🖥️ Multiple MT5 terminals open, switching between accounts</li>
    <li>⏱️ Desperately trying to open the hedge before the prop trade moves</li>
    <li>🧮 Calculating lot sizes in your head while the market ticks</li>
    <li>😤 Missing the entry by seconds and watching the hedge lag behind</li>
    <li>🌙 Worrying about overnight positions with no automation</li>
  </ul>
</div>

<p><strong>Hedge Edge automates everything you do manually</strong> — but faster, more precise, and 24/7.</p>

<h3>Manual hedging vs. Hedge Edge:</h3>
<div class="highlight">
  <div style="text-align: center;">
    <div class="stat"><span class="stat-num">2-5s</span><span class="stat-label">Manual execution</span></div>
    <div class="stat"><span class="stat-num">&lt;100ms</span><span class="stat-label">Hedge Edge execution</span></div>
    <div class="stat"><span class="stat-num">$29/mo</span><span class="stat-label">To never click again</span></div>
  </div>
</div>

<p>You've already proven hedging works. Let us remove the friction.</p>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join Other Hedgers in Discord →</a>
</p>

<p>Tomorrow I'll break down exactly how Hedge Edge improves on your manual workflow.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day1_education": {
            "subject": "Manual hedging costs you more than you think",
            "delay_days": 1,
            "html": lambda name: f"""
<h2>{name}, let's talk about the hidden costs of manual hedging 📊</h2>

<p>You already hedge, so you know the concept works. But manual hedging has costs that automation eliminates:</p>

<h3>1. Execution slippage</h3>
<div class="highlight">
  <p>Manual hedge entry takes <strong>2-5 seconds</strong> after the prop trade. In that time, the market moves. On average, manual hedgers lose <strong>1-3 pips per trade</strong> to slippage.</p>
  <p>Hedge Edge executes locally in <strong>under 100 milliseconds</strong> — effectively zero slippage.</p>
</div>

<h3>2. Time cost</h3>
<div class="highlight">
  <p>Every trade requires you to: switch terminals → calculate lot size → place the order → verify fill → confirm matching. That's <strong>30-60 seconds per trade.</strong></p>
  <p>Multiply by 10-20 trades/day across multiple challenges. That's <strong>5-20 minutes of pure execution work</strong> that adds zero alpha.</p>
</div>

<h3>3. Error rate</h3>
<div class="highlight">
  <p>Manual hedging errors — wrong lot size, wrong direction, missed entries, forgetting to close — directly cost money. Even experienced hedgers make mistakes when rushing.</p>
  <p>Hedge Edge: <strong>zero human error.</strong> Every position is mirrored exactly.</p>
</div>

<h3>4. Emotional interference</h3>
<div class="highlight">
  <p>When you manually hedge, you <em>see</em> the hedge loss in real time. This creates psychological pressure to close the hedge early or skip it on "confident" trades — defeating the entire purpose.</p>
  <p>Automation removes the temptation. The hedge runs. Period.</p>
</div>

<p style="text-align: center;">
  <a href="{SITE_URL}/#learn" class="cta">See Hedge Edge in Action →</a>
</p>

<p>Day 3: The broker optimization for automated hedging.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day3_broker": {
            "subject": "Your hedge broker might be costing you recovery rate",
            "delay_days": 3,
            "html": lambda name: f"""
<h2>{name}, let's optimize your hedge side 🏦</h2>

<p>You already have a hedge broker. But is it optimized for what Hedge Edge does?</p>

<h3>What changes with automation:</h3>
<p>Manual hedging is forgiving of broker quality because your execution is already slow. When Hedge Edge automates at sub-100ms, <strong>broker quality becomes the bottleneck.</strong></p>

<h3>The difference broker choice makes:</h3>
<div class="highlight">
  <table style="width: 100%; color: #e5e5e5; border-collapse: collapse;">
    <tr style="border-bottom: 1px solid #333;">
      <td style="padding: 8px;"></td>
      <td style="padding: 8px; text-align: center;"><strong>Average Broker</strong></td>
      <td style="padding: 8px; text-align: center;"><strong>Hedge Edge Partner</strong></td>
    </tr>
    <tr style="border-bottom: 1px solid #333;">
      <td style="padding: 8px;">Spread (EUR/USD)</td>
      <td style="padding: 8px; text-align: center;">1.2 pips</td>
      <td style="padding: 8px; text-align: center; color: #10b981;">0.0-0.2 pips</td>
    </tr>
    <tr style="border-bottom: 1px solid #333;">
      <td style="padding: 8px;">Execution</td>
      <td style="padding: 8px; text-align: center;">200-500ms</td>
      <td style="padding: 8px; text-align: center; color: #10b981;">&lt;50ms</td>
    </tr>
    <tr>
      <td style="padding: 8px;">Recovery rate</td>
      <td style="padding: 8px; text-align: center;">70-80%</td>
      <td style="padding: 8px; text-align: center; color: #10b981;">85-95%</td>
    </tr>
  </table>
</div>

<h3>Our partner brokers:</h3>
<ul>
  <li>🥇 <strong>Vantage</strong> — Raw ECN, 0.0 pip spreads, co-located servers. Our top pick.</li>
  <li>🥈 <strong>BlackBull Markets</strong> — Institutional liquidity, NZ regulated, deep fills.</li>
</ul>

<p>You <em>can</em> keep your current broker — Hedge Edge works with any MT5 broker. But switching to a partner broker typically improves recovery rate by <strong>10-15 percentage points.</strong></p>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Compare Notes with Other Hedgers →</a>
</p>

<p>Day 5: Migrating from manual to automated — the 10-minute switch.</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day5_product": {
            "subject": "From manual hedging to automated in 10 minutes ⚡",
            "delay_days": 5,
            "html": lambda name: f"""
<h2>{name}, time to retire the manual workflow ⚡</h2>

<p>You've been doing this the hard way. Here's how fast the switch takes:</p>

<h3>Migration steps (you keep your existing setup):</h3>
<div class="highlight">
  <p><strong>Step 1</strong> (2 min) — Download Hedge Edge and log in</p>
  <p><strong>Step 2</strong> (3 min) — Connect your prop MT5 (same terminal you already use)</p>
  <p><strong>Step 3</strong> (3 min) — Connect your hedge broker MT5 (same account you already have)</p>
  <p><strong>Step 4</strong> (2 min) — Configure hedge ratio (import your existing settings)</p>
  <p>✅ <strong>Done.</strong> Same strategy. Same accounts. Zero manual work from now on.</p>
</div>

<h3>What automation gives you that manual can't:</h3>
<ul>
  <li>⚡ <strong>Sub-100ms execution</strong> vs. 2-5 seconds manual</li>
  <li>📊 <strong>Full analytics</strong> — Per-challenge P&L, hedge efficiency scoring, visual hedge map</li>
  <li>🔔 <strong>Notifications</strong> — Email alerts on hedges, drawdown warnings, position summaries</li>
  <li>🌙 <strong>24/7 operation</strong> — Hedges fire even when you're asleep or away</li>
  <li>🧮 <strong>Auto lot sizing</strong> — Dynamic calculation based on your prop position, no mental math</li>
</ul>

<h3>Pricing (less than your monthly spread cost savings):</h3>
<div class="highlight">
  <p><strong>Challenge Shield:</strong> $29/mo — 3 accounts, full automation</p>
  <p><strong>Multi-Challenge:</strong> $59/mo — 5 accounts, complete analytics</p>
  <p><strong>Unlimited:</strong> $99/mo — Unlimited accounts, all platforms, optimal sizing</p>
</div>

<p style="text-align: center;">
  <a href="{SITE_URL}" class="cta">Check Your Waitlist Status →</a>
</p>

<p>Day 7: Founding member access — something special for experienced hedgers 👀</p>

<p>— The Hedge Edge Team</p>
""",
        },

        "day7_offer": {
            "subject": "🔒 For manual hedgers: automate it + founding member perks",
            "delay_days": 7,
            "html": lambda name: f"""
<h2>{name}, you've done this the hard way long enough 👑</h2>

<p>You're a rare trader — you already understand and practice hedging. The fact that you've been doing it manually means you're both disciplined <em>and</em> frustrated.</p>

<p>We built Hedge Edge specifically to solve your frustration.</p>

<div class="highlight" style="border-left-color: #f59e0b;">
  <h3 style="color: #f59e0b; margin-top: 0;">🔓 Founding Member Benefits (Experienced Hedger Priority)</h3>
  <ul>
    <li><strong>Priority access</strong> — As an experienced hedger, your feedback is invaluable. You're first.</li>
    <li><strong>Founding member pricing</strong> — Lowest price ever, locked for life</li>
    <li><strong>Feature input</strong> — Direct line to the dev team. What do YOU need in a hedging tool?</li>
    <li><strong>Beta Tester badge</strong> — Premium Discord + advanced features early access</li>
    <li><strong>Migration support</strong> — We'll personally help you migrate from manual to automated</li>
  </ul>
</div>

<h3>What you gain by automating:</h3>
<div class="highlight">
  <ul>
    <li><strong>Time:</strong> 10-30 minutes/day of manual execution work → zero</li>
    <li><strong>Precision:</strong> 1-3 pips of slippage per trade → near zero</li>
    <li><strong>Coverage:</strong> Only trades when you're at the desk → 24/7 coverage</li>
    <li><strong>Emotional load:</strong> Managing hedge P&L manually → fully automated</li>
  </ul>
</div>

<p>When your spot opens:</p>
<ol>
  <li>Download link + experienced hedger setup guide</li>
  <li>Personal migration call (we import your settings)</li>
  <li>Founding pricing locked in permanently</li>
</ol>

<p style="text-align: center;">
  <a href="{DISCORD_INVITE}" class="cta">Join the Hedging Community →</a>
</p>

<p>Same strategy. Same edge. Zero manual work. Welcome to the upgrade.</p>

<p>— The Hedge Edge Team 🛡️</p>
""",
        },
    },
}


ALL_SEGMENTS = {
    "unsuccessful_unaware": SEGMENT_A,
    "successful_unaware": SEGMENT_B,
    "aware_not_hedging": SEGMENT_C,
    "active_hedger": SEGMENT_D,
}

# Default segment (for untagged users)
DEFAULT_SEGMENT = "unsuccessful_unaware"
