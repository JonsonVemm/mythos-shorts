#!/usr/bin/env python3
"""
Producao em lote: gera varios Shorts de uma vez e agenda cada um num horario.

Por que isso economiza credito: em vez de acordar o Manus todo dia (1 execucao
por dia), voce acorda UMA vez e produz a semana inteira. A automacao passa a
rodar 1x/semana em vez de 7x.

Uso:
  python3 batch.py --count 5 --hour 20 --upload
  python3 batch.py --count 5 --hour 20 --start 2026-10-06 --upload

ATENCAO - cota da API do YouTube:
  videos.insert custa 1.600 unidades e a cota padrao e 10.000/dia.
  Ou seja: no maximo ~6 uploads por dia (padrao). Com --count acima de 6,
  peca aumento de cota no Google Cloud (formulario de quota) ou divida em dias.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone

from config import CHANNEL_NAME, OUTPUT, ROOT, WORK
from run_daily import build_short, load_state, save_state, setup_logging
from topics import TOPICS, next_topic


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5, help="quantos videos gerar")
    ap.add_argument("--hour", type=int, default=20, help="hora local (UTC-3) da publicacao")
    ap.add_argument("--start", help="primeiro dia (YYYY-MM-DD). Padrao: amanha")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--privacy", default=None)
    args = ap.parse_args()

    log = setup_logging(f"batch_{datetime.now(timezone.utc):%Y%m%d}")
    state = load_state()
    posted = set(state["posted"])

    first = (datetime.fromisoformat(args.start).date() if args.start
             else (datetime.now(timezone.utc) + timedelta(days=1)).date())

    index_path = ROOT / "batch_index.json"
    catalog = []
    ok = 0

    for i in range(args.count):
        topic = next_topic(posted)
        posted.add(topic["id"])
        day = first + timedelta(days=i)
        # hora local (UTC-3) -> UTC
        publish_at = datetime(day.year, day.month, day.day, args.hour + 3, 0, 0,
                              tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

        log.info("--- [%d/%d] %s -> %s ---", i + 1, args.count, topic["titulo"], publish_at)
        workdir = WORK / f"batch_{day:%Y%m%d}_{topic['id']}"
        if workdir.exists():
            shutil.rmtree(workdir)

        try:
            res = build_short(topic, workdir, log)
        except Exception as e:
            log.exception("falhou no tema %s: %s", topic["id"], e)
            continue

        final = OUTPUT / f"{day:%Y%m%d}_{topic['id']}.mp4"
        shutil.copy2(res["video"], final)

        from upload import build_description
        title = res["script"]["title"]
        desc = build_description(res["script"], res["credits"], CHANNEL_NAME)

        entry = {"topic_id": topic["id"], "title": title, "video": str(final),
                 "publish_at": publish_at, "description": desc,
                 "tags": res["script"]["tags"], "duration": res["duration"]}

        if args.upload:
            try:
                from upload import upload as yt_upload
                r = yt_upload(final, title, desc, res["script"]["tags"],
                              privacy=args.privacy, publish_at=publish_at)
                entry["youtube"] = r
                log.info("agendado: %s (%s)", r["url"], publish_at)
                ok += 1
            except Exception as e:
                log.error("upload falhou (%s): %s", topic["id"], e)
                entry["error"] = str(e)
        else:
            ok += 1

        catalog.append(entry)
        shutil.rmtree(workdir, ignore_errors=True)

    state["posted"] = list(posted)
    state["history"] = state["history"] + catalog
    save_state(state)
    index_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    log.info("=== lote concluido: %d/%d ok — indice em %s ===", ok, args.count, index_path)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())