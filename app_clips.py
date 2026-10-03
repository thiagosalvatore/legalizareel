#!/usr/bin/env python3
"""Copy app recordings from the frontend's mock-backend recorder into assets/app/.

Usage: python app_clips.py [clip ...]   (no argument: every recorded clip)
"""
import itertools
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_ASSETS = ROOT / "assets" / "app"
DEFAULT_FRONTEND = Path.home() / "projects" / "personal" / "legaliza-obra" / "obra-certa-frontend"
FRONTEND = Path(os.environ.get("OBRA_FRONTEND", DEFAULT_FRONTEND)).expanduser()
RECORDER = FRONTEND / "mock-backend" / "recording"
RECORDINGS = RECORDER / "output"
CLIP_WIDTH = 1080
KEYFRAME_EVERY = 15
Segment = tuple[float, float]
MEDIA_START = re.compile(r'data-media-start="([\d.]+)"')

RECORD_HELP = f"""Record it with the mock backend running:
  cd {FRONTEND}
  npx tsx mock-backend/server.ts            # terminal 1
  pnpm dev --port 3100                      # terminal 2
  cd mock-backend/recording && npm run record -- {{prefix}}"""


def _is_stale(source: Path, target: Path) -> bool:
    return not target.exists() or target.stat().st_mtime < source.stat().st_mtime


def _encode(source: Path, target: Path, video_filter: list[str]) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), *video_filter,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-g", str(KEYFRAME_EVERY), "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(target)],
        check=True,
    )


def _transcode(source: Path, target: Path) -> None:
    _encode(source, target, ["-vf", f"scale={CLIP_WIDTH}:-2"])


def ensure(names: list[str]) -> None:
    """Make every named clip available as assets/app/<name>.mp4, refreshing stale copies."""
    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = RECORDINGS / f"{name}.mp4"
        target = APP_ASSETS / f"{name}.mp4"
        if not source.exists():
            raise SystemExit(f"missing recording {source}\n" + RECORD_HELP.format(prefix=name.split("-")[0]))
        if _is_stale(source, target):
            print(f"syncing {name}")
            _transcode(source, target)


def adopt(source: Path, name: str) -> None:
    """Make a recording made outside the recorder available as assets/app/<name>.mp4, at its own size."""
    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    target = APP_ASSETS / f"{name}.mp4"
    if not source.exists():
        raise SystemExit(f"missing recording {source}")
    if _is_stale(source, target):
        print(f"syncing {name}")
        _encode(source, target, [])


def cut(name: str, segments: list[Segment], cut_name: str) -> None:
    """Join the (start, end) segments of assets/app/<name>.mp4 into assets/app/<cut_name>.mp4."""
    trims = [f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[s{i}]" for i, (start, end) in enumerate(segments)]
    joined = "".join(f"[s{i}]" for i in range(len(segments)))
    graph = ";".join([*trims, f"{joined}concat=n={len(segments)}:v=1:a=0[out]"])
    _encode(APP_ASSETS / f"{name}.mp4", APP_ASSETS / f"{cut_name}.mp4", ["-filter_complex", graph, "-map", "[out]"])


def cut_time(segments: list[Segment], clip_seconds: float) -> float:
    """Seconds into a cut when its source clip reaches clip_seconds."""
    elapsed = 0.0
    for start, end in segments:
        if start <= clip_seconds < end:
            return elapsed + clip_seconds - start
        elapsed += end - start
    raise ValueError(f"the cut leaves out {clip_seconds}s of its clip")


def cut_points(segments: list[Segment]) -> tuple[float, ...]:
    """Seconds into a cut where each segment after the first begins."""
    lengths = [end - start for start, end in segments[:-1]]
    return tuple(itertools.accumulate(lengths))


def scene_time(scenes: Path, scene_id: str, clip_seconds: float) -> float:
    """Seconds into a scene when its app clip reaches clip_seconds, given the clip's data-media-start."""
    html = (scenes / "compositions" / f"{scene_id}.html").read_text(encoding="utf-8")
    return clip_seconds - float(MEDIA_START.search(html).group(1))


def main() -> None:
    names = sys.argv[1:] or sorted(p.stem for p in RECORDINGS.glob("*.mp4"))
    ensure(names)


if __name__ == "__main__":
    main()
