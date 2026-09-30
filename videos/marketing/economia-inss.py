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
from engine import VERTICAL, Beat, Storyboard, build
from themes.legalizaobra import HF_THEME, TEAL, WHITE

SCENES = Path(__file__).resolve().parent / "economia-inss-scenes"
APP_CLIPS = ["01-obra-andrade", "02-esocial-envio", "03-darf", "07-simulacao"]
SIMULACAO_CLICK, SIMULACAO_RESULT = 6.78, 7.73
ESOCIAL_CLICK, ESOCIAL_CONFIRM, ESOCIAL_DONE = 6.75, 9.72, 11.53
DARF_CONFIRM, DARF_DONE = 9.92, 11.8
VOICEOVER = {"voice": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "settings": {"stability": 0.5, "speed": 1.08}}

sb = Storyboard()
scene = sb.scene
flash = sb.flash


def clip(scene_id: str, clip_seconds: float) -> float:
    return app_clips.scene_time(SCENES, scene_id, clip_seconds)


scene(
    id="hook", effect="slowpunch", min_dur=2.6,
    narration="[excited] Quanto de INSS a sua obra vai pagar?",
    sfx=[("whoosh", 0.1), ("boom", 0.45)],
)
scene(
    id="problem", min_dur=5.0,
    narration="Sem planejamento, o INSS sai pela área construída. "
              "Numa casa de 240 metros em São Paulo: 81 mil reais.",
    sfx=[("tick", 0.4), ("drumroll", Beat(0.2)), ("boom", Beat(0.2, 1.6)), ("uhoh", Beat(0.55, 0.1))],
)
flash(TEAL, 0.066, sfx=[("tick", 0.0)])
scene(
    id="meet", effect="punch", min_dur=3.2,
    narration="[excited] Com a Legaliza Obra, você paga menos. Dentro da lei.",
    sfx=[("airhorn", 0.05), ("ok", Beat(0.55, 0.1))],
)
scene(
    id="simulacao", min_dur=5.0,
    narration="Você informa os dados da obra... e vê o resultado na hora.",
    sfx=[("whoosh", 0.2), ("tick", clip("simulacao", SIMULACAO_CLICK)), ("ding", clip("simulacao", SIMULACAO_RESULT))],
)
scene(
    id="economia", effect="slowpunch", min_dur=5.5,
    narration="Nessa obra, o INSS cai de 81 para 47 mil. "
              "[excited] Quase 34 mil de economia!",
    sfx=[("tick", 0.2), ("tick", 0.4), ("type", Beat(0.25)), ("ok", Beat(0.25, 1.1)),
         ("riser", Beat(0.5)), ("success", Beat(0.5, 1.2))],
)
flash(WHITE, 0.066, sfx=[("tick", 0.0)])
scene(
    id="obra", min_dur=4.5,
    narration="Cada obra fica num só lugar: pedreiros, folha e o INSS de cada mês.",
    sfx=[("whoosh", 0.2)],
)
scene(
    id="esocial", min_dur=6.0,
    narration="Um clique envia a obra para o eSocial.",
    sfx=[("whoosh", 0.2), ("tick", clip("esocial", ESOCIAL_CLICK)), ("tick", clip("esocial", ESOCIAL_CONFIRM)),
         ("success", clip("esocial", ESOCIAL_DONE))],
)
scene(
    id="darf", min_dur=4.8,
    narration="E todo mês, a guia DARF sai pronta. Sem planilha.",
    sfx=[("whoosh", 0.2), ("tick", clip("darf", DARF_CONFIRM)), ("success", clip("darf", DARF_DONE))],
)
scene(
    id="cta", effect="slowpunch", min_dur=5.0, blend=0.5,
    narration="[excited] Calcule grátis o INSS da sua obra em legalizaobra ponto com.",
    sfx=[("ding2", Beat(0.35, 0.15))],
)


def main():
    app_clips.ensure(APP_CLIPS)
    voiceover = VOICEOVER if os.environ.get("ELEVENLABS_API_KEY") else None
    build(sb, name="economia-inss", hyperframes=SCENES, theme_files=HF_THEME, poster_scene="economia",
          voiceover=voiceover, size=VERTICAL)


if __name__ == "__main__":
    main()
