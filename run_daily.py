#!/usr/bin/env python3
"""
Roda o Short do dia: roteiro -> voz -> imagens -> trilha -> render -> YouTube.

Uso:
  python3 run_daily.py                 # gera o video do dia (nao publica)
  python3 run_daily.py --upload        # gera e publica
  python3 run_daily.py --topic medusa  # forca um tema do banco
  python3 run_daily.py --upload --privacy unlisted
  python3 run_daily.py --publish-at 2026-10-05T21:00:00Z   # agenda
  python3 run_daily.py --dry-run       # nao consome LLM: usa roteiro fixo

Cada execucao deixa um log em logs/ e um .json ao lado do video com titulo,
descricao e tags (util para subir na mao se quiser).
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config import (CHANNEL_NAME, CTA_TEXT, HOOK_LABEL, MIN_SHOTS, OUTPUT,
                    ROOT, STATE_FILE, WORK)
from render import probe, render
from script_gen import generate_script, narration
from topics import TOPICS, next_topic
from tts import narrate

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(run_id: str) -> logging.Logger:
    logger = logging.getLogger("mythos")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S")

    fh = logging.FileHandler(LOG_DIR / f"{run_id}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"posted": [], "history": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


DRY_SCRIPT = {
    "hook": "Você sabia que nem todo morto aceitava ficar na tumba?",
    "story": [
        "Em algumas lendas, a terra rejeitava quem morria carregando uma dívida.",
        "O corpo então se levantava e caminhava até a casa que o devia.",
    ],
    "surprise": "O coveiro jurou ter ouvido passos dentro do caixão lacrado.",
    "final": "Na manhã seguinte, encontraram apenas as botas dele dentro da sepultura.",
    "beats": [
        "Em algumas lendas, a terra rejeitava quem morria carregando uma dívida.",
        "O corpo então se levantava e caminhava até a casa que o devia.",
        "O coveiro jurou ter ouvido passos dentro do caixão lacrado.",
        "Na manhã seguinte, encontraram apenas as botas dele dentro da sepultura.",
    ],
    "cta": "Siga para mais curiosidades.",
    "title": "A Curiosidade que Ninguém Conta #Shorts",
    "description": "Em algumas tradicoes, a terra recusa quem morreu em divida. "
                   "O corpo se levanta e caminha ate a casa que o devia.",
    "tags": ["mitologia", "folclore", "curiosidades", "shorts"],
    "image_queries": ["Gustave Dore engraving cemetery", "dark forest etching",
                      "medieval manuscript illumination death"],
    "music_mood": "tenso",
    "thumbnail_query": "graveyard moonlight engraving",
    "_topic_id": "dryrun",
    "_topic_title": "O Morto que Recusa a Sepultura",
    "_word_count": 0,
}


def build_short(topic: dict, workdir: Path, log: logging.Logger,
                dry_run: bool = False) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # 1) roteiro
    if dry_run:
        script = dict(DRY_SCRIPT)
        script["_topic_id"] = topic["id"]
        script["_topic_title"] = topic["titulo"]
        log.info("roteiro: DRY RUN (%s)", topic["titulo"])
    else:
        script = generate_script(topic)
        log.info("roteiro: %s | %d palavras | humor %s",
                 topic["titulo"], script["_word_count"], script["music_mood"])

    # 2) narracao
    text = narration(script)
    voice_path = workdir / "voz.mp3"
    nar = narrate(text, voice_path)
    log.info("voz: %.2fs | %d palavras cronometradas | rate %s",
             nar.duration, len(nar.words), nar.rate)

    # 3) imagens
    from visuals import credits, gather_images
    # O nome do personagem entra primeiro para ativar o pacote visual IA
    # específico (quando existir), antes das queries ilustrativas do LLM.
    visual_queries = [topic["titulo"]] + script["image_queries"]
    images = gather_images(visual_queries, MIN_SHOTS)
    if len(images) < 3:
        raise RuntimeError(f"imagens insuficientes: {len(images)}")
    log.info("imagens: %d (%s)", len(images),
             ", ".join(im["title"][:28] for im in images[:3]))

    # 4) trilha
    from music import pick_music
    music, music_src = pick_music(script["music_mood"], nar.duration + 1.0, workdir)
    log.info("trilha: %s", music_src)

    # 5) render
    out = workdir / "short.mp4"
    render(images=[im["file"] for im in images], words=nar.words, voice=voice_path,
           music=music, headline=script["_topic_title"], cta=CTA_TEXT,
           label=HOOK_LABEL, out=out, workdir=workdir)

    info = probe(out)
    vstream = next(s for s in info["streams"] if s.get("width"))
    log.info("render: %sx%s %.2fs %.1f MB",
             vstream["width"], vstream["height"],
             float(info["format"]["duration"]),
             int(info["format"]["size"]) / 1e6)
    log.info("tempo total do pipeline: %.1fs", time.time() - t0)

    return {"script": script, "video": out, "images": images,
            "duration": float(info["format"]["duration"]),
            "credits": credits(images), "music": music_src, "voice_rate": nar.rate}


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera o Short diario de mitologia.")
    ap.add_argument("--topic", help="id do tema (veja topics.py)")
    ap.add_argument("--upload", action="store_true", help="publica no YouTube")
    ap.add_argument("--privacy", default=None, help="public | unlisted | private")
    ap.add_argument("--publish-at", default=None, help="ISO 8601 UTC para agendar")
    ap.add_argument("--dry-run", action="store_true", help="sem chamada de LLM")
    ap.add_argument("--keep-work", action="store_true", help="mantem arquivos temporarios")
    args = ap.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d")
    log = setup_logging(run_id)
    log.info("=== %s | inicio da geracao ===", CHANNEL_NAME)

    state = load_state()
    if args.topic:
        match = [t for t in TOPICS if t["id"] == args.topic]
        if not match:
            log.error("tema '%s' nao existe em topics.py", args.topic)
            return 2
        topic = match[0]
    else:
        topic = next_topic(set(state["posted"]))

    workdir = WORK / f"{run_id}_{topic['id']}"
    if workdir.exists():
        shutil.rmtree(workdir)

    try:
        result = build_short(topic, workdir, log, dry_run=args.dry_run)
    except Exception as e:
        log.exception("FALHOU: %s", e)
        return 1

    # ---- arquiva o video final ----
    final = OUTPUT / f"{run_id}_{topic['id']}.mp4"
    shutil.copy2(result["video"], final)
    log.info("arquivo final: %s", final)

    from upload import build_description
    title = result["script"]["title"]
    description = build_description(result["script"], result["credits"], CHANNEL_NAME)
    meta = {
        "topic_id": topic["id"],
        "title": title,
        "narrative_structure": "GANCHO -> HISTORIA -> SURPRESA -> FINAL -> CTA",
        "hook": result["script"].get("hook", ""),
        "story": result["script"].get("story", result["script"].get("beats", [])[:2]),
        "surprise": result["script"].get("surprise", ""),
        "final": result["script"].get("final", ""),
        "cta": result["script"].get("cta", ""),
        "description": description,
        "tags": result["script"]["tags"],
        "video": str(final),
        "duration": result["duration"],
        "music": result["music"],
        "voice_rate": result["voice_rate"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUTPUT / f"{run_id}_{topic['id']}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- publica ----
    if args.upload:
        try:
            from upload import upload as yt_upload
            res = yt_upload(final, title, description, result["script"]["tags"],
                            privacy=args.privacy, publish_at=args.publish_at)
            meta["youtube"] = res
            log.info("PUBLICADO: %s", res["url"])
        except Exception as e:
            log.error("upload falhou: %s", e)
            log.error("o video continua salvo em %s — suba na mao se quiser", final)
            save_state({**state, "history": state["history"] + [meta]})
            return 1

    state["posted"] = list(dict.fromkeys(state["posted"] + [topic["id"]]))
    state["history"] = state["history"] + [meta]
    save_state(state)

    if not args.keep_work and workdir.exists():
        shutil.rmtree(workdir, ignore_errors=True)

    log.info("=== concluido ===")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
