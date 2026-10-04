"""
Trilha sonora sem custo — versão épica e luminosa.

A versão anterior usava drone grave, ruído filtrado e impactos em baixa
frequência. Isso criava a sensação de "motor" atrás da voz. Agora a trilha é
um bed cinematográfico maior e feliz: arpejo em escala maior, cordas em staccato,
sinos brilhantes e batida leve. Sem drone contínuo, sem ruído, sem subgrave.

Se houver um arquivo em assets/music/, ele continua tendo prioridade.
"""
from __future__ import annotations

import random
import struct
import subprocess
from pathlib import Path

import numpy as np

from config import MUSIC_LIB

SR = 44100

# Cada mood agora usa acordes maiores e pouca energia abaixo de 100 Hz.
MOODS = {
    "epico": {"root": 130.81, "scale": [0, 4, 7, 12, 16, 19], "bpm": 104, "brightness": 1.0},
    "misterio": {"root": 146.83, "scale": [0, 3, 7, 10, 12, 15], "bpm": 92, "brightness": 0.78},
    "tenso": {"root": 123.47, "scale": [0, 3, 7, 10, 12, 15], "bpm": 100, "brightness": 0.70},
    "melancolico": {"root": 130.81, "scale": [0, 3, 7, 12, 15, 19], "bpm": 86, "brightness": 0.72},
}


def _tone(freq: float, length: float, amp: float, bright: float) -> np.ndarray:
    n = max(1, int(SR * length))
    t = np.arange(n) / SR
    # mistura de seno + harmonico macio; sem onda quadrada agressiva
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.24 * bright * np.sin(2 * np.pi * freq * 2 * t)
    sig += 0.08 * bright * np.sin(2 * np.pi * freq * 3 * t)
    attack = min(int(SR * 0.025), n // 4)
    release = min(int(SR * 0.18), n // 2)
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] *= np.linspace(1, 0, release)
    return sig * env * amp


def _kick(length: float = 0.20) -> np.ndarray:
    n = int(SR * length)
    t = np.arange(n) / SR
    f = 115 - 55 * (t / length)
    env = np.exp(-18 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env * 0.18


def _shaker(length: float = 0.08, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * length)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    env = np.exp(-35 * t)
    return noise * env * 0.018


def compose(mood: str = "epico", duration: float = 30.0, seed: int | None = None) -> np.ndarray:
    """Compõe uma trilha cinematográfica alegre, sem drone nem ruído contínuo."""
    seed = seed if seed is not None else random.randint(1, 10_000)
    rng = np.random.default_rng(seed)
    cfg = MOODS.get(mood, MOODS["epico"])
    n = int(SR * duration)
    out = np.zeros(n, dtype=np.float64)
    root, bpm, bright = cfg["root"], cfg["bpm"], cfg["brightness"]
    beat = 60.0 / bpm

    # Arpejo maior: sobe e desce, dando sensação de aventura e movimento.
    step = beat / 2
    notes = [cfg["scale"][i % len(cfg["scale"])] for i in range(int(duration / step) + 2)]
    for i, semi in enumerate(notes):
        t0 = i * step
        if t0 >= duration:
            break
        f = root * (2 ** (semi / 12))
        # oitavas alternadas para não ficar fino demais
        if i % 8 in (4, 5, 6, 7):
            f *= 2
        seg = _tone(f, min(step * 1.75, 0.34), 0.10 * bright, bright)
        s, e = int(t0 * SR), min(n, int(t0 * SR) + len(seg))
        out[s:e] += seg[:e - s]

    # Acordes curtos de cordas/sintetizador a cada 2 compassos.
    bar = beat * 4
    chords = [[0, 4, 7], [7, 11, 14], [9, 12, 16], [5, 9, 12]]
    for k, chord in enumerate(chords * (int(duration / (bar * 2)) + 1)):
        t0 = k * bar * 2
        if t0 >= duration:
            break
        for j, semi in enumerate(chord):
            f = root * (2 ** ((semi % 12) / 12)) * (1 if j == 0 else 2)
            seg = _tone(f, min(bar * 1.65, duration - t0), 0.045 * bright, bright)
            s, e = int(t0 * SR), min(n, int(t0 * SR) + len(seg))
            out[s:e] += seg[:e - s]

    # Batida leve: marca o ritmo sem virar ruído ou motor.
    for k in range(int(duration / beat) + 1):
        t0 = k * beat
        s = int(t0 * SR)
        if s >= n:
            break
        seg = _kick(0.20) if k % 4 == 0 else _shaker(0.07, seed + k)
        e = min(n, s + len(seg))
        out[s:e] += seg[:e - s]

    # Sinos pontuais no fim de frases: brilho, não ambiente constante.
    for t0 in np.arange(3.5, duration, 7.0):
        f = root * (2 ** (rng.choice([12, 16, 19]) / 12))
        seg = _tone(f, 0.65, 0.045 * bright, 1.0)
        s, e = int(t0 * SR), min(n, int(t0 * SR) + len(seg))
        out[s:e] += seg[:e - s]

    # Fades; nenhuma convolução ou camada de ruído contínuo.
    fi, fo = int(SR * 0.35), int(SR * 1.2)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    out /= np.abs(out).max() + 1e-9
    return (out * 0.78).astype(np.float32)


def write_wav(sig: np.ndarray, path: Path) -> Path:
    path = Path(path)
    pcm = np.clip(sig, -1, 1)
    pcm = (pcm * 32767).astype("<i2").tobytes()
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    path.write_bytes(header + pcm)
    return path


def pick_music(mood: str, duration: float, workdir: Path) -> tuple[Path, str]:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    exts = {".mp3", ".wav", ".m4a", ".ogg"}
    lib = [p for p in MUSIC_LIB.rglob("*") if p.suffix.lower() in exts] if MUSIC_LIB.exists() else []
    if lib:
        matching = [p for p in lib if mood.lower() in p.stem.lower()]
        chosen = random.choice(matching or lib)
        return chosen, f"biblioteca:{chosen.name}"
    # Mesmo que o roteirista escolha "tenso" ou "misterio", o canal agora
    # tem identidade épica e positiva. Esses moods só continuam disponíveis
    # para uma biblioteca manual em assets/music/.
    sig = compose(mood="epico", duration=duration + 0.5)
    path = write_wav(sig, workdir / "bed_epico.wav")
    return path, "procedural:epico-limpo-sem-drone"


if __name__ == "__main__":
    from config import WORK
    p, src = pick_music("epico", 31.0, WORK / "musictest")
    print(src, p)
