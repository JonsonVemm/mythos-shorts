# Mitos em 30 segundos — Shorts de mitologia automatizados

Pipeline que produz e publica **1 Short de ~30 s por dia** sobre mitologia e
folclore, em português, gastando praticamente nada.

Todo roteiro segue **GANCHO → HISTÓRIA → SURPRESA → FINAL → CTA** e começa
por personagens populares como Zeus, Medusa, Hades, Thor, Loki e Iara, sempre
explicando a curiosidade para quem ainda não conhece o mito.

> **Leia o [GUIA.md](GUIA.md)** — ele tem o passo a passo de configuração do
> YouTube, as opções de automação e as regras para usar o Manus gastando o
> mínimo de tokens. Este README é só o resumo.

## Início rápido

```bash
cd /home/ubuntu/mythos-shorts

python3 run_daily.py --dry-run --topic medusa   # teste completo, sem gastar LLM
python3 run_daily.py                            # gera o Short do dia
python3 run_daily.py --upload                   # gera e publica
python3 batch.py --count 5 --hour 20 --upload   # semana inteira, agendada
```

Para publicar, primeiro rode uma vez:

```bash
python3 auth_setup.py     # autorização do YouTube (1x, funciona sem navegador)
```

## Como funciona

| Etapa | Ferramenta | Custo |
|---|---|---|
| Roteiro de 30 s | LLM (gpt-5-mini, `reasoning=low`) | ~US$ 0,002 |
| Narração pt-BR + tempo de cada palavra | edge-tts | R$ 0 |
| Arte (gravuras, esculturas, iluminuras) | Wikimedia Commons + cache | R$ 0 |
| Trilha dark ambient | biblioteca local ou compositor procedural | R$ 0 |
| Render 1080x1920 com legenda karaoke | FFmpeg | CPU local |

## Estrutura

```
config.py       toda a configuração (voz, canal, duração, loudness)
topics.py       banco de ~45 temas, sem repetir
script_gen.py   roteiro em JSON estrito (1 chamada de LLM)
tts.py          narração + timestamps por palavra
visuals.py      busca/download/cache de arte de domínio público
music.py        trilha (biblioteca local ou procedural)
render.py       Ken Burns, grade escuro, legendas .ass, mixagem
upload.py       publicação e agendamento no YouTube
auth_setup.py   OAuth (1x)
run_daily.py    pipeline do dia
batch.py        produção em lote agendada
post_now.sh     comando único para o agendador
agents.md       contexto do projeto para o agente Manus
```

## Regra de ouro

O vídeo do dia **não** deve ser produzido numa conversa com o agente — ele sai
de um script determinístico. O Manus entra só para montar, corrigir e evoluir
esse script. É isso que mantém o custo perto de zero.
