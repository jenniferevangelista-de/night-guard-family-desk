"""The narrator character from the Night Guard videos (a night watchman), plus the paper helpers.

Copied from the Night Guard video pipeline (same author) so this repository can draw him on its own.
Fonts are read from FONTS (Windows fonts are not redistributed here).
"""
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
INK = (34, 30, 38)
PAPER = (247, 242, 230)
FONTS = Path(os.environ.get("FONTS", "video/out/fonts"))

LINE = (42, 32, 72)
FUR_K = (192, 152, 114)
FACE = (247, 234, 210)
BELLY = (244, 232, 210)
PATCH_K = (116, 84, 62)
BLUSH = (245, 150, 175, 150)
TONGUE = (240, 120, 140)
NAVY = (38, 50, 108)
NAVY_D = (26, 34, 78)
GOLD = (255, 211, 110)


@lru_cache(maxsize=32)
def font(name: str, size: int):
    return ImageFont.truetype(str(FONTS / name), size)


def dr(t: float) -> int:
    return int(t * 12)  # drawings change on twos


@lru_cache(maxsize=1)
def paper() -> Image.Image:
    rng = np.random.default_rng(3)
    a = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
    lo = rng.normal(0, 1, (H // 40, W // 40)).astype(np.float32)
    lo = np.array(Image.fromarray(((lo + 3) * 40).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 40 - 3
    a += (lo * 3 + rng.normal(0, 1, (H, W)) * 2.5)[..., None]
    y, x = np.ogrid[:H, :W]
    v = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    a *= (1 - 0.18 * np.clip(v - 0.6, 0, 1))[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def text(d, s, x, y, size, col=INK, anchor="mm", fn="segoeprb.ttf"):
    d.text((x, y), s, font=font(fn, size), fill=col, anchor=anchor)


def _rot_ellipse(cx, cy, rx, ry, ang, n=36):
    c, s_ = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(2 * math.pi * k / n) * c - ry * math.sin(2 * math.pi * k / n) * s_,
             cy + rx * math.cos(2 * math.pi * k / n) * s_ + ry * math.sin(2 * math.pi * k / n) * c) for k in range(n)]


def sloth(img, t, cx, by, h=420, m=0.0, mood="talk", wave=0.0):
    """Draw the narrator with its feet at (cx, by). m: mouth 0..1; mood: talk | listen | sleep | yawn; wave: 0..1."""
    ss = 2
    k = ss * h / 420.0
    w_, h_ = int(420 * k), int(440 * k)
    lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)

    def P(x, y):
        return (x * k, y * k)

    def B(x0, y0, x1, y1):
        return (x0 * k, y0 * k, x1 * k, y1 * k)

    lw = max(2, int(7 * k))
    bob = math.sin(dr(t) / 12 * 2.2) * 3
    d.ellipse(B(110, 418, 310, 436), fill=(0, 0, 0, 40))
    for x0 in (128, 222):
        d.ellipse(B(x0, 392, x0 + 70, 424), fill=FUR_K, outline=LINE, width=lw)
    d.polygon([P(*p) for p in _rot_ellipse(64, 292 + bob, 26, 44, math.radians(28))], fill=FUR_K, outline=LINE, width=lw)
    d.rounded_rectangle(B(34, 318 + bob, 68, 352 + bob), radius=int(6 * k), fill=(110, 112, 128), outline=LINE, width=max(2, lw // 2))
    d.polygon([P(38, 352 + bob), P(64, 352 + bob), P(84, 400 + bob), P(18, 400 + bob)], fill=(255, 238, 160, 200))
    ang = math.radians(-25 + 130 * wave + 14 * wave * math.sin(dr(t) / 12 * 6))
    ax, ay = 336, 292 + bob - 40 * wave
    d.polygon([P(*p) for p in _rot_ellipse(ax + 30 * wave, ay - 20 * wave, 26, 44, -ang)], fill=FUR_K, outline=LINE, width=lw)
    d.ellipse(B(52, 112 + bob, 348, 408), fill=FUR_K, outline=LINE, width=lw)
    d.ellipse(B(128, 300 + bob, 272, 398), fill=BELLY)
    d.ellipse(B(92, 168 + bob, 308, 312 + bob), fill=FACE)
    for sx, ex in ((-1, 152), (1, 248)):
        ey = 228 + bob
        d.polygon([P(*p) for p in _rot_ellipse(ex + sx * 4, ey + 6, 44, 30, math.radians(-sx * 28))], fill=PATCH_K)
        if mood == "sleep" or (mood != "yawn" and (t % 4.3) < 0.16):
            d.arc(B(ex - 22, ey - 8, ex + 22, ey + 18), 20, 160, fill=LINE, width=lw)
        else:
            d.ellipse(B(ex - 25, ey - 26, ex + 25, ey + 26), fill=LINE)
            d.ellipse(B(ex - 15, ey - 18, ex - 1, ey - 4), fill=(255, 255, 255))
            d.ellipse(B(ex + 6, ey + 6, ex + 14, ey + 14), fill=(255, 255, 255))
    for x0 in (102, 262):
        d.ellipse(B(x0, 262 + bob, x0 + 38, 280 + bob), fill=BLUSH)
    d.ellipse(B(188, 252 + bob, 212, 266 + bob), fill=LINE)
    my = 272 + bob
    if mood == "yawn":
        d.ellipse(B(182, my - 2, 218, my + 40), fill=LINE)
        d.ellipse(B(190, my + 20, 210, my + 36), fill=TONGUE)
    elif m > 0.06:
        o = 0.35 + 0.65 * min(1.0, m)
        d.chord(B(178, my - 8, 222, my + 34 * o), 0, 180, fill=LINE)
        d.chord(B(188, my + 4 * o, 212, my + 30 * o), 0, 180, fill=TONGUE)
    else:
        d.arc(B(182, my - 14, 218, my + 10), 20, 160, fill=LINE, width=lw)
    d.chord(B(78, 52 + bob, 322, 252 + bob), 180, 360, fill=NAVY, outline=LINE, width=lw)
    d.rounded_rectangle(B(66, 140 + bob, 346, 170 + bob), radius=int(14 * k), fill=NAVY_D, outline=LINE, width=lw)
    d.ellipse(B(178, 82 + bob, 222, 126 + bob), fill=GOLD, outline=LINE, width=max(2, lw // 2))
    d.ellipse(B(190, 78 + bob, 228, 118 + bob), fill=NAVY)
    if mood == "sleep":
        for i in range(3):
            zt = (t * 0.6 + i * 0.33) % 1
            d.text(P(330 + zt * 50, 120 - zt * 100), "z", fill=NAVY, font=font("impact.ttf", int((26 + 22 * zt) * k)), anchor="mm")
    w2, h2 = int(w_ / ss), int(h_ / ss)
    lay = lay.resize((w2, h2), Image.LANCZOS)
    img.paste(lay, (int(cx - w2 / 2), int(by - h2 * 424 / 440)), lay)
