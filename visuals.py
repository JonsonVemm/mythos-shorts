"""
Aquisição de imagens — custo zero, com cache e respeito ao rate-limit.

Fonte principal: Wikimedia Commons (gravuras de Dore, vasos gregos, esculturas,
iluminuras, pinturas antigas — tudo dominio publico).
Fonte secundaria: biblioteca local em assets/images/.

Cache: cada arquivo baixado fica em assets/images/cache/<hash>.ext e e reusado
em qualquer video futuro. Quanto mais o canal roda, menos rede ele precisa.
"""
from __future__ import annotations

import hashlib
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from config import IMAGES_LIB

UA = {"User-Agent": "MythosShortsBot/1.0 (personal automated channel; educational use)"}
API = "https://commons.wikimedia.org/w/api.php"
CACHE = IMAGES_LIB / "cache"

# corta resultados fora do clima do canal (fotos cientificas, mapas, logos...)
BAD_WORDS = ("logo", "icon", "map", "flag", "diagram", "chart", "graph",
             "coat of arms", "seal", "signature", "screenshot", "poster",
             "book cover", "title page", "advertisement", "specimen",
             "holotype", "paratype", "phylogenetic", "taxonomy", "preserved",
             "coloration", "microscope", "macro", "distribution", "chart",
             "comparison", "variation in", "graphic",
             # documentos e cartografia: quebram o clima de arte mitologica
             "mapa", "carta", "atlas", "cartograph", "survey", "topograph",
             "plan of", "planta", "sketch of the coast", "nautical",
             "sheet music", "frontispiece", "letter", "document",
             "portrait of a man", "engraved title")

# usadas no fim de toda busca: garantem que o video nunca fique sem imagem
FALLBACK_QUERIES = (
    "Gustave Dore engraving",
    "ancient greek vase painting",
    "roman marble sculpture",
    "dark forest etching",
    "medieval manuscript illumination",
    "storm clouds oil painting",
)
GOOD_WORDS = ("engraving", "etching", "drawing", "painting", "sculpture",
              "vase", "statue", "illustration", "woodcut", "lithograph",
              "fresco", "frieze", "relief", "bust")
STOP = {"the", "of", "and", "a", "an", "in", "on", "with", "for", "de", "da", "do"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^File:", "", title)).strip()


def _score(info: dict, title: str, query: str) -> float:
    """0 = descartado. Quanto maior, melhor para um Short vertical."""
    w, h = info.get("width", 0), info.get("height", 0)
    if w < 900 or h < 900:
        return -1                        # baixa resolucao
    ar = h / max(w, 1)
    if ar < 0.70 or ar > 2.6:
        return -1                        # largo demais ou tira fina: corta mal em 9:16
    low = title.lower()
    if any(b in low for b in BAD_WORDS):
        return -1

    # relevancia: a imagem precisa compartilhar termo com a busca
    qt, tt = _tokens(query), _tokens(title)
    overlap = len(qt & tt)
    if qt and overlap == 0:
        return -1

    score = min(w * h / 1e6, 10)         # resolucao
    score += 4.0 * overlap               # casamento com a query
    score += 3.0 if ar > 0.95 else 0     # retrato/quadrado enquadra melhor
    score += 2.0 if any(g in low for g in GOOD_WORDS) else 0
    return score


def _get(url: str, **kw):
    """GET com retry/backoff para o 429 do Wikimedia."""
    delay = 1.0
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(delay)
            delay *= 2
    if last:
        print(f"   [visuals] falhou apos retries: {last}")
    return None


def search_commons(query: str, limit: int = 20) -> list[dict]:
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": query,
        "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 2000,
    }
    try:
        r = requests.get(API, params=params, headers=UA, timeout=30)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:
        print(f"   [visuals] busca falhou ({query}): {e}")
        return []

    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        title = p.get("title", "")
        s = _score(ii, title, query)
        if s < 0:
            continue
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            continue
        out.append({
            "url": url.split("?")[0],           # remove parametros utm
            "title": _clean_title(title),
            "score": s,
            "width": ii.get("width"), "height": ii.get("height"),
            "page": ii.get("descriptionurl", ""),
        })
    out.sort(key=lambda x: -x["score"])
    return out


def _cache_path(url: str) -> Path:
    """Nome de arquivo estavel a partir da URL (cache permanente)."""
    h = hashlib.md5(url.encode()).hexdigest()[:16]
    ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return CACHE / f"{h}{ext}"


def fetch(url: str) -> Path | None:
    dest = _cache_path(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 40_000:
        return dest                          # já em cache
    r = _get(url)
    if r is None:
        return None
    dest.write_bytes(r.content)
    if dest.stat().st_size < 40_000:
        dest.unlink(missing_ok=True)
        return None
    time.sleep(0.4)                          # gentileza com o servidor
    return dest


def local_library(limit: int = 60) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return [p for p in IMAGES_LIB.rglob("*")
            if p.suffix.lower() in exts and "cache" not in p.parts][:limit]


def generated_library(queries: list[str], limit: int = 5) -> list[Path]:
    """Encontra pacotes IA nomeados pelo personagem (ex.: generated/zeus)."""
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    # A primeira query é o titulo do personagem, inserido pelo orquestrador.
    # Não usar todas as queries: o LLM pode citar outro mito como referência
    # visual e isso misturaria, por exemplo, Zeus no vídeo da Iara.
    tokens = _tokens(queries[0]) if queries else set()
    generated = IMAGES_LIB / "generated"
    files = [p for p in generated.rglob("*") if p.suffix.lower() in exts] if generated.exists() else []
    matched = [p for p in files if any(tok in p.name.lower() or tok in str(p.parent).lower() for tok in tokens)]
    random.shuffle(matched)
    return matched[:limit]


def gather_images(queries: list[str], need: int) -> list[dict]:
    """
    Devolve `need` imagens unicas prontas para uso, tentando cada query e
    completando com a biblioteca local se preciso.

    IMPORTANTE: os downloads sao SERIAIS. Em paralelo o Wikimedia responde 429
    e quase nada desce (medido: 1/15 em paralelo contra 4/5 em serie).
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    # Pacote visual gerado para o personagem ganha prioridade sobre arte
    # genérica do Commons. Assim Zeus e Iara têm identidade consistente.
    ai_pack = generated_library(queries, need)
    if len(ai_pack) >= need:
        return [{"file": p, "title": p.name, "page": "", "url": str(p),
                 "score": 100, "width": 0, "height": 0} for p in ai_pack]
    t_start = time.time()
    deadline = t_start + 180.0
    seen: set[str] = set()
    per_query: list[list[dict]] = []

    # 1) uma lista por query, sem misturar
    for q in list(queries) + list(FALLBACK_QUERIES):
        if time.time() - t_start > 70:
            break
        found = []
        for cand in search_commons(q):
            if cand["title"] in seen:
                continue
            seen.add(cand["title"])
            found.append(cand)
        if found:
            per_query.append(found)

    # 2) RODIZIO entre as queries: garante variedade visual (sem isso, a busca
    #    que pontua mais alto domina o video inteiro e fica repetitivo)
    cands: list[dict] = []
    for rank in range(6):
        for lst in per_query:
            if rank < len(lst):
                cands.append(lst[rank])
        if len(cands) >= need * 4:
            break

    # 3) baixa em serie ate juntar o necessario
    picked: list[dict] = []
    for cand in cands[: need * 4]:
        if len(picked) >= need or time.time() > deadline:
            break
        f = fetch(cand["url"])
        if f is None:
            continue
        cand["file"] = f
        picked.append(cand)

    if len(picked) < need:
        pool = list(local_library())
        random.shuffle(pool)
        for p in pool:
            if len(picked) >= need:
                break
            picked.append({"file": p, "title": p.name, "page": "", "url": str(p),
                           "score": 0, "width": 0, "height": 0})

    return picked[:need]


def credits(images: list[dict]) -> str:
    lines = []
    for im in images:
        if im.get("page"):
            lines.append(f"- {im['title'][:110]} — {im['page']}")
    return "\n".join(lines)


if __name__ == "__main__":
    got = gather_images(
        ["Curupira", "Gustave Dore forest engraving", "Dante Inferno dark forest",
         "greek vase painting Hades", "ancient roman statue underworld"], 5)
    for g in got:
        print(f"{g['score']:6.1f} {g['width']}x{g['height']} | {g['file'].name} | {g['title'][:60]}")
    print("total:", len(got))
