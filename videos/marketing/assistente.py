#!/usr/bin/env python3
"""Storyboard for the "Legaliza Obra no Claude" intro: a wide pt-BR video that sells the Claude plugin, shows how
to add and connect it, and plays a real Claude session that runs a simulação.

Render:
  python build.py marketing/assistente                                  # edge-tts / Kokoro voice
  ELEVENLABS_API_KEY=... python build.py marketing/assistente           # ElevenLabs voiceover
Preview while editing scenes (after one render wrote index.html):
  cd videos/marketing/assistente-scenes && npx hyperframes@0.8.85 preview
"""
import os
from pathlib import Path

import app_clips
from engine import WIDE, Beat, Storyboard, build
from themes.legalizaobra import HF_THEME, TEAL, WHITE

SCENES = Path(__file__).resolve().parent / "assistente-scenes"
DEFAULT_CLAUDE_RECORDING = Path.home() / "Documents" / "LegalizaObra Videos" / "claude_video.mp4"
CLAUDE_RECORDING = Path(os.environ.get("CLAUDE_RECORDING", DEFAULT_CLAUDE_RECORDING)).expanduser()
CLAUDE_CLIP = "claude-simulacao"
PROMPT_SENT, CHAT_SHOWN, ALLOW_CLICKED, TABLE_SHOWN = 2.2, 2.25, 6.85, 10.7
CUTS = {
    "pedido": [(0.4, 2.7), (4.2, 8.6)],
    "resultado": [(8.35, 17.4)],
}
HOOK = {"typeAt": 0.04, "headAt": 0.42}
VALOR = {"subAt": 0.25, "chipsAt": (0.44, 0.58, 0.69, 0.86), "soonAt": 0.93}
PLUGIN = {"windowAt": 0.23, "typeAt": 0.52, "resultAt": 0.63, "addAt": 0.85}
CONECTAR = {"stepsAt": (0.15, 0.51), "permitAt": 0.85, "doneAt": 0.9}
SEGURO = {"checksAt": (0.49, 0.8)}
INSS_BEFORE, INSS_AFTER = 11680, 4976
RESULTADO = {"before": INSS_BEFORE, "after": INSS_AFTER, "strikeAt": 0.54, "nowAt": 0.71}
COUNTER_LANDS_AFTER = 1.2
VOICEOVER = {"voice": "nPczCjzI2devNBz1zQrb", "model": "eleven_v3", "settings": {"stability": 0.5, "speed": 1.08}}

sb = Storyboard()
scene = sb.scene
flash = sb.flash


def cut_clip(scene_id: str, clip_seconds: float) -> float:
    return app_clips.cut_time(CUTS[scene_id], clip_seconds)


def scene_vars(values: dict) -> dict:
    """Hand tuples to a composition as the comma-separated strings it splits."""
    return {key: ",".join(map(str, value)) if isinstance(value, tuple) else value for key, value in values.items()}


scene(
    id="hook", effect="slowpunch", min_dur=3.4, vars=HOOK,
    narration="[excited] E se você cuidasse das suas obras só conversando?",
    sfx=[("type", Beat(HOOK["typeAt"], 0.1)), ("impact", Beat(HOOK["headAt"], 0.1))],
)
scene(
    id="valor", effect="punch", min_dur=8.0, vars=scene_vars(VALOR),
    narration="Agora a Legaliza Obra funciona dentro do Claude. Você pede numa conversa, e o Claude simula o INSS, "
              "faz o orçamento, manda a obra ao eSocial e gera a guia DARF.",
    sfx=[*[("tick", Beat(at, 0.1)) for at in VALOR["chipsAt"]], ("swoosh", -0.3)],
)
flash(TEAL, 0.066)
scene(
    id="plugin", min_dur=6.0, vars=PLUGIN,
    narration="Conectar é rápido. No Claude, abra Personalizar, Plugins, e procure Legaliza Obra. Depois, clique em Adicionar.",
    sfx=[("type", Beat(PLUGIN["typeAt"], 0.1)), ("click", Beat(PLUGIN["addAt"]))],
)
scene(
    id="conectar", min_dur=6.0, vars=scene_vars(CONECTAR),
    narration="No plugin, abra Conectores e clique em Conectar. Entre com a sua conta e clique em Permitir.",
    sfx=[*[("tick", Beat(at, 0.1)) for at in CONECTAR["stepsAt"]], ("click", Beat(CONECTAR["permitAt"])),
         ("success", Beat(CONECTAR["doneAt"], 0.1)), ("swoosh", -0.3)],
)
flash(WHITE, 0.066)
scene(
    id="pedido", min_dur=6.6,
    vars={"chatAt": round(cut_clip("pedido", CHAT_SHOWN), 2), "allowAt": round(cut_clip("pedido", ALLOW_CLICKED), 2)},
    narration="Pronto. Agora é só pedir. O Claude chama a Legaliza Obra, e você autoriza.",
    sfx=[("click", cut_clip("pedido", PROMPT_SENT)), ("click", cut_clip("pedido", ALLOW_CLICKED))],
)
scene(
    id="resultado", min_dur=7.0, vars={**RESULTADO, "tableAt": round(cut_clip("resultado", TABLE_SHOWN), 2)},
    narration="Em segundos, a simulação está pronta. Nessa obra, o INSS cai de quase 12 mil para menos de 5 mil reais.",
    sfx=[("ding", cut_clip("resultado", TABLE_SHOWN)), ("fall", Beat(RESULTADO["strikeAt"], 0.1)),
         ("cash", Beat(RESULTADO["nowAt"], COUNTER_LANDS_AFTER)), ("swoosh", -0.3)],
)
scene(
    id="seguro", effect="punch", min_dur=5.0, vars=scene_vars(SEGURO),
    narration="E você continua no controle: o assistente sempre pede confirmação antes de enviar algo ao eSocial.",
    sfx=[("tick", Beat(at, 0.1)) for at in SEGURO["checksAt"]],
)
scene(
    id="cta", effect="slowpunch", min_dur=4.5, blend=0.5,
    narration="[excited] Conecte a Legaliza Obra ao Claude hoje.",
    sfx=[("swoosh", 0.0), ("ding2", Beat(0.35, 0.15))],
)


def main():
    app_clips.adopt(CLAUDE_RECORDING, CLAUDE_CLIP)
    for scene_id, segments in CUTS.items():
        app_clips.cut(CLAUDE_CLIP, segments, f"{scene_id}-cut")
    voiceover = VOICEOVER if os.environ.get("ELEVENLABS_API_KEY") else None
    build(sb, name="assistente", hyperframes=SCENES, theme_files=HF_THEME, poster_scene="resultado",
          voiceover=voiceover, size=WIDE)


if __name__ == "__main__":
    main()
