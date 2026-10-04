"""
Geracao de roteiro do Short (1 chamada de LLM por video).

A estrutura editorial e fixa em todo episodio:
  GANCHO -> HISTORIA -> SURPRESA -> FINAL -> CTA

O JSON tambem conserva `beats` como campo derivado para o renderizador: ele e a
sequencia falada (historia + surpresa + final), nao uma estrutura narrativa
solta.
"""
from __future__ import annotations

import json
import re

from openai import OpenAI

from config import LLM_MODEL

SYSTEM = """Voce e roteirista de um canal de curiosidades mitologicas no YouTube Shorts.
Escreve em portugues do Brasil, com tom cinematografico, epico, luminoso e
entusiasmado. Nao trate o tema como terror e nunca use "dark", "sombrio",
"assustador" ou "sem censura" no titulo, descricao ou roteiro.
O publico geralmente conhece o nome do personagem, mas nao conhece a
curiosidade. Explique o basico rapidamente e entregue um detalhe surpreendente.

ESTRUTURA OBRIGATORIA — NUNCA MUDE A ORDEM:
1. GANCHO: abra com uma curiosidade em forma de pergunta ou revelacao.
   Exemplo de formato: "Voce sabia que Zeus nao era originalmente o deus mais poderoso?"
   Maximo 15 palavras. Nao comece com "neste video".
2. HISTORIA: exatamente 2 frases curtas que explicam o contexto para quem nunca
   ouviu falar do mito. Cada uma tem sujeito e verbo, maximo 18 palavras.
3. SURPRESA: exatamente 1 frase com a virada ou fato pouco conhecido. Maximo 18 palavras.
4. FINAL: exatamente 1 frase que fecha com consequencia, imagem perturbadora ou
   pergunta que fica na cabeca. Maximo 16 palavras.
5. CTA: convite seco para seguir, maximo 6 palavras.

REGRAS DE RITMO:
- Soma do GANCHO + 2 frases da HISTORIA + SURPRESA + FINAL + CTA entre 70 e 84 palavras.
- Todas as frases precisam soar naturais em voz alta, com sujeito e verbo.
- Proibido frase nominal picada ou virgula empilhada.
- Cada frase avanca a historia; nao repita a mesma informacao.
- Nada de vocativo de youtuber ("atencao", "olha isso", "escuta", "voce nao vai acreditar").
- Texto puro: sem markdown, emojis, asteriscos, numeracao ou rótulos como "Gancho".
- Fidelidade ao mito: use elementos reais da tradicao. Pode dramatizar, nao inventar.
- O titulo deve ser popular e claro, com o nome do personagem + curiosidade.

image_queries: 5 buscas CURTAS em INGLES para Wikimedia Commons. Use somente
ARTE FIGURATIVA: gravura, pintura, escultura, vaso, iluminura ou baixo-relevo.
Exemplos: "Zeus statue lightning", "Medusa Caravaggio", "greek vase painting Hades".
Nunca peca mapa, carta nautica, bandeira, brasao, diagrama, planta, grafico,
capa de livro ou documento.

music_mood: prefira SEMPRE "epico"; use "misterio" somente se a curiosidade
precisar de suspense. Nunca use "tenso" ou "melancolico" neste canal.
"""

SCHEMA = {
    "name": "short_script",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "hook": {"type": "string"},
            "story": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
            "surprise": {"type": "string"},
            "final": {"type": "string"},
            "cta": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "image_queries": {"type": "array", "items": {"type": "string"}},
            "music_mood": {"type": "string", "enum": ["misterio", "tenso", "epico", "melancolico"]},
            "thumbnail_query": {"type": "string"},
        },
        "required": [
            "hook", "story", "surprise", "final", "cta", "title", "description",
            "tags", "image_queries", "music_mood", "thumbnail_query",
        ],
        "additionalProperties": False,
    },
}


def _words(text: str) -> int:
    return len(re.findall(r"[\wÀ-ÿ'-]+", text))


def _clean(text: str) -> str:
    return str(text).strip().replace("\n", " ")


def generate_script(topic: dict) -> dict:
    """Recebe um tema popular e devolve o roteiro com arco editorial fixo."""
    client = OpenAI()
    user = (
        f"PERSONAGEM/TEMA POPULAR: {topic['titulo']}\n"
        f"CURIOSIDADE OBRIGATORIA: {topic.get('angulo', '')}\n\n"
        "Escreva um Short de 30 segundos. Explique o personagem para um iniciante "
        "e depois entregue a curiosidade na SURPRESA. Preencha todos os campos."
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
        max_completion_tokens=4000,
        extra_body={"reasoning": {"effort": "medium"}},
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError(f"LLM sem conteudo (finish_reason={resp.choices[0].finish_reason}).")
    data = json.loads(content)

    # Higiene e compatibilidade: beats e a ordem falada depois do gancho.
    data["hook"] = _clean(data["hook"])
    data["story"] = [_clean(x) for x in data.get("story", [])[:2]]
    while len(data["story"]) < 2:
        data["story"].append("")
    data["surprise"] = _clean(data["surprise"])
    data["final"] = _clean(data["final"])
    data["cta"] = _clean(data["cta"])
    data["beats"] = data["story"] + [data["surprise"], data["final"]]

    total = _words(data["hook"]) + sum(_words(x) for x in data["beats"]) + _words(data["cta"])
    data["_word_count"] = total
    data["_topic_id"] = topic["id"]
    data["_topic_title"] = topic["titulo"]
    if not data["title"].lower().endswith("shorts"):
        data["title"] = f"{data['title'].strip()} #Shorts"

    queries = [q.strip() for q in data.get("image_queries", []) if q.strip()]
    for q in topic.get("queries", []):
        if len(queries) >= 6:
            break
        queries.append(q)
    data["image_queries"] = queries
    return data


def narration(script: dict) -> str:
    """Texto unico na ordem: GANCHO -> HISTORIA -> SURPRESA -> FINAL -> CTA."""
    parts = [script["hook"]] + [b for b in script["beats"] if b] + [script["cta"]]
    # Preserva ?/! do gancho e evita "?." ou ". ." na locucao.
    spoken = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part[-1] not in ".!?":
            part += "."
        spoken.append(part)
    return " ".join(spoken)


def segments(script: dict) -> list[str]:
    return [script["hook"]] + [b for b in script["beats"] if b] + [script["cta"]]


if __name__ == "__main__":
    from topics import TOPICS
    s = generate_script(TOPICS[0])
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print("\n--- NARRACAO ---\n" + narration(s))
    print("palavras:", s["_word_count"])
