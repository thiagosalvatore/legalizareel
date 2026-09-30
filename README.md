# hogreel

You shipped something good. Nobody's using it, because nobody knows it's good yet.

**hogreel** turns a short script into a punchy, on-brand hype video, rendered headless from HTML. No video editor, no timeline.
You write the lines and the scene list; your agent renders the rest.
Any skill, product, feature, or changelog moment is fair game. Videos are sorted by team, so drop yours in your team's folder and go.

Videos so far: [`devex/facade`](videos/devex/facade.py) (sells [`/isolating-product-facade-contracts`](https://github.com/PostHog/posthog/tree/master/.agents/skills/isolating-product-facade-contracts)), [`devex/stamphog`](videos/devex/stamphog.py) (a Suno music reel), and [`devex/postpile`](videos/devex/postpile.py) (the PostPile launch, HyperFrames scenes with an ElevenLabs voiceover). For a new video, copy `postpile`.

## Quick start

After [setup](#setup):

```bash
ELEVENLABS_API_KEY=$(op read "op://General/Elevenlabs/API Key") python build.py devex/postpile
open postpile-launch-devex.mp4
```

The voiceover take is cached after the first build, so later builds need no key as long as the narration doesn't change.

## Pick how it looks and how it sounds

Every video makes two choices.

**Scenes** (how it looks):

- **HyperFrames** (default for new videos). Each scene is a small HTML page with a GSAP timeline, previewed live in a browser studio and linted. See [HyperFrames scenes](#hyperframes-scenes).
- **Classic** (`facade`, `stamphog`). Each scene is an HTML string built with `themes/posthog.py` and animated with CSS keyframes. Simpler, but no live preview.

**Soundtrack** (how it sounds):

- **ElevenLabs voiceover** (default for feature and launch reels). One enthusiastic, fluent take over the whole reel. See [Voiceover](#voiceover-elevenlabs).
- **Suno song** (music reels). Scenes are timed to a song's lyric track. See [Song cut](#song-cut-suno).
- **Kokoro** (free, local, offline). Narration is synthesized a line per scene. It's the fallback when a storyboard doesn't ask for a voiceover.

Voiceover and Kokoro cuts get the chiptune SFX and a quiet music bed on top. A song cut uses the song alone.

## Why it's built this way

The toolchain (Playwright + Chrome, ffmpeg, a local neural TTS with torch) is ~1 GB to render a ~20 MB file that changes rarely.
So this is **render-on-demand, not build-in-CI**: an agent (or you) runs `python build.py` locally when the script changes.
There is intentionally no GitHub Actions workflow.
The rendered `.mp4` ships as a **Release asset**, not committed to git (see [Publishing](#publishing)).

## Layout

```text
engine.py                      # brand-agnostic pipeline: timing, TTS/voiceover, song sync, SFX, mix, render + mux
themes/posthog.py              # the brand layer for classic scenes: CSS, page() chrome, hedgehog helpers, palette
themes/posthog.css + .js       # the brand layer for HyperFrames scenes (CSS + GSAP motion helpers)
videos/<team>/<name>.py        # one video = one storyboard (videos sorted by owning team)
videos/devex/postpile-scenes/  # a HyperFrames project: compositions/<scene id>.html + its own CSS
build.py                       # thin dispatcher: `python build.py <team>/<name>`
render_anim.mjs, poster.mjs    # classic path: frame capture and the poster still
kokoro_batch.py                # Kokoro synthesis in one model load (runs in .tts-venv)
assets/                        # shared hedgehog PNGs, logos, fonts, songs, product art
.claude/skills/suno-song/      # agent skill: Suno lyrics/styles + syncing a song to the scenes
```

The split is the point: **engine** knows nothing about a brand, **theme** owns all the PostHog look, **storyboard** owns just the story.
A new video is a new `videos/<team>/<name>.py` (plus its scenes folder on the HyperFrames path). Everything else is reused.

## Setup

Needs **ffmpeg/ffprobe**, **node + Playwright + Google Chrome**, **Node 22+** for HyperFrames, and a Python venv for Kokoro.

```bash
# ffmpeg (or use a flox env that provides it)
brew install ffmpeg espeak-ng

# node side: Playwright drives an installed Google Chrome (channel: 'chrome')
npm install
npx playwright install chrome   # skip if you already have Google Chrome

# Kokoro neural TTS (local + free). torch arrives as a dependency.
python3.12 -m venv .tts-venv
.tts-venv/bin/pip install kokoro soundfile
```

The HyperFrames CLI runs through `npx`, pinned in `engine.HF_CLI`, so there's nothing to install for it.
Kokoro falls back to `edge-tts` (needs network) and then macOS `say` if `.tts-venv` is absent, so a quick render still works without the venv, just with a worse voice.

## Build

```bash
python build.py <team>/<name>   # e.g. devex/postpile; no argument renders devex/facade
```

The output is `<name>.mp4` in the repo root, plus `poster.png`.

Env toggles:

- `SKIP_RENDER=1`: keep the rendered video and only rebuild the audio + mux. Seconds instead of minutes. Use it when you changed sound but not visuals. On the classic path it reuses the captured frames, so narration and timing can change too. On the HyperFrames path it reuses the last rendered video and refuses when any scene changed length.
- `SHORT=1`: render the ~40s teaser cut (keeps the storyboard's `short_keep` beats, drops flashes), output suffixed `-40s`.
- `SONG=path/to/song.m4a`: the song cut, see [Song cut](#song-cut-suno). Output suffixed `-song`.
- `SONG_END=2:22`: with `SONG`, end the video there (seconds or m:ss) instead of at the song's end.
- `LYRICS=1`: print the paste-ready Suno lyrics sheet and exit without rendering.

## HyperFrames scenes

[HyperFrames](https://github.com/heygen-com/hyperframes) is an open-source HTML-to-video framework: GSAP timelines, seekable frame capture, a live-reload preview, and a linter.
A storyboard hands its visuals to it with `build(sb, ..., hyperframes=<dir>, theme_files=HF_THEME, poster_scene="<id>")`:

- Each scene is a sub-composition, `<dir>/compositions/<scene id>.html`, with one paused GSAP timeline.
  It reads its final length from the `dur` variable, so beats land at a fraction of the scene and still line up whatever the soundtrack makes the scene's length.
- The scene's `effect` arrives as the `zoom` variable, and every scene ends with `window.brand.camera(tl, "<id>", zoom, dur)`: a slow push on the stage while the logo and team badge hold still.
- `scene(..., blend=0.6)` cross-fades into that scene instead of cutting. The scene before stays on screen underneath while this one fades in, and both keep their timing.
- The engine still does timing, voice, song sync, SFX and the mix. It writes the root `index.html` (slots at the computed times, flashes as color cards), renders silently with the pinned CLI, and muxes the audio on top.
- `assets/` and the theme files are symlinked into the project at render time, so scenes use `assets/...` and the classes in `themes/posthog.css`.

To work on scene visuals, render once (that writes `index.html`), then:

```bash
cd videos/devex/postpile-scenes
npx hyperframes@0.8.85 preview                 # live-reload studio
npx hyperframes@0.8.85 lint                    # must be 0 errors
npx hyperframes@0.8.85 snapshot --at 12.5,30   # stills for a quick look
```

Before writing scenes, read `npx hyperframes@0.8.85 docs compositions` and `docs gsap`, and copy an existing scene's file shape (`compositions/pile.html`).
HyperFrames sends anonymous usage telemetry by default; `npx hyperframes@0.8.85 telemetry disable` turns it off.

## Voiceover (ElevenLabs)

A storyboard passes `build(..., voiceover={"voice": <id>, "model": "eleven_v3", "settings": {...}})`.
The whole narration goes to ElevenLabs as **one take**, so it flows through the reel instead of restarting every scene.
The per-character timestamps cut it back into a chunk per scene.
Pauses longer than 0.3s get capped (`VO_MAX_PAUSE`), and a scene shorter than its `min_dur` holds on silence.

Write the narration as one read:

- v3 audio tags like `[excited]` steer the delivery.
- Punctuation sets the pace: quick lists speed up, `...` slows down.
- `[[slnc N]]` markers are ignored (they're for Kokoro).

`postpile` uses Brian (`nPczCjzI2devNBz1zQrb`) at stability 0.5, speed 1.12.
The key lives in the team 1Password: `op read "op://General/Elevenlabs/API Key"`.
The account also holds cloned voices of real people; stick to the premade ones unless that person said yes.

**Credits.** The shared account has 10,000 characters a month, and a full take is ~1,500.
Takes are cached in `audio/voiceover/` by text + voice settings, so a rebuild with unchanged narration is free and needs no key.
When every scene line already appears, in order, in a cached take of the same voice, that take is reused and cut: dropping a scene, or trimming a line to a phrase the take already says, is free and keeps the delivery.
Any other change re-reads the whole take, which costs credits and changes the delivery elsewhere too.
To audition voices, sample one or two lines, not the whole script.

## Song cut (Suno)

`SONG=path/to/song.m4a python build.py <team>/<name>` makes a music video: the song replaces narration, SFX, and the music bed.
Load the `suno-song` skill for the whole workflow (lyrics, styles, generation, sync). Team style prompts and what each one produced live in [`videos/devex/suno-styles.md`](videos/devex/suno-styles.md).

How the sync works:

- The song needs timed lyrics embedded in the file (Suno exports have them).
- Scenes carry an optional `lyric=` (the song version of the line, with Suno `[Section]` tags). The song is matched against that, or against `narration` when there's no lyric. `LYRICS=1` prints the sheet to paste into Suno.
- Each scene needs at least one of its lines sung, in scene order, and runs until the next scene's line is sung. Other lines (chorus, ad-libs) just hold the current scene.
- A scene with neither `lyric` nor `narration` is a **filler** for instrumental stretches: it takes its `min_dur` out of the sung scene before it, so the next sung line still lands on its own frame.
- Scenes the song doesn't reach keep `min_dur` and play silent, which shows how much song is still missing.
- A song longer than the video is trimmed to the last scene with a 1.5s fade-out. For a take that keeps going after its last line, pick the end by ear with `SONG_END`, since Suno's lyric timings get unreliable near the end.

A song cut changes scene lengths, so it always needs a full render (no `SKIP_RENDER`).

## Sound effects

A scene's `sfx=[(name, offset)]` plays a sound at `offset` seconds into the scene. A negative offset counts back from the scene's end, for a sting that should close the scene whatever its final length.

- The generated sounds are in `engine.gen_sfx()` (`ding`, `tick`, `airhorn`, `success`, …).
- To reuse a real sound, such as a hook from one of the songs, cut it with `sb.sound("name", "assets/songs/x.m4a", start, end, fade_in=..., fade_out=...)` and use `"name"` in `sfx` like any other. `postpile` ends on the "dev-dev-DevEx" chop from `stamp-hog.m4a` this way.
- The music bed fades out over the last scene, so an end-card stinger plays on its own.

## A new video

```bash
mkdir -p videos/<your-team>
cp videos/devex/postpile.py videos/<your-team>/<name>.py
cp -r videos/devex/postpile-scenes videos/<your-team>/<name>-scenes   # then replace the compositions
python build.py <your-team>/<name>
```

For a classic video, copy `videos/devex/facade.py` instead and edit the `scene()` / `flash()` calls and `POSTER`.
Reuse the theme as-is, or write a sibling `themes/<brand>.py` (and `.css`/`.js`) with the same surface and import that instead.

## Shared infrastructure

The engine and theme belong to everyone.
A tweak that makes one video better (a new effect, a cleaner caption, a better voice setting, a tighter scene helper) should land in `engine.py` or the theme so every team's videos get it for free.
Keep only the story in your `videos/<team>/` script; push genuinely reusable wins down into the shared layer instead of copy-pasting them.

Keep the docs honest: if you change the structure, commands, palette, or fonts, update this README and `CLAUDE.md` in the same change. Agents working here are expected to do that automatically.

## Staying on-brand

The theme follows PostHog's [brand guidelines](https://posthog.com/handbook/brand): exact palette hex, official logo variants (white on dark, standard on light), official hedgehog art only (never AI-drawn), and the house voice for narration.
The load-bearing rules are pinned in [CLAUDE.md](CLAUDE.md#brand-compliance); the handbook is the source of truth.
Two things worth knowing up front: the palette is deliberately small and **has no green** (blue is the positive accent), and the hype animation style is an intentional deviation from the brand's "understated" default. Fine for a promo video, never for product UI.

## Publishing

The mp4 is a Release asset, kept out of git history. One release per video:

```bash
gh release create postpile-v1 postpile-launch-devex.mp4 \
  --title "PostPile launch video" \
  --notes "Re-render with: python build.py devex/postpile"
```

`poster.png` is a build output too (not committed); every build regenerates it.
Slack auto-generates a video thumbnail from an early frame, which is often dark.
Upload `poster.png` as a separate image alongside the video for a branded thumbnail.
