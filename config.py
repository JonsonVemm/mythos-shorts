"""
Configuração central do canal de curiosidades mitológicas (YouTube Shorts).

Tudo que você provavelmente vai querer ajustar está aqui — nenhum outro
arquivo precisa ser editado para mudar voz, estilo, duração ou canal.
"""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
IMAGES_LIB = ASSETS / "images"
MUSIC_LIB = ASSETS / "music"
FONTS = ASSETS / "fonts"
WORK = ROOT / "work"
OUTPUT = ROOT / "output"
LOGS = ROOT / "logs"
CREDS = ROOT / "credentials"
STATE_FILE = ROOT / "state.json"

for _p in (ASSETS, IMAGES_LIB, MUSIC_LIB, FONTS, WORK, OUTPUT, LOGS, CREDS):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# VÍDEO
# --------------------------------------------------------------------------
W, H = 1080, 1920          # vertical 9:16 (Short)
FPS = 30
TARGET_SECONDS = 30.0      # duração alvo da narração
MAX_SECONDS = 30.4         # acima disso, a locução é acelerada automaticamente
#                            (garante que o Short final fique em ~30s)
TRANSITION = 0.45          # crossfade entre imagens (s)
MIN_SHOTS = 5              # quantos quadros/imagens por vídeo

# --------------------------------------------------------------------------
# VOZ (edge-tts — gratuito, sem consumir créditos de geração)
# --------------------------------------------------------------------------
# Vozes pt-BR disponíveis: Antonio (masc.), Francisca (fem.).
# O tom agora é claro e energético, sem voz de terror.
VOICE = os.getenv("MYTHOS_VOICE", "pt-BR-AntonioNeural")
VOICE_PITCH = os.getenv("MYTHOS_PITCH", "+2Hz")
VOICE_RATE = os.getenv("MYTHOS_RATE", "+4%")

# --------------------------------------------------------------------------
# IDENTIDADE DO CANAL
# --------------------------------------------------------------------------
CHANNEL_NAME = os.getenv("MYTHOS_CHANNEL", "MITOS EM 30 SEGUNDOS")
HOOK_LABEL = os.getenv("MYTHOS_LABEL", "CURIOSIDADES DA MITOLOGIA")
CTA_TEXT = os.getenv("MYTHOS_CTA", "SIGA PARA MAIS MITOS")

# --------------------------------------------------------------------------
# ÁUDIO
# --------------------------------------------------------------------------
MUSIC_VOLUME = 0.25        # trilha limpa, abaixo da voz
VOICE_VOLUME = 1.0
MASTER_LUFS = -14.0        # padrão de loudness para plataformas

# --------------------------------------------------------------------------
# LLM (proxy embutido do Manus — OpenAI-compatible)
# --------------------------------------------------------------------------
LLM_MODEL = os.getenv("MYTHOS_MODEL", "gpt-5-mini")

# --------------------------------------------------------------------------
# YOUTUBE
# --------------------------------------------------------------------------
YOUTUBE_CATEGORY_ID = "24"          # 24 = Entertainment
YOUTUBE_PRIVACY = os.getenv("MYTHOS_PRIVACY", "public")   # public | unlisted | private
YOUTUBE_CLIENT_SECRET = CREDS / "client_secret.json"
YOUTUBE_TOKEN = CREDS / "token.json"
