"""
Autorizacao OAuth do YouTube — roda UMA vez.

Como usar:
  1. Baixe o client_secret.json do Google Cloud Console (veja o GUIA) e coloque
     em credentials/client_secret.json
  2. Rode:  python3 auth_setup.py
  3. Ele imprime um link. Abra no seu navegador, autorize com a conta do canal.
  4. O navegador vai tentar abrir "http://localhost:8080/?code=..." e mostrar
     erro de conexao. Isso e esperado: copie a URL COMPLETA da barra de
     endereco e cole aqui no terminal.
  5. Pronto: credentials/token.json e criado e nunca mais precisa repetir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config import YOUTUBE_CLIENT_SECRET, YOUTUBE_TOKEN

REDIRECT = "http://localhost:8080/"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not YOUTUBE_CLIENT_SECRET.exists():
        print(f"ERRO: nao encontrei {YOUTUBE_CLIENT_SECRET}")
        print("Baixe o JSON do Google Cloud Console e salve nesse caminho.")
        return 1

    if YOUTUBE_TOKEN.exists():
        ans = input("token.json ja existe. Sobrescrever? [s/N] ").strip().lower()
        if ans != "s":
            print("Nada foi alterado.")
            return 0

    flow = InstalledAppFlow.from_client_secrets_file(
        str(YOUTUBE_CLIENT_SECRET), SCOPES, redirect_uri=REDIRECT)

    url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true")

    print("\n" + "=" * 78)
    print("1) Abra este link no navegador e autorize com a conta do canal:\n")
    print(url)
    print("\n2) O navegador vai cair em http://localhost:8080/?code=... e dar ERRO.")
    print("   Copie a URL INTEIRA da barra de endereco e cole abaixo.")
    print("=" * 78 + "\n")

    pasted = input("Cole a URL completa aqui: ").strip()
    code = None
    if "code=" in pasted:
        code = parse_qs(urlparse(pasted).query).get("code", [None])[0]
    if not code:
        code = pasted.strip()

    flow.fetch_token(code=code)
    creds = flow.credentials
    YOUTUBE_TOKEN.write_text(creds.to_json())

    # valida de verdade: consulta o canal autorizado
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        info = yt.channels().list(part="snippet", mine=True).execute()
        items = info.get("items", [])
        name = items[0]["snippet"]["title"] if items else "(canal nao retornado)"
        cid = items[0]["id"] if items else "?"
        print(f"\nOK! token.json salvo. Canal autorizado: {name} ({cid})")
    except Exception as e:
        print(f"\ntoken.json salvo, mas a validacao falhou: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())