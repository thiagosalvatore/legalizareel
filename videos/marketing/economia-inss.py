#!/usr/bin/env python3
"""Storyboard for the "Economia de INSS" reel: a vertical pt-BR video that sells the INSS savings.

Render:
  python build.py marketing/economia-inss                                  # edge-tts / Kokoro voice
  ELEVENLABS_API_KEY=... python build.py marketing/economia-inss           # ElevenLabs voiceover
Preview while editing scenes (after one render wrote index.html):
  cd videos/marketing/economia-inss-scenes && npx hyperframes@0.8.85 preview
"""
import math
import os
from pathlib import Path

import app_clips
from engine import VERTICAL, Beat, Storyboard, build
from themes.legalizaobra import HF_THEME, TEAL, WHITE

SCENES = Path(__file__).resolve().parent / "economia-inss-scenes"
APP_CLIPS = ["02-esocial-envio", "03-darf", "07-simulacao"]
SIMULACAO_CLICK, SIMULACAO_RESULT = 6.78, 7.73
ESOCIAL_CLICK, ESOCIAL_CONFIRM, ESOCIAL_DONE = 6.75, 9.72, 11.53
DARF_CONFIRM, DARF_DONE = 9.92, 11.8
PILE = {"cards": 23, "fallFrom": 0.06, "fallSpan": 0.5, "errorsAt": (0.76, 0.8, 0.85, 0.89), "collapseAt": 0.93}
PROBLEM = {"countAt": 0.31}
ECONOMIA = {"dropAt": 0.31, "savedAt": 0.62}
ESOCIAL = {"zoomAt": 2.1}
CARD_LANDS_AFTER = 0.18
VOICEOVER = {"voice": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "settings": {"stability": 0.5, "speed": 1.08}}

sb = Storyboard()
scene = sb.scene
flash = sb.flash


def clip(scene_id: str, clip_seconds: float) -> float:
    return app_clips.scene_time(SCENES, scene_id, clip_seconds)


def pile_landings() -> list[Beat]:
    return [Beat(PILE["fallFrom"] + PILE["fallSpan"] * math.sqrt(i / PILE["cards"]), CARD_LANDS_AFTER)
            for i in range(PILE["cards"])]


scene(
    id="hook", effect="slowpunch", min_dur=2.6,
    narration="[excited] Quanto de INSS a sua obra vai pagar?",
    sfx=[("impact", 0.4)],
)
scene(
    id="problem", min_dur=5.0, vars=PROBLEM,
    narration="Sem planejamento, o INSS sai pela área construída: "
              "81 mil reais, numa casa de 240 metros.",
    sfx=[("drumroll", Beat(PROBLEM["countAt"])), ("impact", Beat(PROBLEM["countAt"], 1.6)), ("swoosh", -0.3)],
)
flash(TEAL, 0.066)
scene(
    id="meet", effect="punch", min_dur=3.2,
    narration="[excited] Com a Legaliza Obra, você paga menos. Dentro da lei.",
    sfx=[("airhorn", 0.05)],
)
scene(
    id="simulacao", min_dur=5.0,
    narration="Você informa os dados da obra... e vê o resultado na hora.",
    sfx=[("click", clip("simulacao", SIMULACAO_CLICK)), ("ding", clip("simulacao", SIMULACAO_RESULT))],
)
scene(
    id="economia", effect="slowpunch", min_dur=5.5, vars=ECONOMIA,
    narration="Nessa obra, o INSS cai de 81 para 47 mil. "
              "[excited] Quase 34 mil de economia!",
    sfx=[("fall", Beat(ECONOMIA["dropAt"])), ("riser", Beat(ECONOMIA["savedAt"], -0.3)),
         ("cash", Beat(ECONOMIA["savedAt"], 1.2)), ("swoosh", -0.3)],
)
flash(WHITE, 0.066)
scene(
    id="burocracia", min_dur=11.0,
    vars={**PILE, "errorsAt": ",".join(map(str, PILE["errorsAt"]))},
    narration="Mas pra pagar menos, a obra tem que estar em dia no eSocial. Todo mês. "
              "São 80 envios numa obra só. Um campo errado? Rejeitado.",
    sfx=[*[("thud", beat) for beat in pile_landings()],
         *[("buzz", Beat(at, 0.05)) for at in PILE["errorsAt"]],
         ("crash", Beat(PILE["collapseAt"], 0.05))],
)
flash(TEAL, 0.066)
scene(
    id="esocial", effect="punch", min_dur=7.2, vars=ESOCIAL,
    narration="[excited] A Legaliza Obra faz tudo isso por você. Um clique, e a obra está no eSocial.",
    sfx=[("impact", 0.0), ("click", clip("esocial", ESOCIAL_CLICK)), ("click", clip("esocial", ESOCIAL_CONFIRM)),
         ("success", clip("esocial", ESOCIAL_DONE))],
)
scene(
    id="darf", min_dur=4.8,
    narration="E com a transmissão automática, a guia DARF de todo mês chega pronta no seu e-mail.",
    sfx=[("click", clip("darf", DARF_CONFIRM)), ("success", clip("darf", DARF_DONE))],
)
scene(
    id="cta", effect="slowpunch", min_dur=5.0, blend=0.5,
    narration="[excited] Simule grátis o INSS da sua obra, na calculadora da Legaliza Obra.",
    sfx=[("swoosh", 0.0), ("ding2", Beat(0.35, 0.15))],
)


def main():
    app_clips.ensure(APP_CLIPS)
    voiceover = VOICEOVER if os.environ.get("ELEVENLABS_API_KEY") else None
    build(sb, name="economia-inss", hyperframes=SCENES, theme_files=HF_THEME, poster_scene="economia",
          voiceover=voiceover, size=VERTICAL)


if __name__ == "__main__":
    main()
