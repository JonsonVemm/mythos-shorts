"""
Publicacao no YouTube (Shorts) via YouTube Data API v3.

Precisa de dois arquivos em credentials/:
  client_secret.json  -> baixado do Google Cloud Console (tipo "App para desktop")
  token.json          -> gerado uma unica vez por `python3 auth_setup.py`

Depois disso o refresh token vale indefinidamente e o upload roda sozinho.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import (CREDS, YOUTUBE_CATEGORY_ID, YOUTUBE_CLIENT_SECRET,
                    YOUTUBE_PRIVACY, YOUTUBE_TOKEN)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def _creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not YOUTUBE_TOKEN.exists():
        raise FileNotFoundError(
            "credentials/token.json nao encontrado. Rode: python3 auth_setup.py"
        )
    creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            YOUTUBE_TOKEN.write_text(creds.to_json())
        else:
            raise RuntimeError("Credenciais invalidas. Rode novamente: python3 auth_setup.py")
    return creds


def service():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_creds(), cache_discovery=False)


def channel_info() -> dict:
    yt = service()
    r = yt.channels().list(part="snippet,statistics", mine=True).execute()
    items = r.get("items", [])
    return items[0] if items else {}


def upload(video: Path, title: str, description: str, tags: list[str],
           privacy: str = None, made_for_kids: bool = False,
           publish_at: str | None = None) -> dict:
    """
    Sobe o Short. `publish_at` (ISO 8601 UTC, ex. "2026-10-01T18:00:00Z")
    agenda a publicacao — nesse caso o video entra como 'private' ate a hora.
    """
    from googleapiclient.http import MediaFileUpload

    video = Path(video)
    if not video.exists():
        raise FileNotFoundError(video)

    yt = service()
    privacy = privacy or YOUTUBE_PRIVACY
    status = {
        "privacyStatus": "private" if publish_at else privacy,
        "selfDeclaredMadeForKids": made_for_kids,
        "embeddable": True,
        "license": "youtube",
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": [t for t in tags if t][:35],
            "categoryId": YOUTUBE_CATEGORY_ID,
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": status,
    }

    media = MediaFileUpload(str(video), chunksize=1024 * 1024 * 8,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    resp = None
    while resp is None:
        status_progress, resp = req.next_chunk()
        if status_progress:
            print(f"   [upload] {int(status_progress.progress() * 100)}%")

    vid = resp["id"]
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}"}


def build_description(script: dict, image_credits: str, channel: str) -> str:
    tags_line = " ".join(
        "#" + t.replace(" ", "") for t in script.get("tags", [])[:10]
    )
    parts = [
        script.get("hook", ""),
        "",
        script.get("description", ""),
        "",
        f"Mitologia contada em 30 segundos. {channel}.",
    ]
    if image_credits:
        parts += ["", "Arte de dominio publico (Wikimedia Commons):", image_credits]
    parts += ["", f"#Shorts {tags_line}"]
    return "\n".join(parts)


if __name__ == "__main__":
    print(json.dumps(channel_info(), ensure_ascii=False)[:400])