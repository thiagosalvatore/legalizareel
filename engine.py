#!/usr/bin/env python3
"""Brand-agnostic video engine: HyperFrames scenes + narration + SFX -> mux.

A video script builds a `Storyboard` (a list of scenes + flashes) and hands it to
`build(...)`. The engine times the scenes, synthesizes narration (Kokoro neural TTS,
edge-tts / `say` fallbacks, or one ElevenLabs voiceover take when the story passes
`voiceover=`), generates the SFX + music bed, renders the scenes with HyperFrames and
muxes the final mp4. It knows nothing about a brand: the look comes from the theme
files and the scene compositions a story passes in.

Narration markers: "[[slnc N]]" inserts N ms of silence between spoken chunks. Each
chunk is synthesized as ONE utterance for natural prosody; intonation is directed via
punctuation and the placement of those pauses, never by splicing individual words.

Env toggles (read by build):
  SHORT       keep only `short_keep` scene ids, suffix output with -40s
  SKIP_RENDER reuse the last rendered video (use when only audio changed)
  SONG        path to a song with timed lyrics (Suno export): replaces narration + SFX,
              scenes are timed to the lyric lines, suffix output with -song
  LYRICS      print the paste-ready Suno lyrics sheet (scene `lyric`s) and exit, no render
  SONG_END    with SONG: end the video here (seconds or m:ss) instead of at the song's end,
              for a take that keeps going after its last line
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / "audio"
SFX = AUDIO / "sfx"
for d in (AUDIO, SFX):
    d.mkdir(parents=True, exist_ok=True)

FPS = 30
VERTICAL = (1080, 1920)
WIDE = (1920, 1080)
SR = 44100
LEAD = 0.10  # narration starts slightly after the visual cut
TAIL = 0.28  # breathing room after the line
NARR_VOICE = "pt-BR-AntonioNeural"  # edge-tts neural voice (single knob for all narration)
EDGE_BASE = ("-5%", "+0Hz", "+0%")  # (rate, pitch, volume) for normal speech
SAY_FALLBACK_VOICE = "Luciana"  # offline fallback if edge-tts is unreachable
SAY_FALLBACK_RATE = "165"
# Kokoro neural TTS (local, free) — primary engine; edge-tts is the fallback.
KOKORO_PY = ROOT / ".tts-venv" / "bin" / "python"
KOKORO_VOICE = "pm_alex"  # pm_alex | pm_santa | pf_dora
KOKORO_LANG = "p"
KOKORO_SPEED = 1.05  # speaking speed (Kokoro's only prosody knob)


# ----------------------------------------------------------------------------- storyboard
class Storyboard:
    """Ordered list of scenes/flashes a video script fills in.

    scene(**kw): html body, narration, voice, sfx [(name, offset)], effect, min_dur,
                 and optional lyric (song version of the line, may hold [Section] tags).
                 A negative sfx offset counts back from the scene's end.
    flash(color, dur, sfx): a single-color cut between scenes.
    sound(name, source, start, end, fade_in, fade_out): a sound cut from a file (e.g. a
                 sung sting from a song), usable in sfx= like the generated ones.
    HyperFrames only: scene(blend=N) cross-fades into the scene over its first N seconds
                 instead of cutting.
    """

    def __init__(self):
        self.scenes = []
        self.sounds = {}

    def scene(self, **kw):
        kw["kind"] = "scene"
        self.scenes.append(kw)

    def flash(self, color, dur=0.066, sfx=None):
        self.scenes.append({"kind": "flash", "color": color, "dur": dur, "sfx": sfx or []})

    def sound(self, name, source, start, end, fade_in=0.01, fade_out=0.03):
        self.sounds[name] = (Path(source), start, end, fade_in, fade_out)


# ----------------------------------------------------------------------------- ffmpeg helpers
def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def dur_of(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    val = out.stdout.strip()
    return float(val) if val not in ("", "N/A") else 0.0


# ----------------------------------------------------------------------------- 3. TTS + durations
# Trim silence off both ends of a fragment (Kokoro adds lead-in; edge adds tail).
_TRIM = ("silenceremove=start_periods=1:start_threshold=-50dB,"
         "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse")


def _tokens(text):
    # Split only on [[slnc N]] so each spoken chunk is a full utterance (natural prosody).
    # "*" markers are stripped — emphasis is carried by punctuation, not by splicing words.
    out = []
    for k, part in enumerate(re.split(r"\[\[slnc (\d+)\]\]", text)):
        if k % 2 == 1:
            out.append(("sil", int(part)))
        else:
            seg = part.replace("*", "").strip()
            if seg:
                out.append(("txt", seg))
    return out


def _espeak_env():
    env = dict(os.environ)
    hits = sorted(Path("/opt/homebrew/Cellar/espeak-ng").glob("*/share/espeak-ng-data"))
    if hits:
        env["ESPEAK_DATA_PATH"] = str(hits[-1])
    return env


def _finalize_raw(raw_wav, out_wav):
    """24 kHz Kokoro utterance -> 44.1 kHz stereo, silence trimmed off both ends."""
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav), "-af", _TRIM,
         "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)])


def _edge_fragment(text, out_wav, voice):
    rate, pitch, vol = EDGE_BASE
    mp3 = AUDIO / "_frag.mp3"
    run(["uvx", "edge-tts", "--voice", voice, f"--rate={rate}", f"--pitch={pitch}",
         f"--volume={vol}", "--text", text, "--write-media", str(mp3)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", _TRIM,
         "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)])


def _say_fragment(text, out_wav):
    aiff = AUDIO / "_frag.aiff"
    subprocess.run(["say", "-v", SAY_FALLBACK_VOICE, "-r", SAY_FALLBACK_RATE, text, "-o", str(aiff)], check=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-af", _TRIM,
         "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)])


def _plan_scene(s):
    """Tokenize a scene into [('sil', ms) | ('txt', frag_wav)] and collect its synth jobs."""
    plan, jobs, i = [], [], 0
    for tok in _tokens(s["narration"]):
        if tok[0] == "sil":
            plan.append(("sil", tok[1]))
            continue
        seg = tok[1]
        frag = AUDIO / f"_frag_{s['id']}_{i}.wav"
        raw = AUDIO / f"_raw_{s['id']}_{i}.wav"
        jobs.append({"text": seg, "frag": frag, "raw": raw})
        plan.append(("txt", frag))
        i += 1
    return plan, jobs


def kokoro_spec(all_jobs):
    return [{"text": j["text"], "voice": KOKORO_VOICE, "lang": KOKORO_LANG, "speed": KOKORO_SPEED,
             "out": str(j["raw"])} for j in all_jobs]


def _synth_all(all_jobs):
    """Synthesize every utterance. Kokoro batch (one model load) when available, else edge."""
    if KOKORO_PY.exists():
        jf = AUDIO / "_kokoro_jobs.json"
        jf.write_text(json.dumps(kokoro_spec(all_jobs)))
        subprocess.run([str(KOKORO_PY), str(ROOT / "kokoro_batch.py"), str(jf)],
                       check=True, env=_espeak_env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for j in all_jobs:
            _finalize_raw(j["raw"], j["frag"])
        return
    for j in all_jobs:
        try:
            _edge_fragment(j["text"], j["frag"], NARR_VOICE)
        except Exception:
            _say_fragment(j["text"], j["frag"])


def _assemble_scene(s, plan, out_wav):
    """Stitch a scene's fragments + silences; return start time of the last spoken fragment."""
    pieces, cur, last, idx = [], 0.0, 0.0, 0
    for tok in plan:
        if tok[0] == "sil":
            piece = AUDIO / f"_sil_{s['id']}_{idx}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                 "-i", f"anullsrc=r={SR}:cl=stereo", "-t", f"{tok[1] / 1000:.3f}",
                 "-c:a", "pcm_s16le", str(piece)])
            cur += tok[1] / 1000
            pieces.append(piece)
        else:
            frag = tok[1]
            last = cur
            cur += dur_of(frag)
            pieces.append(frag)
        idx += 1
    if not pieces:  # silent scene (e.g. a cover card) — emit a short silence track
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", f"anullsrc=r={SR}:cl=stereo", "-t", "0.10", "-c:a", "pcm_s16le", str(out_wav)])
        return 0.0
    lst = AUDIO / f"_list_{s['id']}.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in pieces))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(out_wav)])
    return last


def tts_and_durations(S):
    plans, all_jobs = {}, []
    for s in S:
        if s["kind"] != "scene":
            s["frames"] = max(2, round(s["dur"] * FPS))
            s["dur"] = s["frames"] / FPS
            continue
        plan, jobs = _plan_scene(s)
        plans[s["id"]] = plan
        all_jobs += jobs
    _synth_all(all_jobs)
    for s in S:
        if s["kind"] != "scene":
            continue
        wav = AUDIO / f"{s['id']}.wav"
        s["_lastseg"] = _assemble_scene(s, plans[s["id"]], wav)
        ttsd = dur_of(wav)
        target = max(s["min_dur"], LEAD + ttsd + TAIL)
        s["frames"] = round(target * FPS)
        s["dur"] = s["frames"] / FPS
        s["tts"] = ttsd


# ----------------------------------------------------------------------------- 3a. one-take voiceover (ElevenLabs)
# build(..., voiceover={...}) reads the whole narration as ONE take instead of a take per
# line, so it flows through the reel like a real voiceover, with the model picking the
# pace. The per-character timestamps ElevenLabs returns cut the take back into one chunk
# per scene. Takes are cached by text + voice settings, so rebuilding costs no credits.
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128"
VO_CACHE = AUDIO / "voiceover"
# Voice models breathe long between sentences (~30s of a 2 min take): every pause gets
# capped at VO_MAX_PAUSE, as a VO editor would, so the read stays quick without speeding
# up the words.
VO_MAX_PAUSE = 0.3


def _vo_line(s):
    """A scene's part of the take: [[slnc]] markers dropped, punctuation carries the pauses."""
    return re.sub(r"\s+", " ", re.sub(r"\[\[slnc \d+\]\]", " ", s["narration"])).strip()


def _word_chars(line):
    """Indexes of the letters and digits in a line, skipping audio tags like [excited]."""
    out, in_tag = [], False
    for i, ch in enumerate(line):
        if ch == "[":
            in_tag = True
        elif ch == "]":
            in_tag = False
        elif ch.isalnum() and not in_tag:
            out.append(i)
    return out


def _take_key(text, voiceover):
    return hashlib.sha256(json.dumps([text, voiceover], sort_keys=True).encode()).hexdigest()[:16]


def _line_spans(lines, text):
    """Where each line sits in a take's text, in order: [(start, end)], or None if one is missing."""
    spans, cursor = [], 0
    for line in lines:
        at = text.find(line, cursor)
        if at < 0:
            return None
        spans.append((at, at + len(line)))
        cursor = at + len(line)
    return spans


def _cached_take(lines, voiceover):
    """The newest cached take of this voice that already says every line, in order.

    Returns (mp3, alignment, spans) or None. Dropping a scene, or trimming a line to a
    phrase the take already says, then costs no credits and keeps the delivery. A cache
    file only counts when its name is the key of its own text and this voice, so a take
    in another voice or with other settings never matches.
    """
    for timing in sorted(VO_CACHE.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        alignment = json.loads(timing.read_text())
        text = "".join(alignment["characters"])
        spans = _line_spans(lines, text)
        if spans and timing.stem == _take_key(text, voiceover):
            return timing.with_suffix(".mp3"), alignment, spans
    return None


def _synthesize(text, voiceover):
    """Read `text` as one ElevenLabs take into the cache; return (mp3, alignment)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("the voiceover needs ELEVENLABS_API_KEY (see README)")
    body = {"text": text, "model_id": voiceover["model"], "voice_settings": voiceover.get("settings", {})}
    request = urllib.request.Request(
        ELEVEN_URL.format(voice=voiceover["voice"]), data=json.dumps(body).encode(),
        headers={"xi-api-key": api_key, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.load(response)
    except urllib.error.HTTPError as err:  # e.g. 401 for a bad key or when the credits run out
        raise SystemExit(f"ElevenLabs said {err.code}: {err.read().decode()[:400]}") from err
    key = _take_key(text, voiceover)
    VO_CACHE.mkdir(parents=True, exist_ok=True)
    mp3 = VO_CACHE / f"{key}.mp3"
    mp3.write_bytes(base64.b64decode(data["audio_base64"]))
    (VO_CACHE / f"{key}.json").write_text(json.dumps(data["alignment"]))  # written last: marks the take complete
    return mp3, data["alignment"]


def _tighten(wav):
    """Cap every pause in a wav at VO_MAX_PAUSE, keeping half of it on each side."""
    out = subprocess.run(["ffmpeg", "-i", str(wav), "-af", "silencedetect=noise=-38dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    begins = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", out)]
    if len(ends) < len(begins):  # the pause before the next scene runs to the end of the chunk
        ends.append(dur_of(wav))
    keep = VO_MAX_PAUSE / 2
    cuts = [f"between(t,{b + keep:.3f},{e - keep:.3f})" for b, e in zip(begins, ends) if e - b > VO_MAX_PAUSE]
    if not cuts:
        return
    tight = wav.with_name(f"_tight_{wav.name}")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
         f"aselect='not({'+'.join(cuts)})',asetpts=N/SR/TB", "-c:a", "pcm_s16le", str(tight)])
    tight.replace(wav)


def voiceover_durations(S, voiceover):
    """Time scenes to one voiceover take: a scene runs from just before its first word to
    just before the next scene's, so the pauses the voice makes stay where it made them.

    A scene whose chunk is shorter than its min_dur holds on silence for the rest.
    """
    spoken = [s for s in S if s["kind"] == "scene" and _vo_line(s)]
    lines = [_vo_line(s) for s in spoken]
    take = _cached_take(lines, voiceover)
    if take is None:
        text = " ".join(lines)
        mp3, alignment = _synthesize(text, voiceover)
        spans = _line_spans(lines, text)
    else:
        mp3, alignment, spans = take
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    words = _word_chars("".join(alignment["characters"]))  # every spoken character of the take

    def cut_before(i):
        """Just before the word at char i, but after the take's word before it."""
        before = [w for w in words if w < i]
        return max(ends[before[-1]] + 0.02, starts[i] - LEAD) if before else 0.0

    chunks = {}
    for k, (s, (a, b)) in enumerate(zip(spoken, spans)):
        inside = [w for w in words if a <= w < b]
        after = [w for w in words if w >= b]
        if not after:
            end = dur_of(mp3)
        elif k + 1 < len(spans) and not [w for w in words if b <= w < spans[k + 1][0]]:
            end = cut_before(after[0])  # the next scene picks up right here: share the cut
        else:  # the take says more here that the storyboard dropped: stop after a short breath
            end = min(ends[inside[-1]] + VO_MAX_PAUSE, starts[after[0]])
        chunks[s["id"]] = (cut_before(inside[0]), end)
    for s in S:
        if s["kind"] == "scene" and s["id"] in chunks:
            begin, end = chunks[s["id"]]
            wav = AUDIO / f"{s['id']}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ss", f"{begin:.3f}",
                 "-to", f"{end:.3f}", "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
            _tighten(wav)
            s["tts"] = dur_of(wav)
            s["_lead"] = 0.0  # the chunk already starts just before the first word
            target = max(s["min_dur"], s["tts"])
        elif s["kind"] == "scene":
            wav = AUDIO / f"{s['id']}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=stereo",
                 "-t", "0.10", "-c:a", "pcm_s16le", str(wav)])
            target = s["min_dur"]
        else:
            target = s["dur"]
        s["frames"] = max(2, round(target * FPS))
        s["dur"] = s["frames"] / FPS


# ----------------------------------------------------------------------------- 3b. song mode (SONG=...)
def _norm(text):
    """Match key for a line: drop [production cues], keep only letters and digits."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\[[^\]]*\]", " ", text).lower())


def _sung_text(s):
    """What the song sings for a scene: its `lyric` minus [Section] tags, else the narration."""
    if s.get("lyric"):
        return " ".join(line for line in s["lyric"].splitlines() if not line.strip().startswith("["))
    return re.sub(r"\[\[slnc \d+\]\]", "", s["narration"])


def lyric_sheet(S):
    """Paste-ready Suno lyrics: every scene's `lyric` (narration as fallback), in scene order."""
    rows = []
    for s in S:
        if s["kind"] != "scene":
            continue
        for line in (s.get("lyric") or _sung_text(s)).strip().splitlines():
            line = line.strip()
            if line.startswith("[") and rows:
                rows.append("")
            rows.append(line)
    return "\n".join(rows)


def read_song_lyrics(song):
    """Timed lyric lines [(start_seconds, text)] from the song's embedded subtitle track."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(song), "-map", "0:s:0", "-f", "srt", "-"],
        check=True, capture_output=True, text=True,
    )
    lines = []
    for block in out.stdout.replace("\r", "").strip().split("\n\n"):
        rows = block.splitlines()
        if len(rows) < 3:
            continue
        h, m, rest = rows[1].split(" --> ")[0].split(":")
        sec, ms = rest.split(",")
        text = " ".join(rows[2:]).strip()
        if text.startswith("["):  # section tags like [Verse 1]
            continue
        lines.append((int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000, text))
    return lines


def _seconds(value):
    """'142.5' or '2:22.5' -> seconds."""
    minutes, _, seconds = value.rpartition(":")
    return int(minutes or 0) * 60 + float(seconds)


def song_durations(S, song):
    """Time scenes to a song: each sung scene runs until the next sung scene's first lyric.

    A lyric line that's part of the next scene's narration starts that scene. Lines found
    in neither the current nor the next scene (chorus, ad-libs) just extend the current
    one, so the song can shorten narration and add hooks as long as every scene keeps at
    least one exact phrase, in order. The last card ends at the first line the song sings
    that no card can take (Suno's auto length pads with repeats), else at the song's end.

    A scene with neither lyric nor narration is a filler for an instrumental stretch: it
    takes its min_dur out of the sung scene before it, leaving the next sung line on its
    own frame. Scenes the song doesn't reach keep min_dur and play silent, so the gap
    shows how much song is still missing.
    """
    lyrics = read_song_lyrics(song)
    # only scenes with something to sing are matched; the rest are instrumental fillers
    scenes = [s for s in S if s["kind"] == "scene" and _sung_text(s).strip()]
    texts = [_norm(_sung_text(s)) for s in scenes]
    starts, tail, cur = {}, None, -1
    for start, line in lyrics:
        words = _norm(line)
        if not words or (cur >= 0 and words in texts[cur]):
            continue
        if cur + 1 < len(scenes) and words in texts[cur + 1]:
            cur += 1
            starts[scenes[cur]["id"]] = start
        elif cur == len(scenes) - 1 and tail is None:
            tail = start  # song sings on past the last card (Suno's auto length pads with repeats)
    sung_ids = list(starts)
    if not sung_ids:
        raise SystemExit(f"no scene narration matches the lyrics in {song}")
    starts[sung_ids[0]] = 0.0  # first scene also covers the song's intro
    ends = {sid: starts[nxt] for sid, nxt in zip(sung_ids, sung_ids[1:])}
    ends[sung_ids[-1]] = tail if tail is not None else dur_of(song)
    if os.environ.get("SONG_END"):  # picked by ear: the take runs on past where the video should stop
        ends[sung_ids[-1]] = min(ends[sung_ids[-1]], _seconds(os.environ["SONG_END"]))
    # Flashes and unsung scenes are fillers for the instrumental stretches: each takes its
    # time out of the sung scene before it, so the next sung line still lands on its frame.
    filler = {}
    for i, s in enumerate(S):
        if s["kind"] == "flash":
            filler[i] = max(2, round(s["dur"] * FPS))
        elif s["id"] not in starts:
            filler[i] = round(s["min_dur"] * FPS)
    after, last = {}, None
    for i, s in enumerate(S):
        if i in filler:
            if last is not None:
                after[last] += filler[i]
        else:
            last, after[i] = i, 0
    frame = 0
    for i, s in enumerate(S):
        if i in filler:
            s["frames"] = filler[i]
        elif s["id"] == sung_ids[-1]:  # song may stop mid-scene; still show the whole scene
            s["frames"] = max(round(ends[s["id"]] * FPS) - frame, round(s["min_dur"] * FPS))
        else:
            s["frames"] = max(2, round(ends[s["id"]] * FPS) - frame - after[i])
        s["dur"] = s["frames"] / FPS
        frame += s["frames"]


# ----------------------------------------------------------------------------- 4. SFX library + music
def gen_sfx():
    def mk(name, lavfi, af=None):
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", lavfi]
        if af:
            cmd += ["-af", af]
        cmd += ["-ar", str(SR), "-ac", "2", str(SFX / f"{name}.wav")]
        run(cmd)

    mk("boom", "sine=frequency=80:duration=0.7", "afade=t=out:st=0.08:d=0.62,volume=2.2")
    mk("deepboom", "sine=frequency=52:duration=1.0", "afade=t=out:st=0.1:d=0.9,volume=3.0")
    mk("ding", "sine=frequency=880:duration=0.4", "afade=t=out:st=0.05:d=0.35,volume=1.4")
    mk("ding2", "sine=frequency=1318:duration=0.4", "afade=t=out:st=0.05:d=0.35,volume=1.3")
    mk("tick", "sine=frequency=1500:duration=0.05", "volume=1.2")
    mk("ok", "sine=frequency=1046:duration=0.18", "afade=t=out:st=0.04:d=0.14,volume=1.3")
    mk("whoosh", "anoisesrc=color=white:duration=0.5:amplitude=0.5",
       "highpass=f=600,afade=t=in:st=0:d=0.25,afade=t=out:st=0.25:d=0.25,volume=1.6")
    mk("drumroll", "anoisesrc=color=brown:duration=0.9:amplitude=0.7",
       "tremolo=f=22:d=0.9,afade=t=out:st=0.7:d=0.2,volume=1.8")
    mk("uhoh", "sine=frequency=300:duration=0.5", "afade=t=out:st=0.1:d=0.4,volume=1.6")
    # comedic descending "womp" sting for the "boo." beats
    mk("sadwomp", "aevalsrc='0.45*sin(2*PI*(340-150*min(t,0.55))*t)':d=0.55:s=44100",
       "vibrato=f=6:d=0.6,afade=t=out:st=0.4:d=0.15,volume=1.5,aformat=channel_layouts=stereo")
    # descending "record scratch"-ish swoop
    mk("scratch", "aevalsrc='0.6*sin(2*PI*(700-1200*min(t,0.35))*t)':d=0.35:s=44100", "volume=1.4,aformat=channel_layouts=stereo")
    # rising riser
    mk("riser", "aevalsrc='0.5*sin(2*PI*(300+900*t)*t)':d=0.5:s=44100", "volume=1.4,aformat=channel_layouts=stereo")
    mk("riserhit", "aevalsrc='0.5*sin(2*PI*(260+700*min(t,0.6))*t)':d=0.8:s=44100",
       "volume=1.5,aformat=channel_layouts=stereo")
    mk("type", "anoisesrc=color=white:duration=0.4:amplitude=0.3", "tremolo=f=30:d=0.9,highpass=f=1500,volume=0.9")
    mk("airhorn", "aevalsrc='0.33*sin(2*PI*233*t)+0.33*sin(2*PI*277*t)+0.33*sin(2*PI*330*t)':d=0.6:s=44100",
       "afade=t=out:st=0.45:d=0.15,volume=1.5,aformat=channel_layouts=stereo")
    # success arpeggio C-E-G-C
    notes = [("523", 0.0), ("659", 0.13), ("784", 0.26), ("1046", 0.39)]
    for i, (f, _) in enumerate(notes):
        mk(f"_n{i}", f"sine=frequency={f}:duration=0.2", "afade=t=out:st=0.06:d=0.14,volume=1.2")
    # build success by delaying notes and mixing
    inputs = []
    fc = []
    for i, (f, off) in enumerate(notes):
        inputs += ["-i", str(SFX / f"_n{i}.wav")]
        fc.append(f"[{i}]adelay={int(off*1000)}|{int(off*1000)}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(notes))) + f"amix=inputs={len(notes)}:normalize=0[o]")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[o]", "-t", "0.7", "-ar", str(SR), "-ac", "2", str(SFX / "success.wav")])


def cut_sounds(sounds):
    """Cut the storyboard's sounds ({name: (file, start, end, fade_in, fade_out)}) into the SFX library."""
    for name, (source, start, end, fade_in, fade_out) in sounds.items():
        # seek on the input, so the clip's clock (and the fades) start at 0
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source),
             "-af", f"afade=t=in:d={fade_in},afade=t=out:st={end - start - fade_out:.3f}:d={fade_out}",
             "-ar", str(SR), "-ac", "2", str(SFX / f"{name}.wav")])


def gen_music():
    # bleepy minor-ish arpeggio loop
    seq = [220, 329, 440, 329, 261, 391, 523, 391]
    parts = []
    for i, f in enumerate(seq):
        p = AUDIO / f"_m{i}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             f"sine=frequency={f}:duration=0.21",
             "-af", "afade=t=out:st=0.14:d=0.07,volume=0.8", "-ar", str(SR), "-ac", "2", str(p)])
        parts.append(p)
    lst = AUDIO / "_mlist.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(AUDIO / "music_loop.wav")])


# ----------------------------------------------------------------------------- 6. audio segments
def build_audio_segs(S):
    for s in S:
        seg = AUDIO / f"seg_{s['_i']}.wav"
        s["_seg"] = seg
        dur = s["dur"]
        inputs = ["-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=stereo"]
        fc = []
        idx = 1
        labels = ["[0:a]"]  # base silence
        if s["kind"] == "scene":
            inputs += ["-i", str(AUDIO / f"{s['id']}.wav")]
            lead = int(s.get("_lead", LEAD) * 1000)
            fc.append(f"[{idx}:a]adelay={lead}|{lead}[n]")
            labels.append("[n]")
            idx += 1
        for name, off in s.get("sfx", []):
            sfxp = SFX / f"{name}.wav"
            if not sfxp.exists():
                continue
            if off < 0:  # counted back from the scene's end
                off = dur + off
            if name == "sadwomp" and s.get("_lastseg"):  # land the sting on "Boo."
                off = LEAD + s["_lastseg"] + 0.05
            inputs += ["-i", str(sfxp)]
            fc.append(f"[{idx}:a]adelay={int(off*1000)}|{int(off*1000)}[s{idx}]")
            labels.append(f"[s{idx}]")
            idx += 1
        fc.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,"
                  f"alimiter=limit=0.95[o]")
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
             "-map", "[o]", "-t", f"{dur:.4f}", "-ar", str(SR), "-ac", "2", str(seg)])


# ----------------------------------------------------------------------------- 7. assemble
def mix_audio(S, total, song=None):
    """Write final_audio.wav: the song, or narration + SFX segments over the music bed."""
    if song:
        # the song is the whole soundtrack: a longer one (Suno's auto length runs minutes)
        # fades out at the last scene, a shorter one pads with silence so the gap shows
        song_dur = dur_of(song)
        af = f"afade=t=out:st={max(total - 1.5, 0.0):.4f}:d=1.5" if song_dur > total else "apad"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(song), "-map", "0:a:0",
             "-af", af, "-t", f"{total:.4f}", "-ar", str(SR), "-ac", "2",
             str(ROOT / "final_audio.wav")])
    else:
        alist = ROOT / "concat_a.txt"
        alist.write_text("".join(f"file '{s['_seg']}'\n" for s in S))
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(alist),
             "-c", "copy", str(ROOT / "narr_sfx.wav")])
        # mix music bed under narration+sfx; it fades out over the last scene, so the end
        # card belongs to its own stinger (or to silence)
        last = S[-1]["dur"]
        bed_fade = f"afade=t=out:st={total - last:.4f}:d={min(2.0, last):.4f}"
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-i", str(ROOT / "narr_sfx.wav"),
             "-stream_loop", "-1", "-i", str(AUDIO / "music_loop.wav"),
             "-filter_complex",
             f"[1:a]volume=0.085,{bed_fade}[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,"
             "alimiter=limit=0.96,aresample=44100[a]",
             "-map", "[a]", "-t", f"{total:.4f}", str(ROOT / "final_audio.wav")])


def mux(video, name):
    """Put final_audio.wav under a silent video -> <name>.mp4."""
    out = ROOT / f"{name}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-i", str(video), "-i", str(ROOT / "final_audio.wav"),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-shortest", str(out)])
    return out


# ----------------------------------------------------------------------------- 7b. HyperFrames scenes
# A HyperFrames project replaces steps 1, 2, 5 and the concat: each scene is a
# sub-composition `compositions/<id>.html` with its own GSAP timeline, and the engine
# writes the root `index.html` that lays the scenes out at the computed times. Timing,
# TTS, song sync and the audio mix stay here, so both cuts come from the same scenes.
HF_CLI = "hyperframes@0.8.85"  # pinned so a re-render months later draws the same frames
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
# the ffmpeg zoom effects, handed to each scene as its `zoom` variable. The scene pushes in
# on its own content and keeps its chrome (logo, badge) still, so only the theme knows
# what chrome is. Kept small so content near the edges stays in frame.
HF_ZOOM = {"punch": 1.06, "slowpunch": 1.04, "punchfast": 1.08}


def link_into(project, name, target):
    """Symlink a shared file or folder into the project; its server only sees the project dir."""
    link = project / name
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)


def write_hf_index(S, project, total, theme_files, size):
    """Root composition: one slot per scene, flashes as color cards.

    Each scene gets its final length as the `dur` variable, so beats inside a scene can
    land at a fraction of it and still line up in both the narrated and the song cut, and
    its effect as the `zoom` variable (1 = none).

    A scene with blend=N fades in over its first N seconds on its own track, while the
    scene before stays on screen N seconds longer underneath it: a cross-fade that keeps
    both scenes' timing (and so their audio) where it was.
    """
    width, height = size
    slots, fades, start = [], [], 0.0
    for i, s in enumerate(S):
        under = S[i + 1].get("blend", 0) if i + 1 < len(S) else 0
        timing = f'data-start="{start:.4f}" data-duration="{s["dur"] + under:.4f}"'
        if s["kind"] == "flash":
            slots.append(f'<div id="flash-{s["_i"]}" class="clip flash" '
                         f'style="background:{s["color"]}" {timing} data-track-index="2"></div>')
        else:
            values = json.dumps({"dur": round(s["dur"], 4), "zoom": HF_ZOOM.get(s.get("effect"), 1),
                                 "width": width, "height": height})
            slots.append(f'<div id="el-{s["id"]}" data-composition-id="{s["id"]}" '
                         f'data-composition-src="compositions/{s["id"]}.html" '
                         f"data-variable-values='{values}' {timing} "
                         f'data-track-index="{3 if s.get("blend") else 1}"></div>')
            if s.get("blend"):
                fades.append(f'tl.fromTo("#el-{s["id"]}", {{ opacity: 0 }}, '
                             f'{{ opacity: 1, duration: {s["blend"]}, ease: "none" }}, {start:.4f});')
        start += s["dur"]
    newline = "\n      "
    theme = [f'<link rel="stylesheet" href="{n}" />' if n.endswith(".css") else f'<script src="{n}"></script>'
             for n in theme_files]
    html = f"""<!doctype html>
<!-- generated by engine.py from the storyboard; edit the storyboard, not this file -->
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={width}, height={height}" />
    <script src="{GSAP_URL}"></script>
    {newline.join(theme)}
    <style>
      body {{ margin: 0; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      #root > div[data-composition-src], #root > .flash {{ position: absolute; inset: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-width="{width}" data-height="{height}" data-duration="{total:.4f}">
      {newline.join(slots)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {newline.join(fades)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (project / "index.html").write_text(html, encoding="utf-8")


def hf(project, *args):
    subprocess.run(["npx", "--yes", HF_CLI, *args], check=True, cwd=project)


def render_hf(S, project, theme_files, size):
    """Render the scenes silently with HyperFrames; return the video path and its length."""
    link_into(project, "assets", ROOT / "assets")
    for name, path in theme_files.items():
        link_into(project, name, path)
    total = sum(s["dur"] for s in S)
    write_hf_index(S, project, total, theme_files, size)
    video = ROOT / "video_hf.mp4"
    # CRF 22: HyperFrames defaults to 16, which is near-lossless and ~3x the size for no visible gain
    hf(project, "render", "--quiet", "--fps", str(FPS), "--crf", "22", "-o", str(video))
    return video, total


def hf_poster(project, at):
    """Grab one frame of the rendered composition as poster.png."""
    shots = ROOT / "inspect" / "poster"
    hf(project, "snapshot", "--at", f"{at:.2f}", "--no-end", "--describe", "false", "-o", str(shots))
    newest = max(shots.glob("*.png"), key=lambda p: p.stat().st_mtime)
    newest.replace(ROOT / "poster.png")


# ----------------------------------------------------------------------------- orchestration
def poster_time(S, scene_id):
    """A moment late in the scene, when its elements have landed."""
    start = 0.0
    for s in S:
        if s.get("id") == scene_id:
            return start + 0.75 * s["dur"]
        start += s["dur"]
    raise SystemExit(f"poster scene {scene_id!r} is not in the storyboard")


def build_hf(S, name, song, project, theme_files, poster_scene, sounds, size):
    """HyperFrames path of build(): same timing and audio, visuals drawn by HyperFrames.

    SKIP_RENDER=1 keeps the last video_hf.mp4 and only redoes the audio: for sound changes
    that leave every scene's length alone. It refuses when the timing moved.
    """
    video = ROOT / "video_hf.mp4"
    skip = os.environ.get("SKIP_RENDER") and video.exists()
    if skip:
        total = sum(s["dur"] for s in S)
        if abs(dur_of(video) - total) > 1 / FPS:
            raise SystemExit("SKIP_RENDER: the scene timing changed since the last render, so render again")
    else:
        video, total = render_hf(S, project, theme_files, size)
    if not song:
        gen_sfx()
        cut_sounds(sounds)
        gen_music()
        build_audio_segs(S)
    mix_audio(S, total, song)
    out = mux(video, name)
    if poster_scene and not skip:
        hf_poster(project, poster_time(S, poster_scene))
    print(json.dumps({
        "output": str(out),
        "total_seconds": round(total, 2),
        "scenes": [{"id": s.get("id", "flash"), "dur": round(s["dur"], 2),
                    "tts": round(s.get("tts", 0), 2)} for s in S],
    }, indent=2))
    return out, total


def build(sb, *, name, hyperframes, theme_files, poster_scene=None, short_keep=None, voiceover=None,
          size=VERTICAL):
    """Render a storyboard to <name>.mp4.

    voiceover: {"voice": id, "model": id, "settings": {...}} reads the narration as one
    ElevenLabs take (see voiceover_durations) instead of a Kokoro line per scene.
    hyperframes: a HyperFrames project dir with compositions/<scene id>.html per scene.
    HyperFrames draws the visuals: theme_files ({"theme.css": path, ...}) are
    linked into the project and loaded by the root page, and poster_scene names the
    scene whose frame becomes poster.png.
    size: (width, height) in pixels; VERTICAL for Reels/TikTok/Shorts, WIDE for 16:9.
    """
    S = sb.scenes
    if os.environ.get("SHORT") and short_keep:  # ~40s teaser: keep essential beats, drop flashes
        S[:] = [s for s in S if s.get("id") in short_keep]
        name = name + "-40s"
    if os.environ.get("LYRICS"):  # just the Suno lyrics sheet, nothing rendered
        print(lyric_sheet(S))
        return None, 0.0
    song = os.environ.get("SONG")
    for i, s in enumerate(S):
        s["_i"] = i
    if song:  # song replaces narration: time scenes to its lyrics instead of TTS
        song = Path(song).expanduser()
        song_durations(S, song)
        name = name + "-song"
    elif voiceover:
        voiceover_durations(S, voiceover)
    else:
        tts_and_durations(S)
    return build_hf(S, name, song, Path(hyperframes), theme_files, poster_scene, sb.sounds, size)
