# legalizareel — agent guide

Short, brand-themed hype and explainer videos for **Legaliza Obra**, rendered headless from HTML. Most are vertical pt-BR reels.
Read [README.md](README.md) first for setup and the build commands.

## Architecture (keep the layers separate)

- `engine.py`: the **brand-agnostic** pipeline. It times the scenes, reads the narration (ElevenLabs take, or Kokoro / edge-tts / `say` per line), times the scenes to a song, and generates the SFX and music bed. Then it writes the root HyperFrames `index.html`, renders, and muxes. Never put brand or story specifics here.
- `themes/legalizaobra.{css,js,py}`: the **brand layer**. The CSS holds fonts, palette, stage variants and blocks. `window.brand` holds the motion helpers. The Python file holds the palette constants and `HF_THEME`. The whole Legaliza Obra look lives here.
- `videos/<team>/<name>.py`: one **story**. It is a `Storyboard` of `scene()`/`flash()` calls handed to `engine.build()`, with its HyperFrames project in `videos/<team>/<name>-scenes/compositions/<scene id>.html`. `marketing/economia-inss` is the reference.
- `app_clips.py`: copies app recordings from the frontend's recorder into `assets/app/` (git-ignored). A storyboard lists the clips it uses and calls `app_clips.ensure([...])` in `main()`.
- `build.py`: the dispatcher. `python build.py <team>/<name>` (default `marketing/economia-inss`).

**Scenes:**
- Each scene is a HyperFrames sub-composition with one paused GSAP timeline.
- It reads its length from `dur`, its camera push from `zoom`, and the frame size from `width`/`height`. Time beats as fractions of `dur`, so both the narrated cut and the song cut line up.
- Every scene ends with `window.brand.camera(...)`, which pushes in on the content and keeps the logo still. Never scale the whole slot: that zooms the logo too.
- Before writing scenes, read `npx hyperframes@0.8.85 docs compositions` / `gsap`, and copy an existing scene's file shape (`videos/marketing/economia-inss-scenes/compositions/obra.html`).

**Frame size:** `build(..., size=VERTICAL)` (1080×1920) is the default. `WIDE` is 1920×1080. Design scenes for the vertical safe area: platform UI covers about the top 250 px and the bottom 400 px of a reel. Keep headlines and numbers between those.

**App footage** comes from the frontend repo's `mock-backend/recording/` (Playwright, 1080×1920, fake cursor, mock data). README → App footage has the commands.
- Frame a clip in `.screen` and animate the `<video>` (`x`, `y`, `scale`, origin at its top-left corner) to pan and zoom onto the moment that matters.
- Never animate `y` on a `.screen`'s children from a theme helper: it fights the video's own pan.
- If the recorder fails, fix the frontend's mock backend or recorder in a PR on the frontend repo. Do not work around it here.

**Rendering:**
- When you change a scene's visuals, re-render (`python build.py <team>/<name>`).
- `SKIP_RENDER=1` only redoes the audio, and it refuses when a scene changed length.
- Iterate on one scene with `npx hyperframes@0.8.85 preview` or `snapshot --at <t>` in the scenes folder, after one render has written `index.html`.
- `npx hyperframes@0.8.85 lint` must report 0 errors.

**Sound effects follow the picture.**
- Every `sfx` sits on a visible event. Use `Beat(fraction, delay)` for the scene's GSAP beats and `app_clips.scene_time(...)` for app-clip events, measured from the clip.
- When a scene and its sounds share timings, pass them with `scene(vars={...})` rather than writing them twice.
- Use sounds for the moments that matter: clicks, reveals, errors, money. Use `swoosh` into a cut. Put no sound on routine entrances.
- After a render, check the sounds against frames taken at each sfx time.
- README → Sound effects has the details.

**Soundtrack:**
- A story passes `voiceover={...}` when `ELEVENLABS_API_KEY` is set. Write that narration as one continuous read.
- The local voices strip v3 tags like `[excited]`, so one narration serves both cuts.
- For a sung cut, load the `suno-song` skill.

## Render-on-demand, never CI

There is **no CI workflow on purpose**. An agent renders locally when the script changes. Don't add GitHub Actions, and don't commit generated media or app recordings. The `.mp4` ships as a Release asset, and `poster.png` is rebuilt on every build.

## Shared by everyone, kept in sync

Improvements belong in the engine or the theme, not copy-pasted per video. When you catch yourself special-casing the engine for one video, generalize it instead.

Keep `README.md` and this file in sync with reality. If you change the structure, commands, palette, or fonts, update both in the same change.

## Brand

The source of truth is the frontend: `app/globals.css` (tokens), `app/layout.tsx` (fonts), `components/site/*` (the marketing site), `lib/site-content.ts` (claims). Match it, and re-check it when the site changes.

### Palette

| Role | Hex |
| --- | --- |
| Brand teal (primary; hero and CTA panels) | `#1F514C` |
| Teal 2 | `#2A5F59` |
| Deep teal (frames, dark stage) | `#102C29` |
| Mint (tint, highlight on teal) | `#EDFFE3` / `#DAF5CB` |
| Soft mint (sublines on teal) | `#CFE3DF` |
| Background / surface | `#FFFFFF` / `#F5F8F7` |
| Text | `#141414` |
| Warning (the "cost is high" number only) | `#DC8F1F` |
| Danger (eSocial errors and rejections only) | `#B42318` on `#FEF1F0` |

- Teal is the brand. A teal stage takes white headlines, `#CFE3DF` sublines and mint highlights, like the site's hero.
- Use only the solid colours above. No gradients, and don't add new hues.

### Type

- **Hedvig Letters Serif** for headlines and big numbers. Weight 400, tight letter-spacing (−0.02em).
- **Inter** for body text, labels and pills.
- Both are bundled in `assets/fonts/` (OFL). Headings use sentence case.

### Logo

- Use `assets/brand/logo.png`, the official lockup. It is teal on transparent.
- On white or surface stages, show it bare. On teal, put it on a white pill (`.logo-pill`) or card, because there is no white logo.
- Never recolour, stretch, or animate it beyond a fade or pop in. Never rebuild the lockup from the icon plus hand-set text.

### Claims (be honest)

- The site's headline claim is **"até 73%"** (`MAX_SAVINGS_PERCENT` in `lib/site-content.ts`). Always say "até". Never say or imply a guaranteed rate.
- Show real numbers from the mock showcase data (Residência Andrade: INSS R$ 81.141 → R$ 47.251, R$ 33.890 saved, 41.8%). Say that it is "nessa obra".
- Don't use the calculator page's "R$ 2M+ economizados" or "500+ obras" stats. Nothing else in the code backs them.

### Tom de voz (narration + on-screen copy)

- Brazilian Portuguese, spoken like a clear, friendly specialist talking to a builder or an accountant. Use short sentences and the active voice. Lead with the benefit: paying less INSS, legally, without spreadsheets.
- Use the product's own words: obra, pedreiros, eSocial, guia DARF, simulação, orçamento.
- Cut filler words: "revolucionário", "inovador", "solução completa", "otimize seus processos".
- Name the product **Legaliza Obra** in narration (the logo says "legalizaobra").

### Animation

The videos are intentionally **hype**: punch zooms, flashes, chiptune SFX. That's the format. Keep that energy in promo videos only, never in the product UI.

## Python style

Boring and readable. Annotate signatures, keep imports at module level, order helpers before callers. Match the surrounding code.
