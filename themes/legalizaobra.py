"""Legaliza Obra brand theme for HyperFrames scenes: palette constants and theme files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WHITE = "#ffffff"
SURFACE = "#f5f8f7"
INK = "#141414"
TEAL = "#1f514c"
TEAL_2 = "#2a5f59"
TEAL_DEEP = "#102c29"
MINT = "#edffe3"
MINT_SOFT = "#cfe3df"
WARNING = "#dc8f1f"

HF_THEME = {"theme.css": ROOT / "themes" / "legalizaobra.css", "theme.js": ROOT / "themes" / "legalizaobra.js"}
