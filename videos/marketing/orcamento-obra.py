#!/usr/bin/env python3
"""Storyboard for the "Do orçamento à obra" reel: a vertical pt-BR video that sells the simulação → orçamento →
contrato → obra flow.

Render:
  python build.py marketing/orcamento-obra                                  # edge-tts / Kokoro voice
  ELEVENLABS_API_KEY=... python build.py marketing/orcamento-obra           # ElevenLabs voiceover
Preview while editing scenes (after one render wrote index.html):
  cd videos/marketing/orcamento-obra-scenes && npx hyperframes@0.8.85 preview
"""
import os
from pathlib import Path

import app_clips
from engine import VERTICAL, Beat, Storyboard, build
from themes.legalizaobra import HF_THEME, TEAL, WHITE

SCENES = Path(__file__).resolve().parent / "orcamento-obra-scenes"
APP_CLIPS = ["10-orcamento", "11-orcamento-cliente", "12-contrato", "13-obra"]
QUOTE_CREATE, QUOTE_PRICE, QUOTE_SUBMIT, QUOTE_DONE = 6.5, 13.5, 16.15, 16.4
CONTRACT_PREVIEW, CONTRACT_SEND = 13.33, 21.9
OBRA_CREATE, OBRA_NAME, OBRA_SUBMIT, OBRA_DONE = 7.6, 9.05, 12.0, 12.85
CUTS = {
    "orcamento": ("10-orcamento", [(5.6, 7.6), (12.8, 22.7)]),
    "contrato": ("12-contrato", [(12.6, 15.0), (21.5, 22.1), (22.3, 25.5)]),
    "obra": ("13-obra", [(7.4, 10.55), (11.6, 12.15), (12.75, 15.8)]),
}
RETRABALHO = {"typeAt": (0.12, 0.23, 0.36, 0.565), "cps": 16, "typoAt": 0.73}
FLUXO = {"stepsAt": (0.18, 0.32, 0.45, 0.57)}
ORCAMENTO = {"badgeAt": 0.4}
LINK = {"copyAt": 0.08, "flyAt": 0.17, "badgeAt": 0.79}
MODELO = {"swapsAt": (0.33, 0.49, 0.66, 0.76), "readyAt": 0.85}
CONTRATO = {"signedAt": 0.78}
RESUMO = {"beforeMinutes": 120, "afterMinutes": 5, "strikeAt": 0.48, "nowAt": 0.5,
          "checksAt": (0.03, 0.16, 0.3), "lineAt": 0.75}
SWAP_LANDS_AFTER = 0.14
COUNTER_LANDS_AFTER = 1.2
VOICEOVER = {"voice": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "settings": {"stability": 0.5, "speed": 1.08}}

sb = Storyboard()
scene = sb.scene
flash = sb.flash


def clip(scene_id: str, clip_seconds: float) -> float:
    return app_clips.scene_time(SCENES, scene_id, clip_seconds)


def cut_clip(scene_id: str, clip_seconds: float) -> float:
    _, segments = CUTS[scene_id]
    return clip(scene_id, app_clips.cut_time(segments, clip_seconds))


def cuts_at(scene_id: str) -> str:
    _, segments = CUTS[scene_id]
    return ",".join(f"{point:.2f}" for point in app_clips.cut_points(segments))


def scene_vars(values: dict) -> dict:
    """Hand tuples to a composition as the comma-separated strings it splits."""
    return {key: ",".join(map(str, value)) if isinstance(value, tuple) else value for key, value in values.items()}


scene(
    id="hook", effect="slowpunch", min_dur=2.8,
    narration="[excited] Quanto tempo você perde montando orçamento e contrato?",
    sfx=[("impact", 0.4)],
)
scene(
    id="retrabalho", min_dur=8.5, vars=scene_vars(RETRABALHO),
    narration="O nome do cliente vai na planilha, no orçamento, no contrato... "
              "e de novo no cadastro da obra. Tudo à mão.",
    sfx=[*[("type", Beat(at, 0.15)) for at in RETRABALHO["typeAt"]],
         ("buzz", Beat(RETRABALHO["typoAt"])), ("swoosh", -0.3)],
)
flash(TEAL, 0.066)
scene(
    id="fluxo", effect="punch", min_dur=5.5, vars=scene_vars(FLUXO),
    narration="[excited] Na Legaliza Obra, a simulação vira orçamento, contrato e obra. Sem redigitar nada.",
    sfx=[("airhorn", 0.05), *[("tick", Beat(at)) for at in FLUXO["stepsAt"]]],
)
scene(
    id="orcamento", min_dur=7.3, vars={**ORCAMENTO, "cutsAt": cuts_at("orcamento")},
    narration="Na simulação, um clique cria o orçamento. Escolhe o cliente, coloca o preço, e pronto.",
    sfx=[("click", cut_clip("orcamento", QUOTE_CREATE)), ("type", cut_clip("orcamento", QUOTE_PRICE)), ("click", cut_clip("orcamento", QUOTE_SUBMIT)),
         ("ding", cut_clip("orcamento", QUOTE_DONE))],
)
scene(
    id="link", min_dur=6.0, vars=LINK,
    narration="Você manda o link, e o cliente vê a proposta, com a economia de INSS, sem criar conta.",
    sfx=[("click", Beat(LINK["copyAt"])), ("whoosh", Beat(LINK["flyAt"])), ("ok", Beat(LINK["badgeAt"], 0.15))],
)
scene(
    id="modelo", min_dur=5.5, vars=scene_vars(MODELO),
    narration="O contrato sai do seu modelo. Nome, CPF e valor entram sozinhos.",
    sfx=[*[("tick", Beat(at, SWAP_LANDS_AFTER)) for at in MODELO["swapsAt"]],
         ("ok", Beat(MODELO["readyAt"], 0.15))],
)
scene(
    id="contrato", min_dur=6.2, vars={**CONTRATO, "cutsAt": cuts_at("contrato")},
    narration="Revisou? Um clique, e o contrato vai para assinatura eletrônica.",
    sfx=[("click", cut_clip("contrato", CONTRACT_PREVIEW)), ("click", cut_clip("contrato", CONTRACT_SEND)),
         ("success", Beat(CONTRATO["signedAt"], SWAP_LANDS_AFTER)), ("swoosh", -0.3)],
)
flash(WHITE, 0.066)
scene(
    id="obra", min_dur=6.8, vars={"cutsAt": cuts_at("obra")},
    narration="Cliente fechou? Mais um clique, e a obra está criada, com os dados da simulação.",
    sfx=[("click", cut_clip("obra", OBRA_CREATE)), ("type", cut_clip("obra", OBRA_NAME)),
         ("click", cut_clip("obra", OBRA_SUBMIT)), ("success", cut_clip("obra", OBRA_DONE)), ("swoosh", -0.3)],
)
scene(
    id="resumo", effect="slowpunch", min_dur=6.0, vars=scene_vars(RESUMO),
    narration="[excited] Orçamento, contrato e obra: de duas horas para cinco minutos.",
    sfx=[("fall", Beat(RESUMO["strikeAt"], 0.1)), ("cash", Beat(RESUMO["nowAt"], COUNTER_LANDS_AFTER)),
         *[("tick", Beat(at, 0.1)) for at in RESUMO["checksAt"]]],
)
scene(
    id="cta", effect="slowpunch", min_dur=5.0, blend=0.5,
    narration="[excited] Conheça os planos da Legaliza Obra, em legalizaobra ponto com barra preços.",
    sfx=[("swoosh", 0.0), ("ding2", Beat(0.35, 0.15))],
)


def main():
    app_clips.ensure(APP_CLIPS)
    for scene_id, (clip_name, segments) in CUTS.items():
        app_clips.cut(clip_name, segments, f"{scene_id}-cut")
    voiceover = VOICEOVER if os.environ.get("ELEVENLABS_API_KEY") else None
    build(sb, name="orcamento-obra", hyperframes=SCENES, theme_files=HF_THEME, poster_scene="fluxo",
          voiceover=voiceover, size=VERTICAL)


if __name__ == "__main__":
    main()
