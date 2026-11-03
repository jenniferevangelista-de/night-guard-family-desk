"""The public demo, in the style of the Night Guard videos: the Night Guard narrator (Brian's voice) tells the story, then walks
through the real Family Desk recording.

  1. context  the opening of the Night Guard film (picture reused, sound remixed without any noise effects)
  2. bridge   a new paper scene: an alert is only the beginning, now what?
  3. tour     the real Family Desk recording in a paper frame, the narrator beside it, titles, subtitles, more detail

Run from the repository root (in the cloud machine, not on a laptop):
  python video/make_demo.py voices   # narration with edge-tts
  python video/make_demo.py build    # video/out/family_desk_demo.mp4

Inputs in video/out/: ng/night_guard_film_en.mp4, ng/voz/n*.mp3, ng/secrecy.mp3, ng/family.mp3 (from the
Night Guard repository), work/tour_joined.mp4 (made by make_videos.py), fonts/ (impact.ttf, segoeprb.ttf).
"""
import asyncio
import json
import subprocess
import sys
import textwrap
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrator import INK, H, W, font, paper, shield, sloth, text  # noqa: E402

SR, FPS = 48000, 24
OUT = Path("video/out")
NG = OUT / "ng"
WORK = OUT / "demo_work"
MUSIC = Path("video/music/Funkorama.mp3")
VOICE, RATE = "en-US-BrianMultilingualNeural", "+10%"
NIGHT = (38, 50, 108)
SOFT = (120, 112, 125)
SPEED = 1.2  # the Night Guard film was rendered 20% faster than its timeline

# ------------------------------------------------------------------ narration

OUTRO = "Night Guard Family Desk. A partner for parents, a friend for kids, and now a plan for every alert."

BRIDGE = ("But an alert is only the beginning. It's late, a parent reads it, and thinks: now what? "
          "Do I talk to her? Do I keep the chat? Where do I report it? "
          "That's why there's Family Desk. The agent proposes. The parent decides. And both work on the same case.")

TOUR = [
    ("home", "Cases", "Here's Family Desk, running for real. On the left, the cases. Each one starts from a single "
                      "Night Guard alert, and every name and chat here is made up."),
    ("privacy", "Privacy first", "First, the rule that matters most. Let's try to send the desk the whole chat, the way a "
                                 "careless integration might. Refused, before anything is saved."),
    ("alert", "The alert", "Now a real-looking alert. Lia, eleven, on Roblox. Possible grooming. The parent sees the risk, "
                           "the app and one flagged phrase. Nothing more."),
    ("ask", "Ask for a plan", "One click asks the agent for a plan. The agent is Gemma 4, a small open model, running on a "
                              "plain four core CPU. No paid API, nothing to pay."),
    ("work", "Agent at work", "This part is sped up. The agent reads the case through the same typed actions the screen "
                              "uses, gets advice for this exact risk, and writes each step into the shared case."),
    ("plan", "The plan", "Here's the plan. A calm talk with no blame. Keep the evidence. Block the stranger. Report it. "
                         "Then check in again. Every step waits for the parent."),
    ("edit", "Edit and approve", "The parent can rewrite any step in their own words, then approve it. The agent can't "
                                 "approve anything. If it edits an approved step, that step comes back for review."),
    ("decide", "Parent decides", "The parent approves the rest, and marks the talk as done once it really happened."),
    ("words", "The words", "Next, the parent asks for the words to open that talk, gently and without blame."),
    ("work2", "Agent at work", "Sped up again. The draft goes into the same case, right next to the plan."),
    ("draft", "Talk script", "There's the script. The parent reads it, changes a line, saves, and approves it. "
                             "The report text and the case summary work the same way."),
    ("log", "Case log", "Everything is in the case log, labeled parent, agent or Night Guard. So anyone can see who did what."),
    ("close", "Close the case", "When every step is reviewed, the parent closes the case with a short note. If the agent "
                                "asks to close it, the parent has to approve that too."),
    ("end", "Family Desk", "Built on Agent-Native, with an open model, at no cost. The family sees the risk, never the "
                           "whole chat. And now they know what to do next."),
]
# where each part starts in family_desk_tour.mp4 (the first narration cue of each part)
TOUR_STARTS = [0.0, 11.42, 22.13, 33.53, 42.34, 54.74, 63.37, 71.92, 84.45, 89.56, 101.81, 111.14, 116.84, 127.17]

# the Night Guard film, in its own (unsped) timeline: (voice file, start)
NG_LINES = [("n2.mp3", 12.08), ("n3.mp3", 19.41), ("n4.mp3", 33.35), ("n5.mp3", 41.41),
            ("n6.mp3", 55.18), ("n7.mp3", 61.29), ("n8.mp3", 73.73), ("n10.mp3", 111.24)]
NG_SARAH, NG_FAMILY, NG_SWITCH = 79.76, 90.69, 61.29
NG_KEEP = [(12.06, 98.83), (111.24, 119.98)]  # the night scene to the alert, then the family view


def run(*cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def duration(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


@lru_cache(maxsize=64)
def pcm(path: str, tempo: float = 1.0) -> np.ndarray:
    af = ["-af", f"atempo={tempo}"] if tempo != 1.0 else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def add(buf, t0, a, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(a))
    buf[i:j] += a[: j - i] * g


def write_wav(x: np.ndarray, path: Path):
    x = np.clip(x, -1, 1)
    run_in = (np.stack([x, x], 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(path)],
                   input=run_in, check=True)


def funk(n: int) -> np.ndarray:
    x = pcm(str(MUSIC))
    x = np.tile(x, int(np.ceil(n / len(x))))[:n]
    return x / (np.abs(x).max() + 1e-9)


def duck(voice: np.ndarray, depth=0.6) -> np.ndarray:
    k = SR // 4
    c = np.cumsum(np.concatenate([np.zeros(k), (np.abs(voice) > 0.02).astype(float)]))
    return 1 - depth * np.clip((c[k:] - c[:-k]) / k * 3, 0, 1)


# tonal effects only: no noise, no static, no "shhh"
def tt(d):
    return np.arange(int(d * SR)) / SR


def pop():
    t = tt(0.18)
    return np.sin(2 * np.pi * (700 + 900 * t) * t) * np.exp(-t * 28) * 0.5


def chime(f0=1320.0):
    t = tt(0.6)
    return sum(np.sin(2 * np.pi * f0 * m * t) / m for m in (1, 2, 3)) * np.exp(-t * 5) * 0.25


def thump():
    t = tt(0.35)
    return np.sin(2 * np.pi * (90 + 120 * np.exp(-t * 25)) * t) * np.exp(-t * 12) * 0.8


def tick():
    t = tt(0.05)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.4


def swoosh():
    t = tt(0.28)
    return np.sin(2 * np.pi * (320 * t + 1400 * t ** 2)) * np.sin(np.pi * t / .28) ** 2 * 0.3


def alarm():
    t = tt(0.5)
    return np.sin(2 * np.pi * 660 * t) * (np.sin(2 * np.pi * 4 * t) > 0) * np.exp(-t * 3) * 0.3


def drama(dur: float) -> np.ndarray:
    """The Night Guard opening bed (A minor: Am-F-Dm-E), pads, low piano and a heartbeat, all pure tones."""
    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)
    out = np.zeros(int(dur * SR))
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (50, [50, 53, 57]), (52, [52, 56, 59])]
    for k in range(int(dur / 4) + 1):
        root, ch = prog[k % 4]
        t = tt(4 * 1.15)
        env = np.minimum(1, t / 1.2) * np.minimum(1, (4 * 1.15 - t) / 0.8).clip(0)
        pad = sum(np.sin(2 * np.pi * hz(x) * (1 + dt) * t) + .35 * np.sin(4 * np.pi * hz(x) * (1 + dt) * t)
                  for x in ch for dt in (-.003, .003))
        add(out, k * 4, pad * env * .05 + np.sin(2 * np.pi * hz(root - 24) * t) * env * .12)
        for b, x in enumerate([ch[0] + 12, ch[2] + 12, ch[1] + 12, ch[2] + 12]):
            pt = tt(1.6)
            add(out, k * 4 + b, sum(np.sin(2 * np.pi * hz(x) * h * pt) / h ** 1.5 for h in (1, 2, 3)) * np.exp(-pt * 2.2) * .07)
    for i in range(int(dur / 1.15)):
        bt = tt(.25)
        beat = np.sin(2 * np.pi * (55 + 30 * np.exp(-bt * 30)) * bt) * np.exp(-bt * 18) * .35
        add(out, i * 1.15, beat)
        add(out, i * 1.15 + .28, beat * .7)
    return out


def mixdown(x: np.ndarray) -> np.ndarray:
    x = np.tanh(x * 0.9) / np.tanh(0.9)
    return x / (np.abs(x).max() + 1e-9) * 0.95


# ------------------------------------------------------------------ voices

async def make_voices():
    import edge_tts
    vdir = WORK / "voz"
    vdir.mkdir(parents=True, exist_ok=True)
    lines = [("bridge", BRIDGE), ("outro", OUTRO)] + [(sid, line) for sid, _, line in TOUR]
    meta = {}
    for sid, line in lines:
        f = vdir / f"{sid}.mp3"
        for attempt in range(5):
            try:
                await edge_tts.Communicate(line, VOICE, rate=RATE).save(str(f))
                break
            except Exception:  # noqa: BLE001
                if attempt == 4:
                    raise
                await asyncio.sleep(3)
        meta[sid] = {"line": line, "voice": str(f), "dur": round(duration(f), 2)}
        print(f"{sid:8} {meta[sid]['dur']:5.2f}s", flush=True)
    (WORK / "voices.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def voices():
    return json.loads((WORK / "voices.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ shared drawing

@lru_cache(maxsize=64)
def env(path: str):
    a = pcm(path)
    hop = SR // 12
    r = np.array([np.sqrt(np.mean(a[j:j + hop] ** 2)) for j in range(0, len(a), hop)])
    return (r / (r.max() or 1)).tolist()


def mouth(path: str, t: float):
    e = env(path)
    k = int(t * 12)
    if not 0 <= k < len(e):
        return None
    return 0.0 if e[k] < 0.12 else min(1.0, e[k] * 1.25)


def split_line(line: str):
    return [p.strip() for p in line.replace(": ", ":|").replace(". ", ".|").replace("? ", "?|").split("|") if p.strip()]


def cues(line: str, start: float, dur: float):
    parts = split_line(line)
    total = sum(len(p) for p in parts)
    out, t = [], start
    for p in parts:
        d = dur * len(p) / total
        out.append((t, t + d + 0.15, p))
        t += d
    return out


def subtitle(d, s, cx, bottom, maxw):
    f = font("segoeprb.ttf", 38)
    lines = textwrap.wrap(s, 64) if d.textlength(s, font=f) > maxw else [s]
    hh = 54 * len(lines)
    y0 = bottom - 30 - hh
    mw = max(d.textlength(ln, font=f) for ln in lines)
    d.rounded_rectangle((cx - mw / 2 - 22, y0 - 8, cx + mw / 2 + 22, y0 + hh + 4), 16, fill=(255, 251, 240, 235))
    for i, ln in enumerate(lines):
        text(d, ln, cx, y0 + 25 + i * 54, 38, INK)


def encode(frames_fn, n_frames, wav: Path, dst: Path, bg_video: Path | None = None, geom=None):
    """Pipe RGBA frames (optionally over a scaled background video) plus a wav into an mp4."""
    if bg_video is not None:
        fx, fy, fw, fh = geom
        inputs = ["-i", str(bg_video), "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                  "-i", str(wav)]
        filt = ["-filter_complex", f"[0:v]fps={FPS},scale={fw}:{fh},pad={W}:{H}:{fx}:{fy}:color=#f7f2e6[bg];"
                                   f"[bg][1:v]overlay=0:0:shortest=1,setsar=1[v]", "-map", "[v]", "-map", "2:a"]
    else:
        inputs = ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav)]
        filt = ["-map", "0:v", "-map", "1:a"]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", *inputs, *filt, "-t", f"{n_frames / FPS:.3f}",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS),
                           "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), str(dst)], stdin=subprocess.PIPE)
    for i in range(n_frames):
        ff.stdin.write(frames_fn(i / FPS).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit(f"ffmpeg failed for {dst}")
    print(dst, round(duration(dst), 1), flush=True)


# ------------------------------------------------------------------ 1. context

def build_context() -> Path:
    span = NG_KEEP[-1][1] + 1
    n = int(span * SR)
    voice, sfx = np.zeros(n), np.zeros(n)
    for f, st in NG_LINES:
        v = pcm(str(NG / "voz" / f))
        add(voice, st, v / (np.abs(v).max() + 1e-9) * .9)
    for f, st in (("secrecy.mp3", NG_SARAH), ("family.mp3", NG_FAMILY)):
        v = pcm(str(NG / f))
        add(voice, st, v / (np.abs(v).max() + 1e-9) * .9)
    for t0 in (2.2, 3.8, 5.6, 7.4):
        add(sfx, 10.88 + t0, pop())
    add(sfx, 19.41 + 7.0, thump())
    add(sfx, 19.41 + 8.6, thump(), .7)
    for i in range(10):
        add(sfx, 33.35 + .5 + i * .5, tick())
    for i in range(4):
        add(sfx, 41.41 + .4 + i * .7, pop(), .6)
    add(sfx, 41.41 + 8.6, swoosh())
    add(sfx, 41.41 + 9.8, thump(), .8)
    add(sfx, 55.18 + 2.6, pop())
    add(sfx, 61.29 + 1.5, chime(880))
    add(sfx, 61.29 + 1.65, chime(1320))
    add(sfx, NG_SARAH - .8, alarm())
    add(sfx, NG_SARAH - .3, thump(), .6)
    add(sfx, 111.24 + 2.0, chime(1568))
    add(sfx, 111.24 + 2.12, chime(2093))
    for t0 in (4.4, 5.4, 6.4):
        add(sfx, 111.24 + t0, pop(), .7)
    ds = int((12.08 - .6) * SR)
    dr_ = np.zeros(n)
    d = drama(NG_SWITCH + 3)[: n - ds]
    dr_[ds:ds + len(d)] = d
    dr_ /= np.abs(dr_).max() + 1e-9
    fk = funk(n)
    x = np.clip((np.arange(n) / SR - NG_SWITCH) / 2.0, 0, 1)
    music = dr_ * (1 - x) * .55 + fk * x * .30
    music[ds:ds + int(1.5 * SR)] *= np.linspace(0, 1, int(1.5 * SR))
    mix = mixdown(voice + sfx * .7 + music * duck(voice, .55))
    raw = WORK / "context_raw.wav"
    write_wav(mix, raw)
    # cut the kept parts out of the (sped up) film and the sped up mix, then join them
    parts = []
    for k, (a, b) in enumerate(NG_KEEP):
        a2, b2 = a / SPEED, b / SPEED
        p = WORK / f"context_{k}.mp4"
        af = f"atempo={SPEED},atrim={a2:.3f}:{b2:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st={b2 - a2 - .3:.3f}:d=0.3"
        run("ffmpeg", "-v", "error", "-y", "-ss", f"{a2:.3f}", "-to", f"{b2:.3f}", "-i", NG / "night_guard_film_en.mp4",
            "-i", raw, "-filter_complex", f"[0:v]fps={FPS},scale={W}:{H},setpts=PTS-STARTPTS[v];[1:a]{af}[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), p)
        parts.append(p)
    return join(parts, WORK / "part1_context.mp4")


# ------------------------------------------------------------------ 2. bridge

def build_bridge() -> Path:
    v = voices()["bridge"]
    line, path, vd = v["line"], v["voice"], v["dur"]
    lead = 0.6
    dur = lead + vd + 1.2
    cs = cues(line, lead, vd)

    def at(word):
        return lead + vd * line.find(word) / len(line)

    t_now, t_fd, t_prop, t_dec, t_same = at("now what"), at("That's why"), at("The agent"), at("The parent"), at("And both")
    questions = [(at("Do I talk"), "Talk to her?"), (at("Do I keep"), "Keep the chat?"), (at("Where do I"), "Report it where?")]

    def frame(t):
        im = paper().copy().convert("RGBA")
        d = ImageDraw.Draw(im)
        if t < t_fd:
            # the alert card the parent just got
            d.rounded_rectangle((300, 150, 1120, 430), 30, fill=(255, 255, 255, 255), outline=INK, width=6)
            text(d, "Night Guard alert", 710, 205, 44, NIGHT, "mm", "impact.ttf")
            text(d, "Possible grooming  ·  Roblox  ·  Lia", 710, 280, 40)
            text(d, "“let's keep this our secret”", 710, 355, 40, SOFT)
            if t >= t_now:
                text(d, "Now what?", 710, 560, 110, (214, 52, 52), "mm", "impact.ttf")
            for k, (tq, q) in enumerate(questions):
                if t >= tq:
                    text(d, q, 710 + (k - 1) * 380, 720, 42)
        else:
            text(d, "Family Desk", 760, 210, 130, NIGHT, "mm", "impact.ttf")
            text(d, "the agent and the parent, on the same case", 760, 320, 44, SOFT)
            for k, (tq, label) in enumerate(((t_prop, "The agent proposes"), (t_dec, "The parent decides"),
                                             (t_same, "One shared case"))):
                if t >= tq:
                    x0 = 250 + k * 360
                    d.rounded_rectangle((x0, 470, x0 + 330, 640), 26, fill=(255, 255, 255, 255), outline=INK, width=5)
                    for i, ln in enumerate(textwrap.wrap(label, 12)):
                        text(d, ln, x0 + 165, 530 + i * 52, 44, NIGHT, "mm", "impact.ttf")
        m = mouth(path, t - lead)
        sloth(im, t, 1620, 960, 420, m or 0.0, "talk" if m is not None else "listen")
        d = ImageDraw.Draw(im)
        for a, b, s in cs:
            if a <= t < b:
                subtitle(d, s, 760, 1060, 1300)
                break
        return im

    n = int(dur * SR)
    vo = np.zeros(n)
    a = pcm(path)
    add(vo, lead, a / (np.abs(a).max() + 1e-9) * .9)
    fx = np.zeros(n)
    add(fx, .1, swoosh())
    add(fx, t_now, pop())
    for tq, _ in questions:
        add(fx, tq, pop(), .6)
    add(fx, t_fd, chime(1320))
    add(fx, t_fd + .15, chime(1760))
    for tq in (t_prop, t_dec, t_same):
        add(fx, tq, pop(), .7)
    music = funk(n) * .22 * duck(vo)
    music *= np.minimum(1, np.arange(n) / SR / .8)
    wav = WORK / "bridge.wav"
    write_wav(mixdown(vo + fx * .7 + music), wav)
    dst = WORK / "part2_bridge.mp4"
    encode(frame, int(dur * FPS), wav, dst)
    return dst


# ------------------------------------------------------------------ 3. tour

FX, FY, FW, FH = 40, 40, 1536, 960


@lru_cache(maxsize=1)
def tour_base():
    im = paper().copy().convert("RGBA")
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((FX + 10, FY + 14, FX + FW + 10, FY + FH + 14), 22, fill=(60, 50, 40, 70))
    im = Image.alpha_composite(im, sh)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((FX - 8, FY - 8, FX + FW + 8, FY + FH + 8), 26, fill=(34, 30, 38, 255))
    hole = Image.new("L", (W, H), 255)
    ImageDraw.Draw(hole).rounded_rectangle((FX, FY, FX + FW, FY + FH), 18, fill=0)
    im.putalpha(Image.fromarray(np.minimum(np.array(im.split()[3]), np.array(hole))))
    return im


def build_tour() -> Path:
    src = OUT / "work" / "tour_joined.mp4"  # the tour picture before subtitles and sound
    total = duration(src)
    vo = voices()
    lead = 0.3
    pieces, segs, t = [], [], 0.0
    bounds = TOUR_STARTS + [total]
    for k, (sid, title, _) in enumerate(TOUR):
        a, b = bounds[k], bounds[k + 1]
        need = lead + vo[sid]["dur"] + 0.5
        p = WORK / f"tour_{k:02d}.mp4"
        run("ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-an", "-vf", f"fps={FPS}",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", p)
        pieces.append(p)
        span = duration(p)
        hold = max(0.0, need - span)
        if hold > 0.05:
            still = WORK / f"still_{k:02d}.png"
            run("ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", p, "-frames:v", "1", "-update", "1", still)
            h = WORK / f"tour_{k:02d}_hold.mp4"
            run("ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", still, "-t", f"{hold:.3f}", "-vf", f"fps={FPS}",
                "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", h)
            pieces.append(h)
        segs.append({"id": sid, "title": title, "start": t, "vstart": t + lead})
        t += span + hold
    lst = WORK / "tour_list.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in pieces), encoding="utf-8")
    rec = WORK / "tour_held.mp4"
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", rec)
    dur = duration(rec)
    allcues = [c for s in segs for c in cues(vo[s["id"]]["line"], s["vstart"], vo[s["id"]]["dur"])]
    end_at = segs[-1]["vstart"] + vo["end"]["dur"]

    def frame(tq):
        im = tour_base().copy()
        d = ImageDraw.Draw(im)
        cur = [s for s in segs if s["start"] <= tq] or segs[:1]
        s = cur[-1]
        idx = segs.index(s) + 1
        cx = (FX + FW + W) / 2
        text(d, f"{idx}/{len(segs)}", cx, 90, 40, SOFT)
        for i, ln in enumerate(textwrap.wrap(s["title"], 10)):
            text(d, ln, cx, 165 + i * 66, 60, NIGHT, "mm", "impact.ttf")
        m = mouth(vo[s["id"]]["voice"], tq - s["vstart"])
        mood = "talk" if m is not None else "listen"
        sloth(im, tq, cx, 1000, 330, m or 0.0, mood)
        d = ImageDraw.Draw(im)
        for a, b, sub in allcues:
            if a <= tq < b:
                subtitle(d, sub, FX + FW / 2, FY + FH, 1400)
                break
        return im

    n = int(dur * SR)
    voice, fx = np.zeros(n), np.zeros(n)
    for s in segs:
        a = pcm(vo[s["id"]]["voice"])
        add(voice, s["vstart"], a / (np.abs(a).max() + 1e-9) * .9)
        add(fx, s["start"], pop(), .5)
    add(fx, end_at + .3, chime(880), .9)
    add(fx, end_at + .45, chime(1320), .9)
    fade = np.ones(n)
    fade[int((dur - 2) * SR):] = np.linspace(1, 0, n - int((dur - 2) * SR))
    wav = WORK / "tour.wav"
    write_wav(mixdown(voice + fx * .7 + funk(n) * .22 * duck(voice, .65) * fade), wav)
    dst = WORK / "part3_tour.mp4"
    encode(frame, int(dur * FPS), wav, dst, rec, (FX, FY, FW, FH))
    return dst


# ------------------------------------------------------------------ 4. end card

def build_outro() -> Path:
    v = voices()["outro"]
    path, vd = v["voice"], v["dur"]
    lead = 0.5
    dur = lead + vd + 3.5
    vend = lead + vd

    def frame(t):
        im = paper().copy().convert("RGBA")
        d = ImageDraw.Draw(im)
        shield(d, t, W / 2, 250, 0.8)
        z = min(1.0, t / 0.5)
        z = 1 - (1 - z) ** 3
        text(d, "Night Guard Family Desk", W / 2, 500, int(50 + 60 * z), NIGHT, "mm", "impact.ttf")
        if t > lead + 1.0:
            text(d, "a partner for parents · a friend for kids · a plan for every alert", W / 2, 610, 46, INK)
        if t > lead + 2.4:
            text(d, "github.com/jenniferevangelista-de/night-guard-family-desk", W / 2 - 60, 710, 40, (214, 52, 52))
        if t > lead + 3.0:
            text(d, "Jennifer Evangelista · Agent-Native · Gemma · Night Guard", W / 2, 800, 34, SOFT)
        text(d, 'Music: "Funkorama" Kevin MacLeod (incompetech.com), CC BY 4.0 · opening score: original', W / 2, 1050, 22, SOFT)
        m = mouth(path, t - lead)
        mood = "talk" if m is not None else ("listen" if t < lead else ("yawn" if t < vend + 1.0 else "sleep"))
        sloth(im, t, 1720, 990, 340, m or 0.0, mood)
        return im

    n = int(dur * SR)
    vo = np.zeros(n)
    a = pcm(path)
    add(vo, lead, a / (np.abs(a).max() + 1e-9) * .9)
    fx = np.zeros(n)
    add(fx, lead, chime(880), .9)
    add(fx, lead + .15, chime(1320), .9)
    fade = np.ones(n)
    fade[int((dur - 2.5) * SR):] = np.linspace(1, 0, n - int((dur - 2.5) * SR))
    wav = WORK / "outro.wav"
    write_wav(mixdown(vo + fx * .7 + funk(n) * .22 * duck(vo, .65) * fade), wav)
    dst = WORK / "part4_outro.mp4"
    encode(frame, int(dur * FPS), wav, dst)
    return dst


# ------------------------------------------------------------------ join

def join(parts, dst: Path) -> Path:
    ins, pre, filt = [], "", ""
    for k, p in enumerate(parts):
        ins += ["-i", str(p)]
        pre += f"[{k}:v]setsar=1[v{k}];"
        filt += f"[v{k}][{k}:a]"
    run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", f"{pre}{filt}concat=n={len(parts)}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), dst)
    return dst


def build():
    parts = [build_context(), build_bridge(), build_tour(), build_outro()]
    joined = join(parts, WORK / "joined.mp4")
    dst = OUT / "family_desk_demo.mp4"
    run("ffmpeg", "-v", "error", "-y", "-i", joined, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), dst)
    print("done", dst, round(duration(dst), 1), flush=True)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "build"
    if what == "voices":
        asyncio.run(make_voices())
    elif what == "context":
        build_context()
    elif what == "bridge":
        build_bridge()
    elif what == "tour":
        build_tour()
    elif what == "outro":
        build_outro()
    else:
        build()
