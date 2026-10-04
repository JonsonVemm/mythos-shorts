"""
Renderizacao do Short (1080x1920, 30 fps) com FFmpeg.

Pipeline:
  1. cada imagem vira um clipe com movimento Ken Burns (zoom/pan) + grade
     cinematografico escuro (contraste, dessaturacao, sombra azulada, vinheta,
     grao de filme);
  2. os clipes sao unidos com crossfade (xfade);
  3. legendas karaoke sincronizadas por palavra + titulo + CTA (arquivo .ass);
  4. audio: narracao + trilha com ducking (a musica abaixa sozinha quando a
     voz entra) e normalizacao de loudness.

Tudo local, tudo deterministico, tudo sem custo por video.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from config import (FPS, FONTS, H, MASTER_LUFS, MUSIC_VOLUME, TRANSITION, W)

# ---------------------------------------------------------------------------
# registro de movimentos de camera (variedade visual sem ficar repetitivo)
# ---------------------------------------------------------------------------
MOTIONS_PORTRAIT = [
    {"zoom": (1.00, 1.14), "x": (0.50, 0.50), "y": (0.50, 0.50)},   # aproxima
    {"zoom": (1.16, 1.02), "x": (0.50, 0.50), "y": (0.50, 0.50)},   # afasta
    {"zoom": (1.06, 1.22), "x": (0.50, 0.50), "y": (0.82, 0.18)},   # sobe
    {"zoom": (1.06, 1.22), "x": (0.50, 0.50), "y": (0.18, 0.82)},   # desce
    {"zoom": (1.04, 1.20), "x": (0.20, 0.80), "y": (0.50, 0.50)},   # pan direita
    {"zoom": (1.20, 1.04), "x": (0.80, 0.20), "y": (0.50, 0.50)},   # afasta + pan
]

# Obras em paisagem sao cortadas em 9:16: em vez de perder as laterais,
# a janela desliza pelo quadro (pan horizontal de verdade).
MOTIONS_LANDSCAPE = [
    {"axis": "x", "dir": (0.06, 0.94), "zoom": (1.00, 1.08)},
    {"axis": "x", "dir": (0.94, 0.06), "zoom": (1.00, 1.08)},
    {"axis": "x", "dir": (0.15, 0.85), "zoom": (1.12, 1.02)},
    {"axis": "x", "dir": (0.85, 0.15), "zoom": (1.02, 1.14)},
    {"zoom": (1.05, 1.26), "x": (0.50, 0.50), "y": (0.50, 0.50)},
    {"zoom": (1.26, 1.05), "x": (0.50, 0.50), "y": (0.50, 0.50)},
]


def image_ar(image: Path) -> float:
    """Proporcao altura/largura da imagem (1.0 = quadrada)."""
    try:
        from PIL import Image
        with Image.open(image) as im:
            w, h = im.size
        return h / max(w, 1)
    except Exception:
        return 1.0


def choose_motion(image: Path, index: int) -> dict:
    pool = MOTIONS_PORTRAIT if image_ar(image) >= 0.95 else MOTIONS_LANDSCAPE
    return pool[index % len(pool)]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou:\n{' '.join(cmd[:12])}...\n{p.stderr[-2500:]}")


# ---------------------------------------------------------------------------
# 1) clipes Ken Burns
# ---------------------------------------------------------------------------
def _zoompan_expr(motion: dict, frames: int) -> str:
    z0, z1 = motion["zoom"]
    # movimentos de paisagem so definem "dir"; o zoom fica centralizado
    x0, x1 = motion.get("x", (0.5, 0.5))
    y0, y1 = motion.get("y", (0.5, 0.5))
    z = f"{z0}+({z1 - z0})*on/{max(frames - 1, 1)}"
    x = f"(iw-iw/zoom)*({x0}+({x1 - x0})*on/{max(frames - 1, 1)})"
    y = f"(ih-ih/zoom)*({y0}+({y1 - y0})*on/{max(frames - 1, 1)})"
    return f"z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS}"


def make_clip(image: Path, duration: float, out: Path, index: int, workdir: Path) -> Path:
    frames = max(int(round(duration * FPS)), 2)
    motion = choose_motion(image, index)
    big_w, big_h = W * 2, H * 2

    if motion.get("axis") == "x":
        # paisagem: escala pela altura e desliza uma janela 9:16 pelo quadro
        a, b = motion["dir"]
        pre = [
            f"scale=-2:{big_h}:flags=lanczos",
            f"crop={big_w}:{big_h}:"
            f"x='(in_w-out_w)*({a}+({b}-{a})*n/{frames - 1})':y='(in_h-out_h)/2'",
        ]
    else:
        pre = [
            f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase",
            f"crop={big_w}:{big_h}",
        ]

    vf = ",".join(pre + [
        "setsar=1",
        f"zoompan={_zoompan_expr(motion, frames)}",
        # ---- grade cinematografico epico e luminoso ----
        "eq=contrast=1.04:brightness=0.10:saturation=1.18:gamma=1.10",
        "colorbalance=rs=0.02:gs=0.02:bs=0.02:rm=0.01:bm=0.01",
        # sem vinheta pesada: o personagem precisa dominar o quadro
        "noise=alls=2:allf=t+u",
        "format=yuv420p",
    ])
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(image.resolve()),
        "-vf", vf, "-frames:v", str(frames), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", str(out.resolve()),
    ])
    return out


# ---------------------------------------------------------------------------
# 2) legendas / textos (arquivo .ass)
# ---------------------------------------------------------------------------
def _ts(t: float) -> str:
    t = max(t, 0.0)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def chunk_words(words: list[dict], max_words: int = 4, max_chars: int = 22) -> list[dict]:
    """Agrupa palavras em blocos legiveis (max. 4 palavras / 22 caracteres)."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x["text"] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [{"t0": c[0]["t0"], "t1": c[-1]["t1"], "words": c} for c in chunks]


def build_ass(words: list[dict], headline: str, cta: str, label: str,
              total: float, cta_at: float, path: Path) -> Path:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Marca,Archivo Black,40,&H00E8E8E8,&H00E8E8E8,&H00000000,&H80000000,0,0,0,0,100,100,4,0,1,3,0,8,60,60,70,1
Style: Titulo,Anton,110,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,7,3,8,70,70,300,1
Style: Legenda,Archivo Black,76,&H00FFFFFF,&H00999999,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,2,2,70,70,430,1
Style: CTA,Anton,86,&H0000D7FF,&H0000D7FF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,6,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev: list[str] = []

    # marca do canal (fixa)
    ev.append(f"Dialogue: 0,{_ts(0)},{_ts(total)},Marca,,0,0,0,,"
              f"{{\\fad(400,400)}}{_clean(label)}")

    # headline do tema (primeiros ~8s, com leve zoom de entrada)
    head_end = min(total - 0.2, max(6.5, total * 0.30))
    ev.append(
        f"Dialogue: 0,{_ts(0.15)},{_ts(head_end)},Titulo,,0,0,0,,"
        f"{{\\fad(350,350)\\fscx94\\fscy94\\t(0,500,\\fscx100\\fscy100)}}"
        f"{_clean(headline.upper())}"
    )

    # legendas karaoke
    # Um bloco por vez: cada legenda vai ate o inicio da proxima (com uma
    # folga minima). Sem isso, dois blocos ficam visiveis ao mesmo tempo e o
    # libass empilha as linhas, o que confunde a leitura.
    chunks = chunk_words(words)
    for i, ch in enumerate(chunks):
        txt = "".join(
            f"{{\\k{max(int(round((w['t1'] - w['t0']) * 100)), 4)}}}{_clean(w['text'])} "
            for w in ch["words"]
        ).strip()
        start = max(ch["t0"] - 0.12, 0.0)
        if i + 1 < len(chunks):
            end = min(chunks[i + 1]["t0"] - 0.05, total)
        else:
            end = min(ch["t1"] + 0.30, total)
        if end - start < 0.25:
            end = min(start + 0.25, total)
        ev.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Legenda,,0,0,0,,"
                  f"{{\\fad(70,70)}}{txt}")

    # CTA final
    ev.append(
        f"Dialogue: 0,{_ts(max(cta_at, 0.5))},{_ts(total)},CTA,,0,0,0,,"
        f"{{\\fad(250,150)\\fscx100\\fscy100\\t(0,300,\\fscx106\\fscy106)}}"
        f"{_clean(cta.upper())}"
    )

    path.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 3) montagem final
# ---------------------------------------------------------------------------
def render(images: list[Path], words: list[dict], voice: Path, music: Path,
           headline: str, cta: str, label: str, out: Path, workdir: Path,
           voice_delay: float = 0.35) -> Path:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    voice_dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(voice)], capture_output=True, text=True
    ).stdout.strip())
    total = round(voice_delay + voice_dur + 0.35, 3)

    n = len(images)
    clip_d = (total + (n - 1) * TRANSITION) / n

    # --- clipes ---
    clips = []
    for i, img in enumerate(images):
        c = workdir / f"clip_{i:02d}.mp4"
        make_clip(img, clip_d, c, i, workdir)
        clips.append(c)

    # --- legendas (as palavras sao deslocadas pelo delay da voz) ---
    shifted = [{"t0": w["t0"] + voice_delay, "t1": w["t1"] + voice_delay,
                "text": w["text"]} for w in words]
    ass = build_ass(shifted, headline, cta, label, total,
                    cta_at=max(0.0, total - 3.0), path=workdir / "legendas.ass")

    # --- grafo de video: xfade em cadeia ---
    vparts, vlabels = [], []
    for i, c in enumerate(clips):
        vparts.append(f"[{i}:v]setpts=PTS-STARTPTS[c{i}]")
        vlabels.append(f"c{i}")
    cur = vlabels[0]
    for k in range(1, n):
        offset = k * (clip_d - TRANSITION)
        outl = f"x{k}"
        vparts.append(
            f"[{cur}][{vlabels[k]}]xfade=transition=fade:"
            f"duration={TRANSITION}:offset={offset:.3f}[{outl}]"
        )
        cur = outl
    vparts.append(
        f"[{cur}]subtitles=filename=legendas.ass:fontsdir={FONTS},"
        f"format=yuv420p[vout]"
    )

    # --- grafo de audio: voz + trilha com ducking ---
    vi = f"{n}:a"       # entrada da voz
    mi = f"{n + 1}:a"   # entrada da musica
    aparts = [
        f"[{vi}]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"adelay={int(voice_delay * 1000)}|{int(voice_delay * 1000)},volume=1.0[vo]",
        f"[{mi}]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"atrim=0:{total},asetpts=N/SR/TB,volume={MUSIC_VOLUME}[mus]",
        "[vo]asplit=2[vo_mix][vo_key]",
        "[mus][vo_key]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=350:"
        "makeup=1:level_sc=1.4[mus_duck]",
        "[vo_mix][mus_duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]",
        f"[mix]loudnorm=I={MASTER_LUFS}:TP=-1.5:LRA=11,alimiter=limit=0.97[aout]",
    ]

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c.resolve())]
    cmd += ["-i", str(Path(voice).resolve())]
    cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
    cmd += ["-filter_complex", ";".join(vparts + aparts)]
    cmd += ["-map", "[vout]", "-map", "[aout]",
            "-t", f"{total}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-g", str(FPS * 2),
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart", str(Path(out).resolve())]
    run(cmd, cwd=workdir)

    return Path(out)


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,width,height,r_frame_rate,duration:format=duration,size",
         "-of", "json", str(path)], capture_output=True, text=True
    ).stdout
    import json
    return json.loads(out)
