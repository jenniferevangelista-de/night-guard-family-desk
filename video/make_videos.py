"""The two Night Guard Family Desk videos.

1. The film: why the desk exists and how it works, over the app's own screens.
2. The tour: a real recording of the running app (Playwright + Chromium), narrated.

python video/make_videos.py BASE_URL OUT_DIR [film|tour|both]   (the app must be running)
Needs: ffmpeg, edge-tts, Pillow, numpy, playwright. The tour runs before the film,
because the film reuses the screenshots the tour takes.

Narration: edge-tts en-US-AvaMultilingualNeural, first person (the author).
Music: an original bed made in code, then "Funkorama" by Kevin MacLeod
(incompetech.com), CC BY 4.0, read from video/music/Funkorama.mp3 when present.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "video/out")
WORK = OUT / "work"
SHOTS = OUT / "screens"
W, H, FPS, SR = 1920, 1080, 24, 24000
VW, VH = 1600, 900  # browser viewport for the tour, scaled to 1080p
VOICE = "en-US-AvaMultilingualNeural"
MUSIC = ROOT / "video" / "music" / "Funkorama.mp3"

INK = (233, 236, 255)
SOFT = (176, 182, 222)
MOON = (255, 214, 120)
TEAL = (126, 224, 200)
AMBER = (255, 191, 92)


# ------------------------------------------------------------------ small helpers


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def pcm(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def say(text: str, name: str) -> np.ndarray:
    p = WORK / "voice" / f"{name}.mp3"
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = p.with_suffix(".txt")
    if not p.exists() or not stamp.exists() or stamp.read_text(encoding="utf-8") != text:
        run("edge-tts", "--voice", VOICE, "--rate=+2%", "--text", text, "--write-media", str(p))
        stamp.write_text(text, encoding="utf-8")
    return pcm(p)


def write_wav(x: np.ndarray, path: Path):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def srt(cues: list[tuple[float, float, str]], path: Path):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    path.write_text("\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")


def split_cue(text: str, seconds: float) -> list[tuple[float, float, str]]:
    """One-line subtitles of at most ~62 characters, timed by their share of the line."""
    parts, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > 62 and cur:
            parts.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    parts.append(cur)
    total = sum(len(p) for p in parts)
    out, a = [], 0.0
    for p in parts:
        b = a + seconds * len(p) / total
        out.append((a, b, p))
        a = b
    return out


# one handwritten line in a light box at the bottom, like the Night Guard film
SUB_STYLE = "FontName=Kalam,FontSize=13,PrimaryColour=&H00301824,OutlineColour=&H00F7F5F2,BorderStyle=3,Outline=1.6,Shadow=0,MarginV=12"


# ------------------------------------------------------------------ the score and the effects

RNG = np.random.default_rng(31)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _lpf(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


SFX = {
    "pop": lambda: (lambda t: np.sin(2 * np.pi * (700 + 900 * t) * t) * np.exp(-t * 28) * 0.5)(_t(.18)),
    "chime": lambda f0=1320: (lambda t: sum(np.sin(2 * np.pi * f0 * m * t) / m for m in (1, 2, 3)) * np.exp(-t * 5) * 0.25)(_t(.6)),
    "alert": lambda: (lambda t: (np.sin(2 * np.pi * 880 * t) * (t < .12) + np.sin(2 * np.pi * 660 * t) * ((t > .16) & (t < .3))) * 0.35)(_t(.34)),
    "swish": lambda: (lambda t: _lpf(RNG.normal(0, 1, len(t)), 2) * np.sin(np.pi * t / .3) ** 2 * 0.3)(_t(.3)),
}


def night_bed(seconds: float) -> np.ndarray:
    """An original, quiet minor bed: soft pad on A minor - F - D minor - E, a slow heartbeat, a few music-box notes."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (146.83, 174.61, 220.0), (164.81, 207.65, 246.94)]
    x = np.zeros(n)
    for i, st in enumerate(np.arange(0, seconds, 4.0)):
        a, b = int(st * SR), min(n, int((st + 4.4) * SR))
        tt = np.arange(b - a) / SR
        env = np.minimum(1, tt / 1.2) * np.minimum(1, (4.4 - tt) / 1.2)
        for f in chords[i % 4]:
            x[a:b] += np.sin(2 * np.pi * f * tt + .3 * np.sin(2 * np.pi * .2 * tt)) * env * .22
    for st in np.arange(2.0, seconds, 2.6):
        for off, g in ((0, 1.0), (.24, .65)):
            a = int((st + off) * SR)
            m = min(int(.25 * SR), n - a)
            if m > 0:
                tt = np.arange(m) / SR
                x[a:a + m] += np.sin(2 * np.pi * (58 - 18 * tt) * tt) * np.exp(-tt * 16) * g * .5
    notes = [659.25, 523.25, 440.0, 493.88]
    for k, st in enumerate(np.arange(1.5, seconds, 3.1)):
        a = int(st * SR)
        m = min(int(1.6 * SR), n - a)
        if m > 0:
            tt = np.arange(m) / SR
            x[a:a + m] += np.sin(2 * np.pi * notes[k % 4] * tt) * np.exp(-tt * 3) * .12
    x *= np.minimum(1, t / 2.5) * np.minimum(1, (seconds - t) / 2.5)
    return (x / (np.abs(x).max() or 1)).astype(np.float32)


def funk(n: int) -> np.ndarray:
    if not MUSIC.exists():
        return night_bed(n / SR)[:n] * .7
    x = pcm(MUSIC)
    reps = int(np.ceil(n / len(x)))
    return np.tile(x, reps)[:n]


def score(n: int, voice: np.ndarray, switch: float | None, events) -> np.ndarray:
    """Quiet bed first, then Funkorama from `switch`, ducked under the voice; plus the effects."""
    t = np.arange(n) / SR
    bed = night_bed(n / SR)[:n] * .9
    up = funk(n) * .55
    if switch is None:
        mix = up * np.minimum(1, t / 2.0)
    else:
        x = np.clip((t - switch) / 2.5, 0, 1)
        mix = bed * (1 - x) + up * x
    mix *= np.minimum(1, (n / SR - t) / 2.5)
    a = np.abs(np.pad(voice, (0, max(0, n - len(voice))))[:n]).astype(np.float64)
    k = int(SR * .25)
    c = np.concatenate([[0.0], np.cumsum(a)])
    env = (c[np.minimum(np.arange(n) + k, n)] - c[np.maximum(np.arange(n) - k, 0)]) / (2 * k) * 6
    mix = mix * .16 * (1 - .6 * np.clip(env, 0, 1))
    fx = np.zeros(n, np.float32)
    for at, kind, gain, *arg in events:
        clip = SFX[kind](*arg) * gain
        i = int(at * SR)
        seg = clip[: max(0, n - i)]
        fx[i:i + len(seg)] += seg
    return (mix + fx).astype(np.float32)


# ------------------------------------------------------------------ drawing


def get_fonts():
    for fname, url in (("Fredoka.ttf", "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf"),
                       ("Kalam-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/kalam/Kalam-Regular.ttf"),
                       ("Inter.ttf", "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf")):
        p = WORK / fname
        if not p.exists():
            try:
                urllib.request.urlretrieve(url, p)
            except Exception:  # noqa: BLE001
                pass


def font(name: str, size: int, weight: int | None = None):
    for p in (WORK / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        try:
            f = ImageFont.truetype(str(p), size)
            if weight is not None:
                try:
                    f.set_variation_by_axes([weight] if name != "Fredoka.ttf" else [100, weight])
                except Exception:  # noqa: BLE001
                    pass
            return f
        except OSError:
            continue
    return ImageFont.load_default()


def title_font(size):
    return font("Fredoka.ttf", size, 600)


def body_font(size, weight=450):
    return font("Inter.ttf", size, weight)


def backdrop() -> Image.Image:
    """Night sky in the app's indigo, a crescent moon and a few stars."""
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    top, bottom = np.array([30, 27, 75]), np.array([11, 12, 30])
    a = top * (1 - y) + bottom * y + np.array([18, 10, 30]) * np.exp(-((x - .85) ** 2 + (y - .1) ** 2) / .05)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    for _ in range(140):
        px, py = int(rng.integers(0, W)), int(rng.integers(0, H))
        r = rng.choice([1, 1, 1, 2])
        g = int(rng.integers(150, 255))
        d.ellipse([px - r, py - r, px + r, py + r], fill=(g, g, 255, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([1660, 40, 1840, 220], fill=(255, 214, 120, 70))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(img)
    d.ellipse([1700, 80, 1800, 180], fill=MOON)
    d.ellipse([1728, 66, 1828, 166], fill=(29, 25, 70))
    return img


def wrap(text: str, f, width: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if f.getlength(test) > width and cur:
            out.append(cur)
            cur = w
        else:
            cur = test
    return out + ([cur] if cur else [])


def rounded(img: Image.Image, r: int = 22) -> Image.Image:
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(m)
    return out


def paste_shot(img: Image.Image, shot: Path, box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    s = Image.open(shot).convert("RGB")
    s.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
    s = rounded(s, 20)
    x, y = x0 + (x1 - x0 - s.width) // 2, y0 + (y1 - y0 - s.height) // 2
    shadow = Image.new("RGBA", (s.width + 60, s.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([30, 30, s.width + 30, s.height + 30], 22, fill=(0, 0, 0, 170))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)), (x - 30, y - 18))
    ImageDraw.Draw(img).rounded_rectangle([x - 3, y - 3, x + s.width + 2, y + s.height + 2], 22, outline=(120, 110, 220, 255), width=3)
    img.alpha_composite(s, (x, y))


def frame_title(line: str, sub: str) -> Image.Image:
    img = backdrop()
    d = ImageDraw.Draw(img)
    d.text((W // 2, 360), "Night Guard", font=title_font(96), fill=SOFT, anchor="mm")
    d.text((W // 2, 480), "Family Desk", font=title_font(170), fill=INK, anchor="mm")
    d.text((W // 2, 640), line, font=body_font(46, 500), fill=MOON, anchor="mm")
    d.text((W // 2, 990), sub, font=body_font(28), fill=SOFT, anchor="mm")
    return img.convert("RGB")


def frame_statement(big: str, small: str) -> Image.Image:
    img = backdrop()
    d = ImageDraw.Draw(img)
    f = title_font(92)
    lines = wrap(big, f, 1500)
    y = 470 - (len(lines) - 1) * 55
    for ln in lines:
        d.text((W // 2, y), ln, font=f, fill=INK, anchor="mm")
        y += 110
    d.text((W // 2, y + 40), small, font=body_font(38), fill=SOFT, anchor="mm")
    return img.convert("RGB")


def frame_three(title: str, items: list[tuple[str, str]], foot: str) -> Image.Image:
    """Three cards: what Night Guard shares. A crossed-out fourth: the full chat."""
    img = backdrop()
    d = ImageDraw.Draw(img)
    d.text((W // 2, 200), title, font=title_font(78), fill=INK, anchor="mm")
    for i, (head, body) in enumerate(items):
        x0 = 150 + i * 420
        d.rounded_rectangle([x0, 330, x0 + 380, 650], 28, fill=(43, 39, 104), outline=(110, 100, 210), width=3)
        d.text((x0 + 190, 420), head, font=title_font(54), fill=TEAL, anchor="mm")
        y = 500
        for ln in wrap(body, body_font(30), 330):
            d.text((x0 + 190, y), ln, font=body_font(30), fill=INK, anchor="mm")
            y += 42
    x0 = 150 + 3 * 420
    d.rounded_rectangle([x0, 330, x0 + 380, 650], 28, fill=(40, 24, 40), outline=(220, 90, 110), width=3)
    d.text((x0 + 190, 450), "The full chat", font=title_font(50), fill=(255, 150, 160), anchor="mm")
    d.text((x0 + 190, 540), "stays on the child's computer", font=body_font(27), fill=(255, 200, 205), anchor="mm")
    d.line([x0 + 40, 360, x0 + 340, 620], fill=(230, 90, 110), width=7)
    d.text((W // 2, 800), foot, font=body_font(40, 500), fill=MOON, anchor="mm")
    return img.convert("RGB")


def frame_shot(shot: str, title: str, caption: str) -> Image.Image:
    img = backdrop()
    d = ImageDraw.Draw(img)
    d.text((110, 110), title, font=title_font(66), fill=INK, anchor="lm")
    d.text((112, 172), caption, font=body_font(32), fill=SOFT, anchor="lm")
    path = SHOTS / shot
    if path.exists():
        paste_shot(img, path, (110, 230, 1810, 1010))
    return img.convert("RGB")


def frame_cards(title: str, rows: list[tuple[str, str]]) -> Image.Image:
    img = backdrop()
    d = ImageDraw.Draw(img)
    d.text((W // 2, 150), title, font=title_font(76), fill=INK, anchor="mm")
    for i, (head, body) in enumerate(rows):
        col, row = i % 2, i // 2
        x0, y0 = 160 + col * 820, 260 + row * 165
        d.rounded_rectangle([x0, y0, x0 + 780, y0 + 140], 24, fill=(43, 39, 104), outline=(110, 100, 210), width=3)
        d.text((x0 + 34, y0 + 46), head, font=title_font(42), fill=TEAL, anchor="lm")
        d.text((x0 + 34, y0 + 98), body, font=body_font(28), fill=INK, anchor="lm")
    return img.convert("RGB")


# ------------------------------------------------------------------ 1. the film

FILM = [
    ("title", ("When the alert comes, you are not alone.", "A desk where a parent and an AI agent work the same case"),
     "When the alert comes at nine at night, what do you do next? This is Night Guard Family Desk."),
    ("three", ("Last month: Night Guard", [("Risk", "grooming, bullying, scams, self-harm"), ("App", "Roblox, Discord, any chat"),
                                         ("One phrase", "the line that raised the flag")],
               "The family sees the risk. Never the whole chat."),
     "Last month I built Night Guard. It runs Gemma on the child's own computer and watches for grooming, bullying and scams. "
     "It tells the family only three things: the risk, the app, and the one phrase that raised the flag. The full chat never leaves the child's computer."),
    ("statement", ("A warning is not a plan.", "Talk? Block? Report? Keep evidence? In what order?"),
     "But a warning is not a plan. A parent who gets that alert has to decide, fast and scared, how to talk, what to keep, and where to report."),
    ("shot", ("desk-alert.png", "One alert, one case", "Night Guard's alert opens a shared case record"),
     "So I built the other half. Every Night Guard alert opens a case. The parent and the agent work on the same record, and the privacy line is printed on it."),
    ("shot", ("desk-plan.png", "The agent proposes", "Calm talk, evidence, block, report, follow-up"),
     "The agent reads the case and proposes a plan. A calm conversation without blame. What to save before blocking. Where to report: SaferNet in Brazil, or the NCMEC CyberTipline."),
    ("shot", ("desk-approved.png", "The parent decides", "Approve, edit, skip, mark done"),
     "Then the parent decides. Every step waits for approval. I can edit it, skip it, or mark it done. The agent cannot approve anything for me, because the framework keeps those buttons for people only."),
    ("shot", ("desk-drafts.png", "Words for the hard part", "Talk script, report text, case summary"),
     "The agent also writes the hard words: the script to open the conversation, the text for the report, and the case summary. I edit them, then I approve them."),
    ("shot", ("privacy-refused.png", "Privacy is a rule, not a promise", "A payload with the full chat is refused"),
     "And privacy is enforced, not promised. If anything tries to send the whole chat to the desk, the desk refuses it."),
    ("cards", ("How it is built", [("Agent-Native", "one set of actions for UI and agent"),
                                  ("uiOnly", "approvals belong to the parent"),
                                  ("needsApproval", "the agent asks before closing"),
                                  ("Gemma 4 E2B", "local, through Ollama, US$ 0"),
                                  ("Postgres", "cases, steps, drafts, one log"),
                                  ("Live sync", "the screen updates as the agent works")]),
     "Under the hood, it is built with Agent-Native. The screen and the agent call the same actions, so the rules hold for both. "
     "Approvals are UI only, closing a case needs a human yes, and the agent runs on Gemma 4 through Ollama, with no paid API."),
    ("title", ("The family sees the risk. Never the whole chat.", "github.com/jenniferevangelista-de/night-guard-family-desk"),
     "The family sees the risk, never the whole chat. And now, they also know what to do next."),
]


def make_film():
    get_fonts()
    clips, cues, voice_track, t, starts = [], [], [], 0.0, []
    for i, (kind, args, text) in enumerate(FILM):
        frame = {"title": frame_title, "statement": frame_statement, "three": frame_three,
                 "shot": frame_shot, "cards": frame_cards}[kind](*args)
        png = WORK / f"film_{i:02d}.png"
        frame.save(png)
        clip = say(text, f"film_{i:02d}")
        start = t + .5
        cues += [(start + a, start + b, s) for a, b, s in split_cue(text, len(clip) / SR)]
        seg = np.concatenate([np.zeros(int(.5 * SR), np.float32), clip, np.zeros(int(.9 * SR), np.float32)])
        n = int(np.ceil(len(seg) / SR * FPS))
        seg = np.pad(seg, (0, n * SR // FPS - len(seg)))
        voice_track.append(seg)
        dur = n / FPS
        mp4 = WORK / f"film_{i:02d}.mp4"
        run("ffmpeg", "-y", "-loop", "1", "-i", str(png), "-vf",
            f"scale=2880:-2,zoompan=z='min(zoom+0.0003,1.045)':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(dur - .4, 0):.2f}:d=0.4",
            "-frames:v", str(n), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast", str(mp4))
        clips.append(mp4)
        starts.append((t, kind))
        t += dur
        print(f"film scene {i}: {dur:.1f}s", flush=True)
    events, switch = [], None
    for st, kind in starts:
        if kind == "title":
            events += [(st + .3, "chime", .8, 1320), (st + .45, "chime", .8, 1760)]
        elif kind == "three":
            events += [(st + .4, "alert", .8)]
        elif kind in ("shot", "cards"):
            events += [(st + .2, "swish", .7)]
        if kind == "shot" and switch is None:
            switch = st
    finish("family_desk_film", clips, np.concatenate(voice_track), cues, switch, events)


def finish(name: str, clips: list[Path], voice: np.ndarray, cues, switch=None, events=()):
    lst = WORK / f"{name}.txt"
    lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
    silent = WORK / f"{name}_silent.mp4"
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent))
    mix_and_mux(name, silent, voice, cues, switch, events)


def mix_and_mux(name: str, video: Path, voice: np.ndarray, cues, switch: float | None = None, events=()):
    vdur = duration(video)
    n = int(vdur * SR)
    voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    wav = WORK / f"{name}.wav"
    write_wav(voice * .9 + score(n, voice, switch, events), wav)
    sub = OUT / f"{name}.srt"
    srt(cues, sub)
    out = OUT / f"{name}.mp4"
    get_fonts()
    subpath = sub.resolve().as_posix().replace(":", r"\:")
    fontdir = WORK.resolve().as_posix().replace(":", r"\:")
    run("ffmpeg", "-y", "-i", str(video), "-i", str(wav), "-vf", f"subtitles='{subpath}':fontsdir='{fontdir}':force_style='{SUB_STYLE}'",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out))
    print(f"{out}: {duration(out):.1f}s", flush=True)


# ------------------------------------------------------------------ 2. the tour

CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;z-index:99999;width:22px;height:22px;border-radius:50%;pointer-events:none;' +
    'background:rgba(255,214,120,.92);box-shadow:0 0 0 5px rgba(255,214,120,.35);left:-50px;top:-50px;transition:transform .1s';
  const add = () => document.body && !c.isConnected && document.body.appendChild(c);
  document.addEventListener('mousemove', (e) => { add(); c.style.left = (e.clientX - 11) + 'px'; c.style.top = (e.clientY - 11) + 'px'; }, true);
  document.addEventListener('mousedown', () => { c.style.transform = 'scale(.7)'; }, true);
  document.addEventListener('mouseup', () => { c.style.transform = ''; }, true);
})();
"""

TOUR = {
    "open": "This is Family Desk, running for real. I'm Jennifer. On the left, the cases. Each one starts from a Night Guard alert, with fictional data only.",
    "leak": "First, the rule I care about most. Here I try to send the desk a full chat, the way a careless integration might. It is refused.",
    "alert": "Now a real-looking alert: Lia, eleven, on Roblox. Possible grooming. The desk shows the risk, the app and one phrase. Nothing more.",
    "ask": "I ask the agent for a plan. It runs on Gemma 4, a small open model, on a four-core CPU with no paid API.",
    "wait": "This part is sped up. The agent reads the case through the same actions the screen uses, and writes each step into the shared record.",
    "plan": "Here is the plan. A calm talk, the evidence to keep, blocking, reporting, a follow-up. Every step waits for me.",
    "edit": "I can change any step in my own words, then approve it. If the agent ever edits a step I approved, it comes back to me.",
    "approve": "I approve the rest, and mark the first conversation as done once it has happened.",
    "draft": "Now I ask for the words: a script to open the conversation without blame.",
    "script": "The draft lands in the same case. I read it, adjust a line, save, and approve it.",
    "log": "Everything either of us did is in the case log, marked parent, agent or Night Guard.",
    "close": "When every step is reviewed, I close the case with a short note.",
    "end": "The family sees the risk, never the whole chat. And now they know what to do next. Thank you for watching.",
}

SPEED_LABEL = "Gemma 4 E2B on CPU · sped up"


def make_tour():
    from playwright.sync_api import sync_playwright

    get_fonts()
    lines = {k: (say(v, f"tour_{k}"), v) for k, v in TOUR.items()}
    marks: list[tuple[float, str]] = []
    waits: list[tuple[float, float]] = []
    rec = WORK / "rec"
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": VW, "height": VH}, record_video_dir=str(rec),
                                  record_video_size={"width": VW, "height": VH}, color_scheme="dark")
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        page.set_default_timeout(60000)
        page.goto(BASE + "/cases", wait_until="networkidle", timeout=600000)
        t0 = time.monotonic()
        now = lambda: time.monotonic() - t0  # noqa: E731

        def glide(loc, click=False):
            loc = loc.first
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            box = loc.bounding_box()
            if box:
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=20)
                page.wait_for_timeout(150)
                if click:
                    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        def shot(name):
            try:
                page.screenshot(path=str(SHOTS / f"{name}.png"))
            except Exception as e:  # noqa: BLE001
                print("shot", name, "failed:", e, flush=True)

        def step(key, action, min_wait=0.0):
            start = now()
            try:
                action()
            except Exception as e:  # noqa: BLE001
                print("step", key, "failed:", e, flush=True)
            marks.append((start + .3, key))
            rest = max(len(lines[key][0]) / SR + .8, min_wait) - (now() - start)
            if rest > 0:
                page.wait_for_timeout(int(rest * 1000))

        def wait_until(check, seconds):
            a = now()
            while now() - a < seconds:
                if check():
                    break
                page.wait_for_timeout(1000)
            waits.append((a, now()))

        def menu(item):
            glide(page.get_by_role("button", name="Simulate an alert"), True)
            page.wait_for_timeout(700)
            glide(page.get_by_role("menuitem", name=item), True)

        page.mouse.move(800, 450)
        step("open", lambda: (page.wait_for_timeout(500), shot("cases")))
        step("leak", lambda: (menu("Test: send the full chat"), page.wait_for_timeout(1200), shot("privacy-refused")), min_wait=8)
        page.wait_for_timeout(1500)
        step("alert", lambda: (menu("possible grooming"), page.wait_for_url("**/cases/*"), page.wait_for_timeout(2000), shot("desk-alert")))
        step("ask", lambda: glide(page.get_by_role("button", name="Ask the agent for a plan"), True))
        marks.append((now(), "wait"))
        wait_until(lambda: page.get_by_text("Waiting for you").count() >= 3 and not page.get_by_text("Thinking").count(), 1500)
        page.wait_for_timeout(1500)
        shot("desk-plan")
        step("plan", lambda: (page.mouse.move(500, 500, steps=15), page.mouse.wheel(0, 250)), min_wait=6)
        page.mouse.wheel(0, -250)

        def edit():
            glide(page.get_by_role("button", name="Edit"), True)
            page.wait_for_timeout(600)
            box = page.locator("article textarea").first
            box.click()
            page.keyboard.press("End")
            page.keyboard.type(" I will start with: I'm not angry, I want to help.", delay=35)
            page.wait_for_timeout(500)
            glide(page.get_by_role("button", name="Save"), True)
            page.wait_for_timeout(1500)
            glide(page.get_by_role("button", name="Approve"), True)
        step("edit", edit, min_wait=8)

        def approve_rest():
            for _ in range(8):
                btn = page.locator("article").get_by_role("button", name="Approve")
                if not btn.count():
                    break
                glide(btn, True)
                page.wait_for_timeout(900)
            page.wait_for_timeout(500)
            glide(page.get_by_role("button", name="Mark done"), True)
            page.wait_for_timeout(1200)
            shot("desk-approved")
        step("approve", approve_rest, min_wait=6)

        page.mouse.wheel(0, -2000)
        page.wait_for_timeout(600)
        step("draft", lambda: glide(page.get_by_role("button", name="Draft the talk script"), True))
        marks.append((now(), "wait"))
        wait_until(lambda: page.locator("[role=tabpanel] textarea").count() > 0 and not page.get_by_text("Thinking").count(), 1500)
        page.wait_for_timeout(1500)

        def script():
            area = page.locator("[role=tabpanel] textarea").first
            glide(area, True)
            page.keyboard.press("Control+End")
            page.keyboard.type("\nYou can always tell me, and you will never be in trouble for telling me.", delay=30)
            page.wait_for_timeout(500)
            glide(page.get_by_role("button", name="Save my edits"), True)
            page.wait_for_timeout(1500)
            glide(page.get_by_role("tabpanel").get_by_role("button", name="Approve"), True)
            page.wait_for_timeout(1200)
            shot("desk-drafts")
        step("script", script, min_wait=8)

        def log():
            glide(page.get_by_text("Case log"), False)
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(1500)
            shot("desk-log")
        step("log", log, min_wait=5)

        def close():
            page.mouse.wheel(0, -3000)
            page.wait_for_timeout(500)
            glide(page.get_by_role("button", name="Close case"), True)
            page.wait_for_timeout(800)
            page.get_by_role("alertdialog").locator("textarea").fill("")
            page.get_by_role("alertdialog").locator("textarea").type("Talked with Lia, kept the evidence, reported to SaferNet. Check in again on Sunday.", delay=25)
            page.wait_for_timeout(400)
            glide(page.get_by_role("alertdialog").get_by_role("button", name="Close case"), True)
            page.wait_for_timeout(1500)
            shot("desk-closed")
        step("close", close, min_wait=7)
        step("end", lambda: page.mouse.move(800, 300, steps=20), min_wait=5)
        page.wait_for_timeout(1500)
        video = Path(page.video.path())
        ctx.close()
        browser.close()

    (WORK / "tour_marks.json").write_text(json.dumps({"marks": marks, "waits": waits}), encoding="utf-8")
    build_tour(video, lines, marks, waits)


def build_tour(video: Path, lines, marks, waits):
    """Cut the recording into normal and sped-up parts, then place the narration on the new timeline."""
    total = duration(video)
    parts, cursor = [], 0.0
    for a, b in waits:
        parts.append((cursor, a + 1.5, 1.0))
        wait_line = len(lines["wait"][0]) / SR + 1.2
        speed = max(1.0, (b - a - 1.5) / max(wait_line, 6.0))
        parts.append((a + 1.5, b, speed))
        cursor = b
    parts.append((cursor, total, 1.0))

    def remap(t: float) -> float:
        out = 0.0
        for a, b, s in parts:
            if t <= a:
                break
            out += (min(t, b) - a) / s
        return out

    segs = []
    for i, (a, b, s) in enumerate(parts):
        if b - a < .05:
            continue
        seg = WORK / f"tour_part_{i:02d}.mp4"
        vf = f"setpts=(PTS-STARTPTS)/{s:.4f},scale={W}:{H}:flags=lanczos,fps={FPS}"
        if s > 1.01:
            label = f"{SPEED_LABEL} {s:.0f}x"
            fontfile = (WORK / "Inter.ttf").resolve().as_posix()
            vf += (f",drawbox=x=40:y=40:w={30 + 17 * len(label)}:h=64:color=0x1e1b4b@0.85:t=fill,"
                   f"drawtext=fontfile='{fontfile}':text='{label}':x=62:y=58:fontsize=30:fontcolor=0xffd678")
        run("ffmpeg", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(video), "-an", "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast", str(seg))
        segs.append(seg)
    lst = WORK / "tour_parts.txt"
    lst.write_text("".join(f"file '{s.resolve().as_posix()}'\n" for s in segs), encoding="utf-8")
    joined = WORK / "tour_joined.mp4"
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined))

    n = int((duration(joined) + 1) * SR)
    voice = np.zeros(n, np.float32)
    cues = []
    for at, key in marks:
        clip, text = lines[key]
        t = remap(at)
        i = int(t * SR)
        seg = clip[: max(0, n - i)]
        voice[i:i + len(seg)] += seg
        cues += [(t + a, t + b, s) for a, b, s in split_cue(text, len(clip) / SR)]
    mix_and_mux("family_desk_tour", joined, voice, sorted(cues), None, [(remap(marks[-1][0]) + 3, "chime", .8, 1320)])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    which = sys.argv[3] if len(sys.argv) > 3 else "both"
    if which in ("tour", "both"):
        make_tour()
    if which in ("film", "both"):
        make_film()
