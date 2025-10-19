#!/usr/bin/env python3
"""Read-only ingestion of Gmail and Google Drive content into Mindstack.

Features:
- Gmail: list recent messages, pull text/plain or text/html (stripped) bodies, record metadata.
- Drive: list recent files, export Google Docs/Sheets to text/CSV; metadata-only for other mime types.
- Deduplicates via (profile, item_id, sha256).

Requires:
- OAuth client + refresh token generated via Google Workspace MCP (`run_google_mcp.sh`).
- Tokens stored under ~/.config/mindstack/google/<profile>/tokens.json (default).

Usage examples:
  ./scripts/codex/ingest_google_workspace.py --service gmail --dry-run
  ./scripts/codex/ingest_google_workspace.py --service drive --max-results 25
  ./scripts/codex/ingest_google_workspace.py --service both --since 2025-10-01
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from codex_vector.client import CodexVectorClient  # type: ignore  # noqa: E402

DEFAULT_PROFILE = "primary"
GMAIL_COLLECTION_TEMPLATE = "gx_gmail_{profile}"
DRIVE_COLLECTION_TEMPLATE = "gx_drive_{profile}"
CHUNK_SIZE = 1800
USER_AGENT = "Mindstack-Google-Ingest/1.0"

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

ALLOWED_GMAIL_FIELDS = "id,threadId,labelIds,internalDate,payload(parts,body,data,mimeType,filename),snippet"
ALLOWED_DRIVE_FIELDS = (
    "files(id,name,mimeType,modifiedTime,owners(displayName,emailAddress),"
    "parents,trashed,spaces,webViewLink,iconLink,size),nextPageToken"
)
READ_ONLY_SCOPES = {
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
}


class OAuthSession:
    """Minimal OAuth helper using stored Google tokens."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.token_path = config_dir / "tokens.json"
        self.client_secret_path = config_dir / "client_secret.json"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._token = self._load_token()

    def _load_token(self) -> dict:
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"Token file not found at {self.token_path}. Run the Google MCP auth flow first."
            )
        raw = json.loads(self.token_path.read_text())
        # Token file may be list with versioning; normalise to dict.
        if isinstance(raw, list):
            raw = raw[-1]
        return raw

    def _save_token(self, data: dict) -> None:
        tmp = self.token_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.token_path)

    def _client_credentials(self) -> Tuple[str, str]:
        if "client_id" in self._token and "client_secret" in self._token:
            return self._token["client_id"], self._token["client_secret"]
        if not self.client_secret_path.exists():
            raise FileNotFoundError(
                f"Client secret not found at {self.client_secret_path}. Set GOOGLE_OAUTH_CREDENTIALS or copy file."
            )
        secret = json.loads(self.client_secret_path.read_text())
        if "installed" in secret:
            data = secret["installed"]
        elif "web" in secret:
            data = secret["web"]
        else:
            data = secret
        return data["client_id"], data["client_secret"]

    def _token_expired(self) -> bool:
        expiry = self._token.get("expiry_date")
        if not expiry:
            return True
        try:
            expiry_ts = int(expiry) / 1000 if len(str(expiry)) > 10 else int(expiry)
        except ValueError:
            return True
        return dt.datetime.utcnow().timestamp() > (expiry_ts - 60)

    def ensure_token(self) -> str:
        if not self._token.get("access_token") or self._token_expired():
            client_id, client_secret = self._client_credentials()
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self._token.get("refresh_token"),
                "grant_type": "refresh_token",
            }
            resp = self.session.post(TOKEN_ENDPOINT, data=data, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            self._token.update(payload)
            if "expires_in" in payload:
                expiry = (dt.datetime.utcnow() + dt.timedelta(seconds=int(payload["expires_in"]))).timestamp()
                self._token["expiry_date"] = int(expiry * 1000)
            self._save_token(self._token)
        return self._token["access_token"]

    def get(self, url: str, **kwargs) -> requests.Response:
        token = self.ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        resp = self.session.get(url, headers=headers, timeout=kwargs.pop("timeout", 15), **kwargs)
        if resp.status_code == 401:
            # Retry once after refresh
            self._token["expiry_date"] = 0
            token = self.ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = self.session.get(url, headers=headers, timeout=kwargs.pop("timeout", 15), **kwargs)
        resp.raise_for_status()
        return resp


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    text = text.strip()
    if not text:
        return []
    segments = []
    start = 0
    while start < len(text):
        segments.append(text[start : start + chunk_size])
        start += chunk_size
    return segments


def clean_html(value: str) -> str:
    stripped = html.unescape(value)
    stripped = stripped.replace("<br>", "\n").replace("<br />", "\n").replace("<p>", "\n")
    return " ".join(strip_tags(stripped).split())


def strip_tags(value: str) -> str:
    output = []
    in_tag = False
    for char in value:
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if not in_tag:
            output.append(char)
    return "".join(output)


def decode_body(part: dict) -> str:
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
    if part.get("mimeType", "").startswith("text/html"):
        return clean_html(decoded)
    return decoded


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_collection(client: CodexVectorClient, name: str) -> None:
    try:
        client.ensure_collection(name)
    except Exception:
        try:
            client.create_collection(name)
        except Exception:
            pass


def upsert_chunks(
    client: CodexVectorClient,
    collection: str,
    chunks: Iterable[str],
    *,
    base_metadata: dict,
    dry_run: bool,
) -> int:
    segments = [chunk for chunk in chunks if chunk.strip()]
    if not segments:
        return 0
    metadata_items = []
    docs = []
    for idx, chunk in enumerate(segments):
        doc_id = sha256_text(f"{base_metadata['item_id']}:{idx}:{chunk}")
        docs.append(chunk)
        metadata = dict(base_metadata)
        metadata.update({
            "chunk_id": idx,
            "doc_id": doc_id,
            "sha256": sha256_text(chunk),
        })
        metadata_items.append(metadata)
    if dry_run:
        return len(docs)
    ensure_collection(client, collection)
    client.upsert(collection, docs, metadata_items=metadata_items)
    return len(docs)


def gmail_list_messages(oauth: OAuthSession, max_results: int, newer_than: Optional[str]) -> List[dict]:
    params = {
        "maxResults": max_results,
        "q": "label:inbox"
    }
    if newer_than:
        try:
            dt.datetime.strptime(newer_than, "%Y-%m-%d")
            params["q"] += f" after:{newer_than}"
        except ValueError:
            pass
    resp = oauth.get(f"{GMAIL_BASE}/users/me/messages", params=params)
    data = resp.json()
    return data.get("messages", [])


def gmail_fetch_message(oauth: OAuthSession, message_id: str) -> dict:
    params = {"format": "full", "fields": ALLOWED_GMAIL_FIELDS}
    resp = oauth.get(f"{GMAIL_BASE}/users/me/messages/{message_id}", params=params)
    return resp.json()


def iter_payload_text(payload: dict) -> List[str]:
    parts = []
    if payload.get("mimeType", "").startswith("text/"):
        parts.append(payload)
    for part in payload.get("parts", []) or []:
        parts.extend(iter_payload_text(part))
    return parts


def ingest_gmail(client: CodexVectorClient, oauth: OAuthSession, collection: str, max_results: int, since: Optional[str], dry_run: bool) -> int:
    messages = gmail_list_messages(oauth, max_results, since)
    total_chunks = 0
    for message in messages:
        msg = gmail_fetch_message(oauth, message["id"])
        payload = msg.get("payload", {})
        text_parts = iter_payload_text(payload)
        text_content = "\n".join(decode_body(part) for part in text_parts)
        if not text_content.strip():
            continue
        metadata = {
            "source": "gmail",
            "profile": oauth.config_dir.name,
            "item_id": msg["id"],
            "thread_id": msg.get("threadId"),
            "labels": msg.get("labelIds", []),
            "mime_type": payload.get("mimeType"),
            "snippet": msg.get("snippet"),
            "url": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
        }
        total_chunks += upsert_chunks(client, collection, chunk_text(text_content), base_metadata=metadata, dry_run=dry_run)
    return total_chunks


def drive_list_files(oauth: OAuthSession, max_results: int, since: Optional[str]) -> List[dict]:
    params = {
        "pageSize": max_results,
        "orderBy": "modifiedTime desc",
        "fields": ALLOWED_DRIVE_FIELDS
    }
    q_filters = ["trashed = false"]
    if since:
        q_filters.append(f"modifiedTime > '{since}T00:00:00'" )
    params["q"] = " and ".join(q_filters)
    resp = oauth.get(f"{DRIVE_BASE}/files", params=params)
    return resp.json().get("files", [])


def drive_export_file(oauth: OAuthSession, file_id: str, mime_type: str) -> Optional[str]:
    if mime_type == "application/vnd.google-apps.document":
        export_type = "text/plain"
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        export_type = "text/csv"
    else:
        return None
    resp = oauth.get(f"{DRIVE_BASE}/files/{file_id}/export", params={"mimeType": export_type})
    return resp.text


def ingest_drive(client: CodexVectorClient, oauth: OAuthSession, collection: str, max_results: int, since: Optional[str], dry_run: bool) -> int:
    files = drive_list_files(oauth, max_results, since)
    total_chunks = 0
    for item in files:
        text = drive_export_file(oauth, item["id"], item.get("mimeType", ""))
        if not text:
            continue
        metadata = {
            "source": "drive",
            "profile": oauth.config_dir.name,
            "item_id": item["id"],
            "title": item.get("name"),
            "mime_type": item.get("mimeType"),
            "modified": item.get("modifiedTime"),
            "owners": [owner.get("emailAddress") for owner in item.get("owners", []) if owner.get("emailAddress")],
            "url": item.get("webViewLink"),
        }
        total_chunks += upsert_chunks(client, collection, chunk_text(text), base_metadata=metadata, dry_run=dry_run)
    return total_chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Gmail and Drive data (read-only)")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Profile name (matches Google config directory)")
    parser.add_argument("--service", choices=["gmail", "drive", "both"], default="gmail")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum items per service fetch")
    parser.add_argument("--since", help="Optional date filter (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Qdrant; print summary only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = args.profile
    config_dir = Path(os.environ.get("GOOGLE_CONFIG_DIR", Path.home() / ".config" / "mindstack" / "google" / profile))
    oauth = OAuthSession(config_dir)

    client = CodexVectorClient()

    total_chunks = 0
    services = ["gmail", "drive"] if args.service == "both" else [args.service]

    if "gmail" in services:
        collection = GMAIL_COLLECTION_TEMPLATE.format(profile=profile)
        chunks = ingest_gmail(client, oauth, collection, args.max_results, args.since, args.dry_run)
        print(f"[gmail] {'dry-run' if args.dry_run else 'ingested'} {chunks} chunks into {collection}")
        total_chunks += chunks

    if "drive" in services:
        collection = DRIVE_COLLECTION_TEMPLATE.format(profile=profile)
        chunks = ingest_drive(client, oauth, collection, args.max_results, args.since, args.dry_run)
        print(f"[drive] {'dry-run' if args.dry_run else 'ingested'} {chunks} chunks into {collection}")
        total_chunks += chunks

    if total_chunks == 0:
        print("No content processed.")


if __name__ == "__main__":
    main()
