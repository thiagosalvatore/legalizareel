#!/usr/bin/env python3
"""Render many narration fragments in a single Kokoro process so the model loads once.

Reads a JSON job list [{"text", "voice", "lang", "speed", "out"}, ...] from argv[1] and writes
each fragment as a 24 kHz wav. build.py post-processes (resample / trim / emphasis).
"""
import json
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

jobs = json.loads(open(sys.argv[1]).read())
pipelines = {}
for job in jobs:
    if job["lang"] not in pipelines:
        pipelines[job["lang"]] = KPipeline(lang_code=job["lang"])
    pipeline = pipelines[job["lang"]]
    chunks = [audio for _, _, audio in pipeline(job["text"], voice=job["voice"], speed=job["speed"])]
    out = np.concatenate(chunks) if chunks else np.zeros(1, dtype="float32")
    sf.write(job["out"], out, 24000)
