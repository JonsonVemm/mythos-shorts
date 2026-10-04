# Mythos Sombrio — contexto do projeto (para o agente Manus)

> LEIA ESTE ARQUIVO ANTES DE QUALQUER COISA. Ele existe para que voce nao
> precise redescobrir nada: isso e o que economiza tokens nas proximas sessoes.

## O que e

Canal de curiosidades mitológicas no YouTube Shorts. 1 video de ~30s por dia, vertical
1080x1920, narrado em pt-BR, com legendas karaoke, arte de dominio publico e
trilha épica e luminosa.

**Estrutura editorial obrigatoria:** todo roteiro deve ser GANCHO -> HISTORIA
-> SURPRESA -> FINAL -> CTA. O gancho parte de uma curiosidade popular; a
historia explica o contexto para iniciantes; a surpresa entrega o fato pouco
conhecido; o final fecha com consequencia. `topics.py` prioriza personagens
populares (Zeus, Medusa, Hades, Afrodite, Thor, Loki, Odin, Hercules, Aquiles,
Anubis, Iara e Saci) antes de temas de nicho.

Diretorio: `/home/ubuntu/mythos-shorts`

## Como rodar

```bash
cd /home/ubuntu/mythos-shorts
python3 run_daily.py --dry-run --topic medusa   # teste, sem gastar LLM
python3 run_daily.py                            # gera o Short do dia
python3 run_daily.py --upload                   # gera e publica
python3 batch.py --count 5 --hour 20 --upload    # semana inteira, agendada
bash post_now.sh                                # entrada usada pelo agendador
```

## Arquitetura (nao mude sem motivo)

| Arquivo | Papel |
|---|---|
| `config.py` | TODA a configuracao (voz, duracao, canal, loudness). Mude aqui, nao nos outros. |
| `topics.py` | Banco de ~45 temas. `next_topic()` nunca repete. |
| `script_gen.py` | 1 chamada de LLM (gpt-5-mini, reasoning=low) -> GANCHO/HISTORIA/SURPRESA/FINAL em JSON estrito. ~US$0,002/video. |
| `tts.py` | edge-tts (gratis) + `boundary="WordBoundary"` para timestamps por palavra. |
| `visuals.py` | Wikimedia Commons + cache em `assets/images/cache/`. Nunca baixa 2x. |
| `music.py` | Usa `assets/music/` se houver; senão compõe trilha épica procedural (numpy). |
| `render.py` | FFmpeg: Ken Burns + grade escuro + xfade + .ass karaoke + ducking de audio. |
| `upload.py` | YouTube Data API v3. `--publish-at` agenda como privado. |
| `auth_setup.py` | OAuth uma unica vez (funciona sem navegador, com copiar/colar de URL). |
| `state.json` | Temas ja postados + historico. NAO apague. |

## Regras de ouro

1. **Nunca** use geracao de video/imagem/musica do Manus para o conteudo diario:
   o pipeline e inteiramente de custo zero (FFmpeg + edge-tts + Commons).
   Geracao por IA so para assets pontuais que ficam salvos para sempre.
2. Se o usuario pedir mudanca de estilo, ajuste `config.py` ou `render.py` —
   nunca reescreva o pipeline.
3. Antes de dizer que funcionou, rode `python3 run_daily.py --dry-run` e confira
   o MP4 com `ffprobe` (1080x1920, ~30s, audio presente).
4. Ao adicionar temas, edite `topics.py` no mesmo formato.
5. Ao adicionar trilhas, jogue os arquivos em `assets/music/` — o pipeline
   passa a usa-las automaticamente (o nome pode conter o mood: `epico_01.mp3`).
6. Cota do YouTube: 1.600 unidades por upload, 10.000/dia por padrao => ~6/dia.

## Custo por video (referencia)

- LLM: ~US$0,002
- Voz: R$0 (edge-tts)
- Imagens: R$0 (dominio publico)
- Trilha: R$0 (procedural)
- Render: minutos de CPU do sandbox
- **Total: praticamente zero.**
