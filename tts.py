"""
Narracao gratuita + timestamps por palavra.

edge-tts usa as vozes neurais do Microsoft Edge: qualidade alta, custo zero e
retorna o instante exato de cada palavra (WordBoundary), que e o que permite
legenda karaoke sincronizada — o maior fator de retencao em Shorts.
"""
from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import edge_tts

from config import MAX_SECONDS, VOICE, VOICE_PITCH


@dataclass
class Narration:
    audio: Path
    duration: float
    words: list[dict] = field(default_factory=list)   # [{t0, t1, text}]
    rate: str = "+0%"


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


async def _synth(text: str, out: Path, rate: str) -> list[dict]:
    # boundary="WordBoundary" é essencial: o padrão do edge-tts 7.x é
    # SentenceBoundary, que não dá o tempo de cada palavra.
    com = edge_tts.Communicate(text=text, voice=VOICE, rate=rate,
                               pitch=VOICE_PITCH, boundary="WordBoundary")
    words: list[dict] = []
    with open(out, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # edge-tts entrega offset/duration em unidades de 100 ns
                t0 = chunk["offset"] / 1e7
                t1 = (chunk["offset"] + chunk["duration"]) / 1e7
                words.append({"t0": t0, "t1": t1, "text": chunk["text"]})
    return words


def _calibrate(words: list[dict], duration: float) -> list[dict]:
    """
    Corrige pequeno desvio entre os timestamps do Edge e o MP3 real.
    Ajuste afim simples: ancora o fim da ultima palavra no fim do audio.
    """
    if not words:
        return words
    last = words[-1]["t1"]
    if last <= 0 or duration <= 0:
        return words
    # se o desvio relativo for grande demais, distribui proporcionalmente
    scale = duration / (last + 0.12) if last > 0.5 else 1.0
    if abs(scale - 1.0) > 0.03:
        for w in words:
            w["t0"] *= scale
            w["t1"] *= scale
    return words


def narrate(text: str, out_path: Path, timeout_s: float = 60.0) -> Narration:
    """
    Gera a locucao. Se passar de MAX_SECONDS, regrava mais rapido — assim
    TODO video sai com ~30s sem precisar reescrever o roteiro.
    """
    out_path = Path(out_path)
    rate = "+0%"
    words = asyncio.run(_synth(text, out_path, rate))
    dur = _duration(out_path)

    tried = 0
    while dur > MAX_SECONDS and tried < 4:
        tried += 1
        pct = min(25, int(round((dur / (MAX_SECONDS - 0.5) - 1.0) * 100)) + 4)
        rate = f"+{pct}%"
        words = asyncio.run(_synth(text, out_path, rate))
        dur = _duration(out_path)

    return Narration(audio=out_path, duration=dur, words=_calibrate(words, dur), rate=rate)


if __name__ == "__main__":
    from pathlib import Path as P
    import json
    n = narrate(
        "Medusa nao nasceu monstro. Nasceu sacerdotisa. "
        "A pena veio de um deus, nao de um crime. "
        "Uma unica olhada e o corpo vira pedra. "
        "Siga para mais mitos.",
        P("/tmp/test_narr.mp3"),
    )
    print("duracao:", n.duration, "rate:", n.rate)
    print(json.dumps(n.words[:6], ensure_ascii=False, indent=2))
