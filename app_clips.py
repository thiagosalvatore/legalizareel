#!/usr/bin/env python3
"""Copy app recordings from the frontend's mock-backend recorder into assets/app/.

Usage: python app_clips.py [clip ...]   (no argument: every recorded clip)
"""
import os
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

RECORD_HELP = f"""Record it with the mock backend running:
  cd {FRONTEND}
  npx tsx mock-backend/server.ts            # terminal 1
  pnpm dev --port 3100                      # terminal 2
  cd mock-backend/recording && npm run record -- {{prefix}}"""


def _is_stale(source: Path, target: Path) -> bool:
    return not target.exists() or target.stat().st_mtime < source.stat().st_mtime


def _transcode(source: Path, target: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
         "-vf", f"scale={CLIP_WIDTH}:-2", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-g", str(KEYFRAME_EVERY), "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(target)],
        check=True,
    )


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


def main() -> None:
    names = sys.argv[1:] or sorted(p.stem for p in RECORDINGS.glob("*.mp4"))
    ensure(names)


if __name__ == "__main__":
    main()
