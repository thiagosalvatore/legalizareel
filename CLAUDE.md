# hogreel — agent guide

Short, brand-themed hype/explainer videos for PostHog skills, rendered headless from HTML.
Read [README.md](README.md) for setup and the build commands first.

## Architecture (keep the layers separate)

- `engine.py` — **brand-agnostic** pipeline: HTML scenes → frames → clips → concat → mux, plus TTS and SFX. Never put brand or story specifics here.
- `themes/posthog.py` — the **brand layer**: CSS, `page()` chrome, hedgehog helpers, palette. All PostHog look lives here. A different brand = a sibling theme module with the same surface.
- `videos/<team>/<name>.py` — one **story**: a `Storyboard` of `scene()`/`flash()` calls handed to `engine.build()`. Videos are sorted by owning team; a new video is a new file in your team's folder, nothing else.
- `build.py` — dispatcher: `python build.py <team>/<name>` (default `devex/facade`).
- **HyperFrames scenes (the default for new videos; `devex/postpile` is the reference)** — a storyboard can pass `hyperframes=<dir>` to `build()`. Each scene is then a HyperFrames sub-composition `<dir>/compositions/<scene id>.html` with its own GSAP timeline, and the engine writes the root `index.html` (generated, gitignored) and renders with the pinned `hyperframes` CLI. Timing, TTS, song sync and the audio mix are unchanged. The brand for this path is `themes/posthog.css` + `themes/posthog.js` (`HF_THEME`), linked into the project at render time. Scenes read their length from the `dur` variable and time beats as fractions of it, so both the narrated and the song cut line up. The storyboard `effect` reaches the scene as the `zoom` variable; every scene ends with `window.brand.camera(...)`, which pushes in on the content and keeps the logo and badge still (never scale the whole slot: that zooms the chrome). Before writing scenes, read the HyperFrames rules: `npx hyperframes@0.8.85 docs compositions` / `gsap`, and copy an existing scene's file shape (`videos/devex/postpile-scenes/compositions/pile.html`).

When you change a scene's visuals, you must re-render (`python build.py <team>/<name>`) — frames are captured, not live. Use `SKIP_RENDER=1` only when you changed audio/timing but not visuals. `SONG=<file>` swaps narration for a song with embedded timed lyrics and re-times scenes to it (see README), so it always needs a full render. For sung versions, load the `suno-song` skill (`.claude/skills/suno-song/SKILL.md`): scenes carry an optional `lyric=` for the song, and `LYRICS=1` prints the Suno sheet. Keep `narration` for the spoken TTS cut. A story can pass `voiceover={...}` to `build()` to read the narration as one ElevenLabs take instead (see README → Voiceover); write that narration as one continuous read. That's the default soundtrack for feature and launch reels; a Suno song is for music reels, Kokoro is the free local fallback. The ElevenLabs account is shared and has 10,000 characters a month (a take is ~1,500): audition voices on a line or two, and prefer edits the engine can cut from a cached take (drop a scene, trim a line to a phrase the take already says) over re-reads.

On the HyperFrames path there's no frame cache. `SKIP_RENDER=1` keeps the last rendered `video_hf.mp4` and only redoes the audio, which only works when no scene changed length (it refuses otherwise); any visual or timing change re-renders. To iterate on one scene's visuals, render once (writes `index.html`), then run `npx hyperframes@0.8.85 preview` in the scenes folder for live reload, or `npx hyperframes@0.8.85 snapshot --at <t>` for stills. `npx hyperframes@0.8.85 lint` must report 0 errors.

## Render-on-demand, never CI

The toolchain is ~1 GB to produce a ~9 MB file. There is **no CI workflow on purpose** — an agent renders locally when the script changes. Don't add GitHub Actions, don't commit generated media. The `.mp4` ships as a Release asset and `poster.png` regenerates each build — nothing generated is committed.

## Shared by everyone, kept in sync

The engine and theme are shared by every team. Improvements belong there, not copy-pasted per video — a better effect, caption, transition, or voice setting should lift everyone's output, not just one team's. Put only team and story specifics in `videos/<team>/<name>.py`; when you catch yourself special-casing the engine for a single video, generalize it instead.

Keep `README.md` and this file in sync with reality. If you change the structure, commands, palette, or fonts, update both in the same change — never leave the docs stale.

## Brand compliance

The canonical source is `~/workspace/posthog.com/contents/handbook/brand/` (visual-identity, tone, assets) — read it when in doubt; this section only pins the load-bearing, stable rules. The north-star test: **remove the logo — does it still feel like PostHog?** It should. Handcrafted beats generated.

### Palette — exact hex, and it's deliberately small

| Role | Light | Dark |
| --- | --- | --- |
| Background / opposite-mode text | `#EEEFE9` | `#151515` |
| Red (brand color, *not* a status color) | `#F54E00` | same |
| Blue (primary accent) | `#1D4AFF` | same |
| Yellow | `#DC9300` | `#F1A82C` |
| Gray | `#BFBFBC` | same |

- **There is no brand green.** Don't reach for green/teal as a "success/good" color — that's the status-indicator habit the brand avoids. Use blue for the positive accent, or opacity, before any new hue.
- More colors = each means less. Modify with **opacity**, don't add hues. No gradient backgrounds (solid only). No rainbow palettes.

### Type

- **Open Runde** — body and headings. Weights 400/500/600/700. Loaded by posthog.com via Cloudinary (URLs in `posthog.com/src/components/Layout/Fonts.css`); bundle the woff2 into `assets/fonts/` for offline, deterministic capture.
- **Squeak** — expressive display font for marketing headlines. Bundled at `posthog.com/static/fonts/squeak-bold-webfont.woff2`. Rules: **always uppercase, always bold, only with hedgehog art**, letter-spacing −2%, line-height 100%. Never for body/subtitles, never without a hog.
- **Loud Noises** — only for text a hedgehog is holding/saying (signs, speech bubbles), uppercase.
- Monospace (Menlo) is fine for code blocks. No other decorative fonts. Headings are **sentence case** (Squeak's all-caps is the one exception).

### Logo

- Use the official SVG. **White wordmark (`posthog-logo-white.svg`) on dark/colored backgrounds; standard (`posthog-logo.svg`) on light. Never the standard logo on dark.** `page()` already picks the variant from the `dark` flag.
- Never modify logomark colors. **Never pair the bare logomark with hand-set "PostHog" text** — use the real logo lockup. Don't stretch/skew/rotate/add effects. Don't animate the logo (spin/bounce/glitch); a gentle fade-in to a still frame is fine. Full logo min 80px wide (else logomark only); keep clear space ≈ the height of the "P".

### Hedgehogs (Max)

- **Official art only** (art library / press page assets in `assets/`). **Never AI-generated hogs**, never modify existing ones, no competitor/derivative styles. Use them to express a point, not just to fill space.

### Tone (narration + on-screen copy)

- Explain it to a smart friend: clear, simple, specific, direct, **honest including about limitations**, conversational.
- Cut hedge/weasel words — leverage→use, utilize→use, streamline→speed up, plus seamless / robust / best-in-class / holistic / synergy. Active voice. Lead with the benefit, not the feature. No forced humor (clear beats clever; let the genuine jokes land).
- Product names in **Sentence case** ("Product analytics", "Visual review"), not Title Case.

### Animation — the one deliberate deviation

The brand default is *understated* (animate-in then settle, don't loop). These videos are intentionally **hype** — punch zooms, flashes, chiptune SFX, comedic stings. That's the format and it's on purpose. Keep that energy scoped to promo videos; never carry it into product UI. (The idle hedgehog bob is the mildest nod to "bring characters to life.")

## Python style

Boring and readable. Annotate signatures, keep imports at module level, order helpers before callers. Match the surrounding code.
