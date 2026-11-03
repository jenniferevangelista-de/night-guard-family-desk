# How the Family Desk demo was made

The demo is narrated by the character from the Night Guard videos, with the `en-US-BrianMultilingualNeural` voice. Every case, child and chat shown is fictional.

| Part | What it is |
|---|---|
| Context | The opening of the Night Guard film: the problem, the numbers, Night Guard warning the kid and sending one alert to the family |
| Bridge | A new paper scene: an alert is only the beginning, so now what? Family Desk: the agent proposes, the parent decides, one shared case |
| Tour | A real recording of the running app: a refused full-chat payload, a new alert, the agent's plan, edits and approvals, the talk script, the case log, closing the case |

The same video is the hackathon demo on Clips.

## Pipeline

```
video/make_videos.py tour                    records the real app (Playwright, headless Chromium,
        |                                    visible cursor); waiting time of the CPU model is cut
        |                                    and sped up, with an on-screen label
        v
video/make_demo.py voices                    Narration (edge-tts, Brian, +10%)
video/make_demo.py build
   1. context   Night Guard film picture, sound remixed: Brian's original lines, the app's spoken
                warning, the A minor bed, then Funkorama
   2. bridge    paper scene drawn with Pillow, the narrator's mouth follows the voice
   3. tour      recording in a paper frame, the narrator beside it, part titles, subtitles; the picture
                holds on the last frame of a part when the narration needs more time
        |
        v
joined, loudness -14 LUFS, H.264 + AAC  ->  video/out/family_desk_demo.mp4
```

Run it in a cloud machine, from the repository root, with the app running for the tour:

```bash
python video/make_videos.py http://127.0.0.1:8080 video/out tour
python video/make_demo.py voices
python video/make_demo.py build
```

`make_demo.py` also needs, in `video/out/`: the Night Guard film and its narration files (`ng/`, from the Night Guard repository) and the fonts `impact.ttf` and `segoeprb.ttf` (`fonts/`, not redistributed here). `video/narrator.py` draws the narrator and the paper.

## Sound

Every effect is a tone: pops, chimes, ticks, a low thump, a sine glide for transitions. There is no noise, static or hiss anywhere in the mix.

## Honest speed-up

The agent runs on Gemma 4 E2B through Ollama on a 4-core CPU with no GPU. A plan takes a few minutes there. The tour keeps every frame of those minutes but plays them faster, and the label on screen says "Gemma 4 E2B on CPU · sped up" with the factor. Nothing in the agent's output is edited.

## Tools

| Tool | Used for |
|---|---|
| Playwright + Chromium | Drives the real app and records the tour |
| Pillow + NumPy | Draws the narrator, the paper scenes and the frame, synthesizes the music bed and the effects |
| edge-tts | Narration (Brian) |
| ffmpeg | Speed-up, cuts, holds, mixing, loudness, encoding |

## Music credit

"Funkorama" by Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/). The dramatic opening music is original and generated in code. The MP3 is not stored in this repository; put it at `video/music/Funkorama.mp3` before rendering.
