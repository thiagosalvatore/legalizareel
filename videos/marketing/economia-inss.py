#!/usr/bin/env python3
"""Storyboard for the "Economia de INSS" reel: a vertical pt-BR video that sells the INSS savings.

Render:
  python build.py marketing/economia-inss                                  # edge-tts / Kokoro voice
  ELEVENLABS_API_KEY=... python build.py marketing/economia-inss           # ElevenLabs voiceover
Preview while editing scenes (after one render wrote index.html):
  cd videos/marketing/economia-inss-scenes && npx hyperframes@0.8.85 preview
"""
import os
from pathlib import Path

import app_clips
from engine import VERTICAL, Storyboard, build
from themes.legalizaobra import HF_THEME, TEAL, WHITE

SCENES = Path(__file__).resolve().parent / "economia-inss-scenes"
APP_CLIPS = ["01-obra-andrade", "02-esocial-envio", "03-darf", "07-simulacao"]
VOICEOVER = {"voice": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "settings": {"stability": 0.5, "speed": 1.08}}

sb = Storyboard()
scene = sb.scene
flash = sb.flash

scene(
    id="hook", effect="slowpunch", min_dur=2.6,
    narration="[excited] Quanto de INSS a sua obra vai pagar?",
    sfx=[("tick", 0.2), ("boom", 0.9)],
)
scene(
    id="problem", min_dur=5.0,
    narration="Sem planejamento, o INSS sai pela área construída. "
              "Numa casa de 240 metros em São Paulo: 81 mil reais.",
    sfx=[("drumroll", 1.0), ("uhoh", 3.2)],
)
flash(TEAL, 0.066, sfx=[("tick", 0.0)])
scene(
    id="meet", effect="punch", min_dur=3.2,
    narration="[excited] Com a Legaliza Obra, você paga menos. Dentro da lei.",
    sfx=[("airhorn", 0.1), ("ok", 1.8)],
)
scene(
    id="simulacao", min_dur=5.0,
    narration="Você informa os dados da obra... e vê o resultado na hora.",
    sfx=[("type", 0.4), ("ding", 3.6)],
)
scene(
    id="economia", effect="slowpunch", min_dur=5.5,
    narration="Nessa obra, o INSS cai de 81 para 47 mil. "
              "[excited] Quase 34 mil de economia!",
    sfx=[("riser", 1.2), ("success", 2.9)],
)
flash(WHITE, 0.066, sfx=[("tick", 0.0)])
scene(
    id="obra", min_dur=4.5,
    narration="Cada obra fica num só lugar: pedreiros, folha e o INSS de cada mês.",
    sfx=[("ding", 0.5)],
)
scene(
    id="esocial", min_dur=6.0,
    narration="Um clique envia a obra para o eSocial.",
    sfx=[("tick", 1.4), ("ok", 3.9)],
)
scene(
    id="darf", min_dur=4.8,
    narration="E todo mês, a guia DARF sai pronta. Sem planilha.",
    sfx=[("tick", 0.8), ("success", 3.6)],
)
scene(
    id="cta", effect="slowpunch", min_dur=5.0, blend=0.5,
    narration="[excited] Calcule grátis o INSS da sua obra em legalizaobra ponto com.",
    sfx=[("ding2", 1.8)],
)


def main():
    app_clips.ensure(APP_CLIPS)
    voiceover = VOICEOVER if os.environ.get("ELEVENLABS_API_KEY") else None
    build(sb, name="economia-inss", hyperframes=SCENES, theme_files=HF_THEME, poster_scene="economia",
          voiceover=voiceover, size=VERTICAL)


if __name__ == "__main__":
    main()
