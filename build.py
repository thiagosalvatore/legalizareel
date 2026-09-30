#!/usr/bin/env python3
"""Render a video. Usage: python build.py <team>/<name>  (default: marketing/economia-inss).

Videos live in videos/<team>/<name>.py and expose a main() that builds a Storyboard
and hands it to engine.build(). See README.md for the toolchain and env toggles.
"""
import importlib
import sys


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "marketing/economia-inss"
    importlib.import_module("videos." + name.replace("/", ".")).main()


if __name__ == "__main__":
    main()
