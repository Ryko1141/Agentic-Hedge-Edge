"""
Generate and upload branded emojis for the Hedge Edge Discord server.
Creates trading/prop-firm themed custom emojis using Pillow and uploads via Discord API.
"""

import os
import io
import base64
import math
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

# Brand colors
GREEN = "#00C853"       # Hedge Edge primary green
DARK_GREEN = "#00963F"
RED = "#FF1744"
DARK_BG = "#1A1A2E"
GOLD = "#FFD700"
BLUE = "#2196F3"
WHITE = "#FFFFFF"
BLACK = "#000000"
ORANGE = "#FF9800"
PURPLE = "#9C27B0"
TEAL = "#009688"

SIZE = 128  # Discord recommended emoji size


def new_canvas(bg_color=None):
    """Create a transparent 128x128 canvas or one with a background."""
    if bg_color:
        img = Image.new("RGBA", (SIZE, SIZE), bg_color)
    else:
        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def draw_circle(draw, center, radius, fill):
    """Draw a filled circle."""
    x, y = center
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill)


def draw_rounded_rect(draw, bbox, radius, fill):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)


def to_base64(img):
    """Convert PIL Image to base64-encoded PNG string for Discord API."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"


# ─── Emoji generators ───────────────────────────────────────────────


def emoji_bull():
    """Green bull market emoji - upward arrow in green circle."""
    img, draw = new_canvas()
    draw_circle(draw, (64, 64), 58, GREEN)
    # Big up arrow
    arrow = [(64, 18), (100, 62), (78, 62), (78, 108), (50, 108), (50, 62), (28, 62)]
    draw.polygon(arrow, fill=WHITE)
    return img


def emoji_bear():
    """Red bear market emoji - downward arrow in red circle."""
    img, draw = new_canvas()
    draw_circle(draw, (64, 64), 58, RED)
    # Big down arrow
    arrow = [(64, 110), (28, 66), (50, 66), (50, 20), (78, 20), (78, 66), (100, 66)]
    draw.polygon(arrow, fill=WHITE)
    return img


def emoji_profit():
    """Dollar sign in gold circle - profit emoji."""
    img, draw = new_canvas()
    draw_circle(draw, (64, 64), 58, GOLD)
    # Draw $ sign using lines
    # Vertical bar
    draw.rectangle([58, 18, 70, 110], fill=DARK_BG)
    # Top curve
    draw.arc([34, 26, 94, 66], start=180, end=0, fill=DARK_BG, width=10)
    # Bottom curve  
    draw.arc([34, 62, 94, 102], start=0, end=180, fill=DARK_BG, width=10)
    # Top-left horizontal
    draw.rectangle([34, 36, 64, 46], fill=DARK_BG)
    # Bottom-right horizontal
    draw.rectangle([64, 82, 94, 92], fill=DARK_BG)
    return img


def emoji_shield():
    """Shield emoji - Hedge Edge Challenge Shield brand element."""
    img, draw = new_canvas()
    # Shield shape
    shield = [
        (64, 8),     # top center
        (110, 24),   # top right
        (108, 72),   # mid right
        (64, 118),   # bottom point
        (20, 72),    # mid left
        (18, 24),    # top left
    ]
    draw.polygon(shield, fill=GREEN)
    # Inner shield
    inner = [
        (64, 20),
        (98, 33),
        (96, 70),
        (64, 108),
        (32, 70),
        (30, 33),
    ]
    draw.polygon(inner, fill=DARK_BG)
    # Checkmark inside
    check = [(38, 62), (56, 82), (90, 40)]
    draw.line(check, fill=GREEN, width=10, joint="curve")
    return img


def emoji_chart_up():
    """Chart going up emoji."""
    img, draw = new_canvas()
    draw_rounded_rect(draw, [4, 4, 124, 124], 16, DARK_BG)
    # Grid lines (subtle)
    for y in [32, 56, 80, 104]:
        draw.line([(16, y), (112, y)], fill="#333355", width=1)
    # Upward trend line
    points = [(16, 100), (40, 80), (56, 88), (72, 55), (90, 42), (112, 18)]
    draw.line(points, fill=GREEN, width=6, joint="curve")
    # Dots at points
    for px, py in points:
        draw_circle(draw, (px, py), 5, GREEN)
    return img


def emoji_chart_down():
    """Chart going down emoji."""
    img, draw = new_canvas()
    draw_rounded_rect(draw, [4, 4, 124, 124], 16, DARK_BG)
    for y in [32, 56, 80, 104]:
        draw.line([(16, y), (112, y)], fill="#333355", width=1)
    points = [(16, 20), (40, 38), (56, 32), (72, 65), (90, 80), (112, 104)]
    draw.line(points, fill=RED, width=6, joint="curve")
    for px, py in points:
        draw_circle(draw, (px, py), 5, RED)
    return img


def emoji_fire():
    """Fire/hot streak emoji."""
    img, draw = new_canvas()
    # Outer flame (orange)
    flame_outer = [
        (64, 6),
        (90, 34), (98, 56), (100, 78),
        (96, 100), (80, 118), (64, 122),
        (48, 118), (32, 100),
        (28, 78), (30, 56), (38, 34),
    ]
    draw.polygon(flame_outer, fill=ORANGE)
    # Inner flame (yellow)
    flame_inner = [
        (64, 36),
        (80, 56), (84, 72), (82, 92),
        (74, 108), (64, 112),
        (54, 108), (46, 92),
        (44, 72), (48, 56),
    ]
    draw.polygon(flame_inner, fill=GOLD)
    # Core (white-ish)
    flame_core = [
        (64, 66),
        (72, 80), (72, 96),
        (64, 104),
        (56, 96), (56, 80),
    ]
    draw.polygon(flame_core, fill="#FFF9C4")
    return img


def emoji_target():
    """Target/goal emoji."""
    img, draw = new_canvas()
    draw_circle(draw, (64, 64), 56, RED)
    draw_circle(draw, (64, 64), 44, WHITE)
    draw_circle(draw, (64, 64), 32, RED)
    draw_circle(draw, (64, 64), 20, WHITE)
    draw_circle(draw, (64, 64), 10, RED)
    return img


def emoji_rocket():
    """Rocket emoji for launches/gains."""
    img, draw = new_canvas()
    # Rocket body
    body = [
        (64, 8),     # nose
        (82, 44),    # right upper
        (82, 94),    # right lower
        (46, 94),    # left lower
        (46, 44),    # left upper
    ]
    draw.polygon(body, fill=WHITE)
    # Nose cone
    nose = [(64, 8), (78, 40), (50, 40)]
    draw.polygon(nose, fill=RED)
    # Window
    draw_circle(draw, (64, 58), 10, BLUE)
    draw_circle(draw, (64, 58), 6, "#90CAF9")
    # Left fin
    fin_l = [(46, 78), (22, 104), (46, 100)]
    draw.polygon(fin_l, fill=RED)
    # Right fin
    fin_r = [(82, 78), (106, 104), (82, 100)]
    draw.polygon(fin_r, fill=RED)
    # Exhaust flame
    exhaust = [(52, 94), (64, 122), (76, 94)]
    draw.polygon(exhaust, fill=ORANGE)
    exhaust_inner = [(56, 94), (64, 114), (72, 94)]
    draw.polygon(exhaust_inner, fill=GOLD)
    return img


def emoji_diamond():
    """Diamond hands / premium emoji."""
    img, draw = new_canvas()
    # Diamond shape
    top = [(64, 8), (108, 44), (64, 120), (20, 44)]
    draw.polygon(top, fill=BLUE)
    # Facets - top
    draw.polygon([(64, 8), (40, 44), (88, 44)], fill="#64B5F6")
    # Left facet
    draw.polygon([(20, 44), (40, 44), (64, 120)], fill="#1976D2")
    # Right facet
    draw.polygon([(108, 44), (88, 44), (64, 120)], fill="#1565C0")
    # Top center
    draw.polygon([(40, 44), (88, 44), (64, 120)], fill="#2196F3")
    # Highlight
    draw.polygon([(64, 8), (40, 44), (64, 44)], fill="#90CAF9")
    return img


def emoji_crown():
    """Crown for top traders/VIP."""
    img, draw = new_canvas()
    # Crown base
    draw.rectangle([20, 72, 108, 108], fill=GOLD)
    # Crown points
    points_crown = [
        (20, 72), (20, 28),     # left
        (44, 52),               # valley 1
        (64, 20),               # center peak
        (84, 52),               # valley 2
        (108, 28), (108, 72),   # right
    ]
    draw.polygon(points_crown, fill=GOLD)
    # Gems
    draw_circle(draw, (64, 50), 7, RED)
    draw_circle(draw, (34, 50), 6, BLUE)
    draw_circle(draw, (94, 50), 6, BLUE)
    # Base line detail
    draw.rectangle([20, 72, 108, 80], fill="#FFC107")
    # Gem on base
    draw_circle(draw, (64, 90), 6, RED)
    draw_circle(draw, (40, 90), 5, GREEN)
    draw_circle(draw, (88, 90), 5, GREEN)
    return img


def emoji_verified():
    """Green verified checkmark badge."""
    img, draw = new_canvas()
    # Star/badge shape using circle
    draw_circle(draw, (64, 64), 56, GREEN)
    # White checkmark
    check = [(32, 64), (54, 88), (98, 38)]
    draw.line(check, fill=WHITE, width=14, joint="curve")
    return img


def emoji_alert():
    """Alert / warning triangle."""
    img, draw = new_canvas()
    # Triangle
    triangle = [(64, 10), (118, 114), (10, 114)]
    draw.polygon(triangle, fill=GOLD)
    # Inner triangle (slightly smaller, darker)
    inner = [(64, 28), (106, 108), (22, 108)]
    draw.polygon(inner, fill="#FFF8E1")
    # Exclamation mark
    draw.rectangle([58, 44, 70, 82], fill=DARK_BG)
    draw_circle(draw, (64, 96), 7, DARK_BG)
    return img


def emoji_buy():
    """Green BUY signal."""
    img, draw = new_canvas()
    draw_rounded_rect(draw, [4, 24, 124, 104], 16, GREEN)
    # "BUY" text - draw manually
    # B
    draw.rectangle([16, 40, 23, 88], fill=WHITE)
    draw.arc([17, 40, 40, 63], 270, 90, fill=WHITE, width=4)
    draw.arc([17, 64, 42, 88], 270, 90, fill=WHITE, width=4)
    # U
    draw.rectangle([46, 40, 53, 80], fill=WHITE)
    draw.rectangle([66, 40, 73, 80], fill=WHITE)
    draw.arc([46, 70, 73, 92], 0, 180, fill=WHITE, width=4)
    # Y
    draw.line([(80, 40), (92, 62)], fill=WHITE, width=5)
    draw.line([(104, 40), (92, 62)], fill=WHITE, width=5)
    draw.rectangle([89, 62, 95, 88], fill=WHITE)
    return img


def emoji_sell():
    """Red SELL signal."""
    img, draw = new_canvas()
    draw_rounded_rect(draw, [4, 24, 124, 104], 16, RED)
    # Simple approach: just draw geometric SELL
    # S - two arcs
    draw.arc([10, 36, 34, 60], 180, 0, fill=WHITE, width=5)
    draw.arc([10, 58, 34, 84], 0, 180, fill=WHITE, width=5)
    # E
    draw.rectangle([40, 38, 47, 86], fill=WHITE)
    draw.rectangle([40, 38, 60, 44], fill=WHITE)
    draw.rectangle([40, 58, 58, 64], fill=WHITE)
    draw.rectangle([40, 80, 60, 86], fill=WHITE)
    # L
    draw.rectangle([66, 38, 73, 86], fill=WHITE)
    draw.rectangle([66, 80, 86, 86], fill=WHITE)
    # L
    draw.rectangle([92, 38, 99, 86], fill=WHITE)
    draw.rectangle([92, 80, 112, 86], fill=WHITE)
    return img


def emoji_hedge():
    """Hedge Edge "HE" brand mark."""
    img, draw = new_canvas()
    # Green gradient background circle
    draw_circle(draw, (64, 64), 60, GREEN)
    draw_circle(draw, (64, 64), 52, DARK_BG)
    # "HE" letters
    # H
    draw.rectangle([28, 36, 36, 92], fill=GREEN)
    draw.rectangle([52, 36, 60, 92], fill=GREEN)
    draw.rectangle([28, 58, 60, 68], fill=GREEN)
    # E
    draw.rectangle([68, 36, 76, 92], fill=GREEN)
    draw.rectangle([68, 36, 98, 44], fill=GREEN)
    draw.rectangle([68, 58, 94, 66], fill=GREEN)
    draw.rectangle([68, 84, 98, 92], fill=GREEN)
    return img


def emoji_star():
    """Gold star for ratings/reviews."""
    img, draw = new_canvas()
    # 5-pointed star
    points = []
    for i in range(5):
        # Outer point
        angle = math.radians(-90 + i * 72)
        points.append((64 + 56 * math.cos(angle), 64 + 56 * math.sin(angle)))
        # Inner point
        angle = math.radians(-90 + i * 72 + 36)
        points.append((64 + 24 * math.cos(angle), 64 + 24 * math.sin(angle)))
    draw.polygon(points, fill=GOLD)
    return img


def emoji_lock():
    """Lock/security emoji for protected content."""
    img, draw = new_canvas()
    # Lock body
    draw_rounded_rect(draw, [24, 56, 104, 116], 12, GREEN)
    # Shackle
    draw.arc([38, 14, 90, 66], 180, 0, fill=GREEN, width=12)
    # Keyhole
    draw_circle(draw, (64, 80), 10, DARK_BG)
    draw.polygon([(58, 84), (70, 84), (64, 104)], fill=DARK_BG)
    return img


def emoji_handshake():
    """Partnership/welcome hand icon."""
    img, draw = new_canvas()
    draw_circle(draw, (64, 64), 58, TEAL)
    # Simplified handshake - two overlapping hand shapes
    # Left hand
    draw.rounded_rectangle([18, 50, 66, 70], radius=6, fill=WHITE)
    draw.rounded_rectangle([18, 56, 44, 90], radius=8, fill=WHITE)
    # Right hand
    draw.rounded_rectangle([62, 50, 110, 70], radius=6, fill=WHITE)
    draw.rounded_rectangle([84, 56, 110, 90], radius=8, fill=WHITE)
    # Clasp in middle
    draw_circle(draw, (64, 60), 14, "#E0F2F1")
    draw_circle(draw, (64, 60), 8, TEAL)
    return img


def emoji_100():
    """100% / perfect score emoji."""
    img, draw = new_canvas()
    draw_rounded_rect(draw, [4, 20, 124, 108], 16, RED)
    # "100" - simplified
    # 1
    draw.rectangle([16, 38, 24, 92], fill=WHITE)
    draw.polygon([(16, 46), (16, 38), (28, 38)], fill=WHITE)
    # First 0
    draw.ellipse([30, 38, 66, 92], fill=WHITE)
    draw.ellipse([38, 46, 58, 84], fill=RED)
    # Second 0
    draw.ellipse([72, 38, 108, 92], fill=WHITE)
    draw.ellipse([80, 46, 100, 84], fill=RED)
    return img


def emoji_eyes():
    """Eyes watching / DD emoji."""
    img, draw = new_canvas()
    # Left eye
    draw.ellipse([8, 32, 60, 96], fill=WHITE)
    draw_circle(draw, (38, 64), 16, DARK_BG)
    draw_circle(draw, (38, 64), 8, "#333366")
    draw_circle(draw, (32, 56), 4, WHITE)  # highlight
    # Right eye
    draw.ellipse([68, 32, 120, 96], fill=WHITE)
    draw_circle(draw, (98, 64), 16, DARK_BG)
    draw_circle(draw, (98, 64), 8, "#333366")
    draw_circle(draw, (92, 56), 4, WHITE)  # highlight
    return img


# ─── Emoji registry ────────────────────────────────────────────────

EMOJIS = {
    "he_bull":      ("Bull market / pump", emoji_bull),
    "he_bear":      ("Bear market / dump", emoji_bear),
    "he_profit":    ("Profit / money", emoji_profit),
    "he_shield":    ("Challenge Shield brand", emoji_shield),
    "he_chartup":   ("Chart going up", emoji_chart_up),
    "he_chartdown": ("Chart going down", emoji_chart_down),
    "he_fire":      ("Hot streak / fire", emoji_fire),
    "he_target":    ("Target / goal hit", emoji_target),
    "he_rocket":    ("Rocket / to the moon", emoji_rocket),
    "he_diamond":   ("Diamond / premium", emoji_diamond),
    "he_crown":     ("Crown / top trader", emoji_crown),
    "he_verified":  ("Verified checkmark", emoji_verified),
    "he_alert":     ("Alert / warning", emoji_alert),
    "he_buy":       ("BUY signal", emoji_buy),
    "he_sell":      ("SELL signal", emoji_sell),
    "he_hedge":     ("Hedge Edge logo mark", emoji_hedge),
    "he_star":      ("Gold star / rating", emoji_star),
    "he_lock":      ("Locked / premium only", emoji_lock),
    "he_welcome":   ("Welcome / partnership", emoji_handshake),
    "he_100":       ("100 / perfect", emoji_100),
    "he_eyes":      ("Eyes / watching / DD", emoji_eyes),
}


def upload_emoji(name, image):
    """Upload a single emoji to the Discord guild."""
    data = {"name": name, "image": to_base64(image)}
    r = requests.post(
        f"https://discord.com/api/v10/guilds/{GUILD_ID}/emojis",
        headers=HEADERS,
        json=data,
        timeout=15,
    )
    return r.status_code, r.json()


def main():
    print(f"Generating and uploading {len(EMOJIS)} custom emojis to Hedge Edge Discord...\n")

    success = 0
    failed = 0

    for name, (desc, gen_func) in EMOJIS.items():
        img = gen_func()
        status, resp = upload_emoji(name, img)
        if status in (200, 201):
            emoji_id = resp.get("id", "?")
            print(f"  ✅ :{name}: — {desc} (ID: {emoji_id})")
            success += 1
        else:
            err = resp.get("message", resp)
            print(f"  ❌ :{name}: — {desc} — Error: {err}")
            failed += 1

    print(f"\nDone! {success}/{len(EMOJIS)} uploaded successfully, {failed} failed.")


if __name__ == "__main__":
    main()
