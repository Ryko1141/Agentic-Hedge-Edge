#!/usr/bin/env python3
"""
generate_voiceover.py - Content Engine BOFU Video Voiceover Generator

Generates professional voiceover audio for the Hedge Edge BOFU landing page
video using ElevenLabs text-to-speech API.

Usage:
    python generate_voiceover.py --action generate
    python generate_voiceover.py --action list-voices
    python generate_voiceover.py --action preview --voice-id <id>
    python generate_voiceover.py --action usage
"""

import sys, os, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.elevenlabs_client import (
    generate_speech, generate_long_speech, list_voices, get_subscription_info
)
from shared.notion_client import log_task

AGENT = "Content Engine"
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')

# -- BOFU Voiceover Script (pure narration text) --
BOFU_SCRIPT = """
Every prop firm trader knows the pain. You pay five hundred dollars for a challenge. You trade well. Then one bad day, one news spike, one overnight gap, and you breach the drawdown limit. Challenge failed. Money gone.

Now multiply that by three attempts. Four. Five. The average trader spends over two thousand dollars just trying to get funded.

What if every dollar you spent on a failed challenge came back to you?

That is exactly what Hedge Edge does.

When you open a trade on your prop firm account, Hedge Edge instantly opens the opposite position on your personal broker account. If the challenge fails, your hedge profits recover the fee. If the challenge passes, you keep the funded account and the profit split.

The math is simple. You are covered either way.

Here is how fast the setup takes. Step one, download Hedge Edge and log in. Step two, connect your prop firm MT5 terminal. Step three, connect your hedge broker terminal. Step four, activate hedging. That is it. Ten minutes, and every trade you take is automatically protected.

Hedge Edge runs locally on your machine. Zero latency. No cloud delays. Your trades are mirrored in under one hundred milliseconds. And it works across multiple accounts simultaneously, whether you are running two challenges or twenty.

Five hundred traders are already using Hedge Edge to protect over two million dollars in funded capital. The Starter plan is just twenty nine dollars a month. That is less than six percent of a single hundred thousand dollar challenge fee.

One payout from a funded account covers years of Hedge Edge.

Stop burning money on failed challenges. Start recovering it.

Download Hedge Edge free from the link below. Your funded accounts deserve protection.
""".strip()


def cmd_generate(args):
    """Generate the BOFU voiceover audio."""
    print("=" * 65)
    print("  BOFU VOICEOVER GENERATION")
    print("=" * 65)

    voice_id = args.voice_id or "pNInz6obpgDQGcFmaJgB"  # Adam (confident male)
    output_path = os.path.join(RESOURCES_DIR, args.output or "bofu_voiceover.mp3")

    print(f"\n  Voice ID:    {voice_id}")
    print(f"  Output:      {output_path}")
    print(f"  Script:      {len(BOFU_SCRIPT)} chars (~90 seconds)")
    print(f"  Model:       eleven_multilingual_v2")
    print(f"  Stability:   {args.stability}")
    print(f"  Similarity:  {args.similarity}")
    print(f"  Style:       {args.style}")
    print()

    # Check usage before generating
    try:
        info = get_subscription_info()
        remaining = info.get("characters_remaining", 0)
        print(f"  Characters remaining: {remaining:,}")
        if remaining < len(BOFU_SCRIPT):
            print(f"  WARNING: Script is {len(BOFU_SCRIPT)} chars but only {remaining} remaining!")
            if not args.force:
                print("  Use --force to generate anyway.")
                return
    except Exception as e:
        print(f"  Could not check usage: {e}")

    print(f"\n  Generating voiceover...")
    result_path = generate_long_speech(
        text=BOFU_SCRIPT,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_path=output_path,
        stability=args.stability,
        similarity_boost=args.similarity,
        style=args.style,
        output_format="mp3_44100_128",
    )

    file_size = os.path.getsize(result_path)
    print(f"\n  Audio saved: {result_path}")
    print(f"  File size:   {file_size / 1024:.1f} KB")
    print(f"  Format:      MP3 44.1kHz 128kbps")
    print()

    log_task(AGENT, "BOFU voiceover generated",
             "Complete", "P1",
             f"voice={voice_id}, chars={len(BOFU_SCRIPT)}, size={file_size/1024:.0f}KB")

    print("  Done! Audio ready for video production.")


def cmd_list_voices(args):
    """List available ElevenLabs voices."""
    print("=" * 65)
    print("  AVAILABLE ELEVENLABS VOICES")
    print("=" * 65)

    voices = list_voices()
    print(f"\n  Found {len(voices)} voices:\n")

    for v in voices:
        labels = v.get("labels", {})
        gender = labels.get("gender", "?")
        accent = labels.get("accent", "?")
        age = labels.get("age", "?")
        use_case = labels.get("use_case", "")
        print(f"  {v['name']:20s}  {v['voice_id']}")
        print(f"    Category: {v['category']:12s}  Gender: {gender:8s}  Accent: {accent}")
        if use_case:
            print(f"    Use case: {use_case}")
        print()


def cmd_preview(args):
    """Generate a short preview with a specific voice."""
    print("=" * 65)
    print("  VOICE PREVIEW")
    print("=" * 65)

    voice_id = args.voice_id
    if not voice_id:
        print("\n  ERROR: --voice-id required for preview")
        return

    preview_text = "Five hundred traders are already using Hedge Edge to protect over two million dollars in funded capital. Stop burning money on failed challenges. Start recovering it."
    output_path = os.path.join(RESOURCES_DIR, f"preview_{voice_id[:8]}.mp3")

    print(f"\n  Voice: {voice_id}")
    print(f"  Text:  {preview_text[:60]}...")
    print(f"  Generating preview...")

    result = generate_speech(
        text=preview_text,
        voice_id=voice_id,
        output_path=output_path,
        stability=args.stability,
        similarity_boost=args.similarity,
        style=args.style,
    )

    size = os.path.getsize(result)
    print(f"\n  Preview saved: {result} ({size/1024:.1f} KB)")


def cmd_usage(args):
    """Show ElevenLabs subscription usage."""
    print("=" * 65)
    print("  ELEVENLABS USAGE")
    print("=" * 65)

    info = get_subscription_info()
    print(f"\n  Tier:                {info['tier']}")
    print(f"  Characters used:     {info['character_count']:,}")
    print(f"  Character limit:     {info['character_limit']:,}")
    print(f"  Characters remaining:{info['characters_remaining']:,}")
    print(f"\n  BOFU script length:  {len(BOFU_SCRIPT):,} chars")

    if info['characters_remaining'] >= len(BOFU_SCRIPT):
        print(f"  Status: OK  - enough quota for voiceover generation")
    else:
        deficit = len(BOFU_SCRIPT) - info['characters_remaining']
        print(f"  Status: INSUFFICIENT - need {deficit:,} more characters")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="BOFU Voiceover Generator")
    p.add_argument("--action", required=True,
                   choices=["generate", "list-voices", "preview", "usage"])
    p.add_argument("--voice-id", default=None, help="ElevenLabs voice ID")
    p.add_argument("--output", default=None, help="Output filename")
    p.add_argument("--stability", type=float, default=0.45)
    p.add_argument("--similarity", type=float, default=0.78)
    p.add_argument("--style", type=float, default=0.15)
    p.add_argument("--force", action="store_true", help="Force generation even if low quota")

    args = p.parse_args()
    {
        "generate": cmd_generate,
        "list-voices": cmd_list_voices,
        "preview": cmd_preview,
        "usage": cmd_usage,
    }[args.action](args)
