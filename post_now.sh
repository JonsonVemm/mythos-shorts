#!/usr/bin/env bash
# ============================================================================
# PONTO DE ENTRADA UNICO DA AUTOMACAO
#
# E isto que o agendador (Manus ScheduleTask ou cron) deve chamar:
#     bash /home/ubuntu/mythos-shorts/post_now.sh
#
# Ele gera o Short do dia e publica no YouTube. Toda a inteligencia esta no
# Python; o agendador so precisa disparar esta linha — e por isso que o custo
# de automacao e minimo.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

# carrega variaveis de ambiente do sandbox (chaves de API), se existirem
[ -f /home/ubuntu/.user_env ] && set -a && . /home/ubuntu/.user_env && set +a

mkdir -p logs

DATA=$(date -u +%Y%m%d)
python3 run_daily.py --upload 2>&1 | tee "logs/${DATA}_run.log"

# devolve a URL do Short publicado (o agendador reporta isso ao usuario)
grep -o 'https://youtube.com/shorts/[A-Za-z0-9_-]*' "logs/${DATA}_run.log" | tail -1 || true