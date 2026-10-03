# legalizareel

Short, punchy, on-brand videos for **Legaliza Obra**, rendered headless from HTML. You don't need a video editor or a timeline.
You write the lines and the scene list, and your agent renders the rest.
The default output is a vertical 1080×1920 reel in Brazilian Portuguese, for Instagram Reels, TikTok and YouTube Shorts.

This repo is a fork of PostHog's [hogreel](https://github.com/PostHog/hogreel). It keeps the engine. The theme, assets and videos are new.

Videos so far:

- [`marketing/economia-inss`](videos/marketing/economia-inss.py), a 53 s reel. It shows the INSS savings, then the eSocial work that piles up and gets rejected, then the app doing it in one click, with real app footage. For a new video, copy it.
- [`marketing/orcamento-obra`](videos/marketing/orcamento-obra.py), a 64 s reel. One client goes from the simulação to an orçamento, a link, a contract and an obra, and nobody types her data twice. It mixes animated scenes with cut app footage.
- [`marketing/assistente`](videos/marketing/assistente.py), a 61 s wide (1920×1080) product intro. It sells the Legaliza Obra plugin for Claude, shows how to add and connect it, and plays a real Claude session that runs a simulação.

## Quick start

After [setup](#setup):

```bash
ELEVENLABS_API_KEY=$(op read --account my.1password.com "op://Private/ElevenLabs/credential") \
  python build.py marketing/economia-inss
open economia-inss.mp4
```

With `ELEVENLABS_API_KEY` set, the narration is an ElevenLabs voiceover. Without it, a free local voice reads it. The key is in the personal 1Password account (vault Private, item ElevenLabs).

## How a video is made

- **Scenes** are [HyperFrames](https://github.com/heygen-com/hyperframes) compositions. Each scene is a small HTML page with a GSAP timeline. You can preview it live in a browser studio, and a linter checks it.
- **App footage** comes from the frontend's Playwright recorder. It runs the real app against the mock backend, so the video shows the real product with showcase data. See [App footage](#app-footage).
- **Soundtrack**:
  - **ElevenLabs voiceover** (the best one). The whole narration is read as one take.
  - **Local voice** (free, the fallback when there's no key). The fallback order is Kokoro `pm_alex` when `.tts-venv` exists, then edge-tts `pt-BR-AntonioNeural`, then macOS `say -v Luciana`.
  - **Suno song** (music reels).

The voiceover and local cuts get the chiptune SFX and a quiet music bed on top. A song cut uses the song alone.

## Why it's built this way

The toolchain (HyperFrames + Chrome, ffmpeg, optionally a local neural TTS with torch) is big, and the file it renders changes rarely.
So videos are **rendered on demand, never in CI**: an agent (or you) runs `python build.py` locally when the script changes.
There is intentionally no GitHub Actions workflow.
The rendered `.mp4` ships as a **Release asset** and is never committed to git (see [Publishing](#publishing)).

## Layout

```text
engine.py                          # brand-agnostic pipeline: timing, TTS/voiceover, song sync, SFX, mix, HyperFrames render + mux
themes/legalizaobra.py             # palette constants + HF_THEME (the files a scene project links in)
themes/legalizaobra.css + .js      # the brand layer for scenes: fonts, palette, blocks, GSAP motion helpers
videos/<team>/<name>.py            # one video = one storyboard
videos/<team>/<name>-scenes/       # its HyperFrames project: compositions/<scene id>.html
app_clips.py                       # copies app recordings from the frontend recorder into assets/app/
build.py                           # thin dispatcher: `python build.py <team>/<name>`
kokoro_batch.py                    # Kokoro synthesis in one model load (runs in .tts-venv)
assets/brand/                      # logo, icon, app icon, the site's construction photo
assets/fonts/                      # Hedvig Letters Serif + Inter (OFL)
assets/app/                        # app recordings (git-ignored, filled by app_clips.py)
.claude/skills/suno-song/          # agent skill: Suno lyrics/styles + syncing a song to the scenes
```

The layers stay separate:
- The **engine** knows nothing about a brand.
- The **theme** owns the whole Legaliza Obra look.
- The **storyboard** owns only the story.

## Setup

Needs **ffmpeg/ffprobe**, **Node 22+** (HyperFrames runs through `npx`) and **Google Chrome**. `uv` is optional, for edge-tts and the tests.

```bash
brew install ffmpeg espeak-ng

# optional: Kokoro neural TTS (local, free, offline). torch comes with it, about 1 GB.
python3.12 -m venv .tts-venv
.tts-venv/bin/pip install kokoro soundfile
```

The HyperFrames CLI is pinned in `engine.HF_CLI`, so you install nothing for it.
If `.tts-venv` is missing, the engine uses edge-tts (needs network), then macOS `say`.

## App footage

The frontend repo (`obra-certa-frontend`) has a mock backend and a Playwright recorder, in `mock-backend/` and `mock-backend/recording/`. The recorder shoots 1080×1920 clips of the real app with a visible cursor. Login still goes through the real Supabase project, and every account sees the showcase account (Construtora Horizonte).

```bash
cd ~/projects/personal/legaliza-obra/obra-certa-frontend
npx tsx mock-backend/server.ts                       # terminal 1: mock API on :8000
pnpm dev --port 3100                                 # terminal 2
cd mock-backend/recording && npm install
npm run login                                        # once, or when the Supabase session expires
npm run record                                       # every shot; `npm run record -- 02 07` for some
```

You can use other ports so you don't clash with another checkout:
- Run the mock with `MOCK_PORT=8100` and the app with `NEXT_PUBLIC_API_URL=http://localhost:8100 pnpm dev --port 3200`.
- Then record with `BASE_URL=http://localhost:3200 MOCK_URL=http://localhost:8100 npm run record`.

A storyboard lists the clips it needs, and its `main()` calls `app_clips.ensure(...)`. That copies each clip into `assets/app/`, scaled to 1080 wide with frequent keyframes so HyperFrames can seek it. It also refreshes a copy whose recording is newer. `OBRA_FRONTEND` overrides where the frontend checkout is. `python app_clips.py` syncs every recorded clip.

In a scene, a clip goes in a `.screen` frame:

```html
<div class="screen" id="obra-screen">
  <video id="obra-video" class="clip" src="assets/app/01-obra-andrade.mp4" data-start="0" data-media-start="3.2" muted playsinline></video>
</div>
```

- `data-media-start` trims the start of the clip.
- To pan or zoom, animate the `<video>` with `x`, `y` and `scale`. Its transform origin is its top-left corner.
- `scale: 1.06, x: -70` hides the app's sidebar rail.
- `scale: 1.8, x: -394, y: -925` centres a dialog in the middle of the app.

A recording made outside the recorder, such as a screen capture of Claude, goes in with `app_clips.adopt(<path>, "<name>")`. It writes `assets/app/<name>.mp4` at the recording's own size, and refreshes it when the recording is newer. Keep the recording outside the repo. `marketing/assistente` reads its Claude session from `CLAUDE_RECORDING`, which defaults to `~/Documents/LegalizaObra Videos/claude_video.mp4`. Export the capture at full size: the wide frame zooms in on it.

A recording often waits on something the reel should not show, such as a page that compiles in dev. To drop those stretches, cut the clip:

- The storyboard lists the `(start, end)` seconds to keep, and `main()` calls `app_clips.cut("<clip>", segments, "<scene>-cut")`. That writes `assets/app/<scene>-cut.mp4`, and the scene plays it with one `<video>`.
- `app_clips.cut_time(segments, t)` turns a moment in the recording into a moment in the cut, for sounds.
- `app_clips.cut_points(segments)` gives the seconds where each later segment starts. Pass them to the scene in `vars`, so the scene can reframe the video at each cut.
- Don't put two `<video>`s with the same `src` in one scene. HyperFrames does not seek them separately, and one of them freezes.

## Build

```bash
python build.py <team>/<name>   # no argument renders marketing/economia-inss
```

The output is `<name>.mp4` in the repo root, plus `poster.png`.

Env toggles:

- `SKIP_RENDER=1`: keep the last rendered video and only rebuild the audio and the mux. It refuses when any scene changed length.
- `SHORT=1`: render the teaser cut. It keeps only the storyboard's `short_keep` beats, and the output name gets `-40s`.
- `SONG=path/to/song.m4a`: the song cut, see [Song cut](#song-cut-suno). The output name gets `-song`.
- `SONG_END=2:22`: with `SONG`, end the video at this time instead of at the song's end.
- `LYRICS=1`: print the paste-ready Suno lyrics sheet and exit without rendering.

`build(..., size=VERTICAL)` is the default (1080×1920). `size=WIDE` renders 1920×1080. Scenes read the size as the `width` and `height` variables.

## Scenes

A storyboard hands its visuals to HyperFrames with `build(sb, ..., hyperframes=<dir>, theme_files=HF_THEME, poster_scene="<id>")`.

- Each scene is a sub-composition, `<dir>/compositions/<scene id>.html`, with one paused GSAP timeline.
  - It reads its final length from the `dur` variable. Beats land at a fraction of the scene, so they still line up whatever the soundtrack makes the scene's length.
- The scene's `effect` arrives as the `zoom` variable. Every scene ends with `window.brand.camera(tl, "<id>", zoom, dur)`: a slow push on the stage while the logo holds still.
- `scene(..., blend=0.5)` cross-fades into that scene instead of cutting.
- The theme has blocks for scenes that animate the product instead of filming it:
  - `.window` is an app or file window, and `.field` / `.input` is a form field in it.
  - `.doc` is a paper page, and `.swap` holds two `.var` / `.val` chips (a template field and its value).
  - `.screen.phone` is a phone frame for a clip recorded at a phone size. `.screen.wide` is a 1440×810 frame for landscape footage in a `WIDE` video.
  - `.stage.landscape` moves the logo to the top-left corner, for `WIDE` videos.
  - `.bubble` is a chat message, with an optional `.caret` for `typeText`.
  - `.chain`, `.step` and `.link` make a vertical flow of steps. `.check` is a ticked circle, and `.status.pending` / `.status.done` are status badges.
- The theme's motion helpers, besides `upIn`, `popIn`, `fadeIn`, `floatIn`, `counter` and `camera`:
  - `typeText(tl, el, text, at, cps)` types text out and returns when it ends.
  - `swapText(tl, el, at)` flips a `.swap` from its first child to its second.
  - `drawLine(tl, el, at, duration)` grows a `.link` downwards.
  - `counter(..., format)` takes an optional formatter, for counts that are not money.
- `scene(..., vars={...})` hands extra values to the scene's composition variables. Declare them in the composition's `data-composition-variables`. Use this when the storyboard also needs a value, such as the beat times for sounds. Then the value is written once, in the storyboard. `burocracia` gets its pile timings this way.
- The engine writes the root `index.html`, renders silently with the pinned CLI, and muxes the audio on top.
- `assets/` and the theme files are symlinked into the project at render time. That's why scenes use `assets/...` paths and the classes in `themes/legalizaobra.css`.

To work on scene visuals, render once (that writes `index.html`), then:

```bash
cd videos/marketing/economia-inss-scenes
npx hyperframes@0.8.85 preview                 # live-reload studio
npx hyperframes@0.8.85 lint                    # must be 0 errors
npx hyperframes@0.8.85 snapshot --at 12.5,30   # stills for a quick look
```

Before you write scenes, read `npx hyperframes@0.8.85 docs compositions` and `docs gsap`, and copy an existing scene's file shape (`compositions/obra.html`).
HyperFrames sends anonymous usage telemetry by default. `npx hyperframes@0.8.85 telemetry disable` turns it off.

## Voiceover (ElevenLabs)

A storyboard passes `build(..., voiceover={"voice": <id>, "model": "eleven_v3", "settings": {...}})`.

- The whole narration goes to ElevenLabs as **one take**, so it flows through the reel instead of restarting every scene. The per-character timestamps cut it back into a chunk per scene.
- Pauses longer than 0.3 s are shortened to 0.3 s (`VO_MAX_PAUSE`).
- A scene shorter than its `min_dur` holds on silence.
- `eleven_v3` speaks Brazilian Portuguese with any premade voice. `economia-inss` uses Brian (`nPczCjzI2devNBz1zQrb`), picked over the account's Brazilian library voices (Gabriel, Will, Eric) in an audition.
- To audition, render one line per voice with the text-to-speech endpoint (about 40–90 characters each). Never audition with a whole take.
- A new take changes where each word lands. Afterwards, move the scene beats (the `vars` of the scene) onto the words they illustrate. The take's alignment JSON in `audio/voiceover/` gives the start time of every character. Put the picture 0.1–0.5 s ahead of the word.

Write the narration as one read:

- v3 audio tags like `[excited]` steer the delivery. The local voices drop them.
- Punctuation sets the pace: quick lists speed up, `...` slows down.
- Write numbers the way you want them said ("81 mil", "legalizaobra ponto com").

Takes are cached in `audio/voiceover/` by text and voice settings.
- A rebuild with unchanged narration is free and needs no key.
- Dropping a scene, or trimming a line to a phrase the take already says, reuses the cached take.
- Any other change re-reads the whole take.

## Song cut (Suno)

`SONG=path/to/song.m4a python build.py <team>/<name>` makes a music video: the song replaces narration, SFX, and the music bed.
Load the `suno-song` skill for the whole workflow (lyrics, styles, generation, sync).

- The song needs timed lyrics in the file. Suno's m4a exports have them.
- Scenes can have a `lyric=`, the sung version of the line. The engine matches the song against it, or against `narration` when a scene has no lyric. `LYRICS=1` prints the sheet to paste into Suno.
- Each scene needs at least one of its lines sung, in scene order. A scene runs until the next scene's line is sung.

## Sound effects

A scene's `sfx=[(name, offset)]` plays a sound at `offset` into the scene. Every sound goes on something that happens on screen: a click, a dialog, a number landing. Never place a sound at a time that only sounds nice. There are three kinds of offset:

- **Seconds** from the scene's start, for fixed-time entrances. Example: `("whoosh", 0.2)` when a `.screen` starts to rise.
- **`Beat(fraction, delay)`**, for anything the scene's GSAP timeline places at a fraction of `dur`. Examples: `Beat(0.2, 1.6)` when a counter that starts at `0.2 * dur` and runs for 1.6 s lands; `Beat(0.55, 0.1)` when an element that enters at `0.55 * dur` shows up. Use the same fractions as the scene's script.
- **Negative seconds** from the scene's end, for a sting that closes the scene.

For app footage, write the event in **clip time**: `app_clips.scene_time(SCENES, "<scene id>", <seconds in the clip>)` subtracts the scene's `data-media-start`, so trimming a clip moves its sounds with it. To find the event times in a clip, use the moments where the UI visibly changes:

```bash
ffmpeg -i assets/app/02-esocial-envio.mp4 -vf "scale=270:-1,select='gt(scene,0.012)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"
```

A click shows up as the change it causes, such as a dialog opening or a loading state. Re-measure after re-recording a clip, because each recording's timing moves a little.


- The generated sounds are in `engine.gen_sfx()`:
  - `click` for a real cursor click in app footage.
  - `thud` for a card landing.
  - `swoosh` to lead into a cut. Place it at `-0.3` on the scene before the cut.
  - `impact` for a big reveal.
  - `crash` for something collapsing.
  - `buzz` for an error or rejection.
  - `cash` for money landing.
  - `fall` for a number dropping.
  - The older chiptune set: `ding`, `success`, `airhorn`, `riser`, `drumroll` and others.
- Skip sounds on entrances that don't matter, like a card sliding in or a screen rising. A sound on every movement becomes noise.
- To reuse a real sound, cut it with `sb.sound("name", "path/to/file.m4a", start, end, fade_in=..., fade_out=...)`. Then use `"name"` in `sfx` like any other sound.
- The music bed fades out over the last scene.

## A new video

```bash
mkdir -p videos/<team>
cp videos/marketing/economia-inss.py videos/<team>/<name>.py
cp -r videos/marketing/economia-inss-scenes videos/<team>/<name>-scenes   # then replace the compositions
python build.py <team>/<name>
```

## Shared infrastructure

The engine and theme are shared by every video.
A tweak that makes one video better belongs in `engine.py` or the theme, so every video gets it: a new effect, a cleaner block, a better voice setting.
Keep only the story in your `videos/<team>/` script.

Keep the docs honest. If you change the structure, commands, palette, or fonts, update this README and `CLAUDE.md` in the same change.

## Staying on-brand

The theme follows the app and site after the redesign (frontend `app/globals.css`, `components/site/*`). [CLAUDE.md](CLAUDE.md#brand) pins the rules.

## Publishing

Every finished video ships as a GitHub Release asset, kept out of git history. Publish it as the last step of the work, after the storyboard and scenes are committed and pushed:

```bash
gh release create orcamento-obra-v1 orcamento-obra.mp4 poster.png \
  --target "$(git rev-parse HEAD)" \
  --title "Do orçamento à obra reel" \
  --notes "Re-render with: python build.py marketing/orcamento-obra"
```

- A new video starts at `-v1`. Each new render with a visible or audible change gets the next number. `gh release list` shows the numbers in use.
- `--target` ties the tag to the commit that has the video's source.
- Attach the `poster.png` from the same build. Every build makes a new one, so publish before you build another video.
