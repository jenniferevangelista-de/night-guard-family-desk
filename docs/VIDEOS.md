# How the Family Desk videos were made

Two videos, both narrated in first person with the `en-US-AvaMultilingualNeural` voice. Every case, child and chat shown is fictional.

| Video | What it is |
|---|---|
| Film | Why the desk exists and how it works: Night Guard's privacy rule, the plan, the approvals, the drafts, the stack |
| Tour | A real recording of the running app: a refused full-chat payload, a new alert, the agent's plan, edits and approvals, the talk script, the case log, closing the case |

Plus the hackathon demo on Clips, which is the tour uploaded to clips.agent-native.com.

## Pipeline

One script, `video/make_videos.py`, makes both (the same structure as the Night Guard and Witching Hour videos):

```
TOUR                                         FILM
Playwright drives the running app            scenes drawn with Pillow (1920x1080)
  (headless Chromium, visible cursor)        over the tour's screenshots
        |                                            |
waiting time of the CPU model is cut         one narration line per scene
and sped up, with an on-screen label               |
        |                                            |
narration placed on the new timeline   ---> same finishing: music bed + Funkorama,
                                             ducking, effects, Kalam subtitles,
                                             loudness -14 LUFS, H.264 + AAC
```

Run it with the app already running (see the README), from the repository root:

```bash
python video/make_videos.py http://127.0.0.1:8080 video/out tour
python video/make_videos.py http://127.0.0.1:8080 video/out film
```

The tour runs first because the film reuses its screenshots (`video/out/screens/`).

## Honest speed-up

The agent runs on Gemma 4 E2B through Ollama on a 4-core CPU with no GPU. A plan takes a few minutes there. The tour keeps every frame of those minutes but plays them faster, and the label on screen says "Gemma 4 E2B on CPU · sped up" with the factor. Nothing in the agent's output is edited.

## Tools

| Tool | Used for |
|---|---|
| Playwright + Chromium | Drives the real app and records the tour |
| Pillow + NumPy | Draws the film scenes, synthesizes the music bed and the effects |
| edge-tts | Narration (Ava) |
| ffmpeg | Speed-up, subtitles, mixing, loudness, encoding |

## Music credit

"Funkorama" by Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/). The quiet opening bed is original and generated in code. The MP3 is not stored in this repository; put it at `video/music/Funkorama.mp3` before rendering, or the script uses the generated bed only.
