---
name: suno-song
description: Make a sung soundtrack for a legalizareel video with Suno and render the music-video cut. Covers writing per-scene `lyric=` lines for a music reel, generating the paste-ready lyrics sheet (LYRICS=1), Suno style/exclude/duration settings, delivery and pacing tags, the team style library, and syncing the downloaded song back to the scenes (SONG=...). Use when asked for a song, Suno lyrics or style prompts, a music-video or sung version of a video, or when a Suno .m4a shows up.
---

# Suno song for a legalizareel video

The song replaces TTS narration, SFX, and the music bed. Scenes are timed to the timed lyrics Suno embeds in its downloads, so the lyrics in Suno and the `lyric=` lines in the storyboard have to agree.

## Workflow

1. **Write lyrics in the storyboard.** Give each `scene()` a `lyric="..."` (see "Writing for a music reel" below). The spoken `narration=` stays for the TTS cut. Don't change it for the song.
2. **Print the sheet:** `LYRICS=1 python build.py <team>/<name>`. It prints every scene's lyric in order and exits without rendering. Scenes without `lyric` fall back to their narration. Paste the output into Suno's Lyrics box as-is.
3. **Suno settings** (Custom mode, V5.5 or newer):
   - Style: start from `videos/<team>/suno-styles.md` when the team has one.
   - Exclude styles: `long intro, instrumental outro, fade out, extended chorus`.
   - Duration slider: about the video length +10%. Get it from a plain render's `total_seconds` or `ffprobe` of the last mp4. The slider is a target, not exact, so crop the rest afterwards.
4. **Download the .m4a.** Suno's m4a keeps a timed-lyrics subtitle track (`mov_text`), which the engine reads. Check with `ffprobe <file>`: there should be a subtitle stream. Other formats may not have it.
5. **Render:** `SONG="<path>.m4a" python build.py <team>/<name>` → `<name>-song.mp4`. Always a full render (no `SKIP_RENDER`), because scene lengths change. `SHORT=1` also works for a sung teaser.
6. **Verify:**
   - The printed `scenes` durations look sane: no 0.07s scenes, and no giant hold except where a chorus is meant to hold.
   - Where the song ends: `ffmpeg -ss <t> -i <out>.mp4 -vn -af silencedetect=noise=-50dB:d=1 -f null - 2>&1 | rg silence_`. Silence before the last scene means the song is too short or a scene's line didn't match.

## How sync works (the rules lyrics must follow)

- A lyric line starts scene N+1 when it's contained in scene N+1's sung text (punctuation and case ignored). Lines found in neither the current nor the next scene only hold the current scene, which is how choruses and ad-libs work.
- So **every scene needs at least one sung line, in scene order.** A skipped scene stalls the matching and everything after it goes silent.
- **Don't reuse the next scene's words in a chorus**, or the video jumps ahead early.
- The first scene always starts at 0, so a long Suno intro just holds the first scene.
- The song usually ends at `[End]`. Scenes it never reaches keep `min_dur` and play silent, which is a visible cue to regenerate longer.
- Put the chorus in the `lyric` of the scene whose card should stay on screen during it, usually the payoff card.
- **Instrumental stretches get filler scenes**: a scene with neither `lyric` nor `narration` takes its `min_dur` out of the sung scene before it, leaving the next sung line on its own frame. Use them wherever a card would otherwise hold for more than ~5s, and put the facts the song had no room for on them.
- **Short cards need fast entrances**: scenes time their beats as fractions of `dur`, but the theme's entrances (`upIn`, `floatIn`) have fixed lengths tuned for 3-4s narrated scenes. On a 1-2s music card, start them at `at = 0` and shorten the stagger, or the last element is still arriving when the scene cuts.
- **A take that runs long** (the last line lands, then minutes of hook): end the video by ear with `SONG_END=<m:ss>`. Split the payoff into two cards (the numbers, then the brand) so the last chorus holds on a card made for holding, and give that card a late beat for the sign-off.
- **The lyric track can omit lines Suno actually sang.** Towards the end of a take it often degrades into placeholder spans of several seconds, and a short outro chop may have no entry at all. When the user reports hearing something the track doesn't list, believe the user: place that card by the clock instead, using fixed `min_dur`s on the filler scenes that lead up to it, and write the arithmetic down so one number can be nudged later.

## Writing for a music reel

- **One idea per scene, 1–3 short lines.** Sung lines take about twice as long as spoken ones, so cut words hard.
- **Echo the on-screen big text.** Viewers read and hear the same words, which lands better than paraphrasing.
- Rhythm beats grammar: fragments are fine ("No walls. CI runs everything."). Aim for similar syllable counts within a verse.
- **One hook, used twice at most:** once after the title card and once over the payoff. No repeated chorus after the last line.
- Tone rules still apply (see CLAUDE.md, "Tom de voz"): honest claims ("até 73%", never "73% garantido"), no filler words, sentence case.
- End on the sign-off and `[End]`. A stuttered call ("Le-le-Legaliza Obra") works as the last ad-lib line.

## Varying the voice within one song

A reel reads better when the delivery changes with the job of the scene. Suno does this from the section tags, so no engine work is needed:

- **Explainer beats** (how it works, what it does): `[Verse: spoken, dry, no melody, clear diction]`. Keep the lines plain and literal, and don't rhyme them — this is where the viewer actually learns something.
- **Praise beats** (the payoff, the hook, the sign-off): `[Chorus: funky, sung, falsetto ad-libs, full groove]`. Short, repeatable, and fine to be over the top.
- Alternating spoken verse and sung chorus is the default shape. Say "spoken-word verses, sung chorus" in the style prompt too, because the tags land better when the style agrees with them.
- If a take sings a line that must be understood, regenerate or use Quick Replace on that section. Suno respects the delivery tags better when the section is short.
- The engine doesn't mix TTS with a song — in song mode the track is the whole soundtrack. Getting the spoken parts clear is a Suno problem, not a render problem.

## Tags cheat sheet (hints, not guarantees)

- Section plus delivery in one tag, on its own line before the section: `[Verse 1: spoken-sung, vocals start immediately, no intro]`, `[Break: beat drops out, spoken]`, `[Hook: doubled vocal, filter opens]`, `[Outro: short, stuttered vocal chop]`, `[End]`.
- Delivery words that work: spoken, spoken-sung, talk-sung, clipped, whispered, belted, doubled vocal, stuttered vocal chops.
- **Tempo** is global: BPM in the style. Suno has no per-line speed control. Line breaks and short lines slow the delivery down, `...` adds a held pause, and hyphenated-words get rushed.
- **Long intro:** don't open with a bare `[Intro]` (Suno reads it as instrumental). Open with a vocal section tagged "no intro", exclude "long intro", and crop or Quick Replace the start in Suno's editor if it still drags.
- **Won't stop:** `[End]` right after the last line, plus the exclude list. Otherwise crop in the editor (Pro/Premier: ⋮ → Edit → Crop Song).

## Iterating on a style without going in circles

Suno samples differently on every generation, so a single take never tells you whether a
prompt is good. And a style string is a bag of competing pulls: rewriting several parts at
once makes the result unattributable.

- Keep a **locked base string** in the team's style file. Copy it and change **one axis** per
  generation: tempo, drum weight, vocal character, genre label, or mix polish.
- Take **two generations per prompt** before judging it.
- **Log what each prompt produced**, including the bad ones and the word you think caused it.
- When the user says "like X but harder/faster", change only the tempo or drum words. Genre
  labels (`bloghouse`, `electro`, `big room`) and grit words (`distorted`, `crunchy`,
  `gang-shouted`, `aggressive`) change the vocal character too, which is rarely what they
  asked for.
- **Once a take has a vocal worth keeping, make a Persona from it** (`...` → Create → Make a
  Persona). A Persona captures the vocals, energy and atmosphere, and you then supply entirely
  new lyrics and a new style. It's the only route to "same voice, different words". Pro/Premier,
  and in beta at the time of writing — confirm it's on the account before promising it.
- **Remix cannot do that, and saying otherwise wastes the user's credits.** Remix is an umbrella
  over Cover, Extend, Reuse and Speed. Cover replaces the vocal identity, Extend only continues
  the existing audio from a timestamp, Reuse just refills the prompt box. None of them take a
  new lyric sheet while holding the vocal, so a Remix aimed at new lyrics returns a mild rework
  of the old song.
- **Check a Suno feature before building a workflow on it.** The names shift between versions
  and third-party guides conflate them (Persona vs Lyricist vs Voices especially). Suno's own
  blog and help pages are the authority.
- Record variants **written out in full**, never as "the base plus this phrase" — the shorthand
  is how a string that was never actually generated ends up logged as the winner.

## Club and DJ cuts (not reels)

A standalone club edit — chanted hooks, no narration — is a different deliverable, and two
things invert:

- **No sync.** There's no per-scene line, so there's nothing for the engine to match. It never
  goes through `SONG=`; it's a Suno artifact that lives in the style file.
- **The exclude list flips.** `long intro`, `instrumental outro`, `instrumental break`,
  `instrumental drop` and `extended chorus` exist to stop a *reel* take from drifting into dead
  air. In a club cut they'd ban the breakdown, the drop and the looping hook. Drop them and
  keep only the vocal and ending guards.

Suno won't reach true DJ length (~5 min with 32 bars of beat-only at each end) in one
generation; that needs Extend. Say so before promising it.

## Style library

- Per team: `videos/<team>/suno-styles.md`. Record what worked and why (narration clarity vs tune), and combine from there.
- Style prompt pattern: genre, BPM, production texture, vocal description (gender, language, delivery, hook), groove, instruments, mix, "vocals start right away, ends cleanly".
