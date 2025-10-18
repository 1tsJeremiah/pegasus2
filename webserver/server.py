#!/usr/bin/env python3
"""
Tiny, dependency-free web server for workspace previews.

Usage:
  python webserver/server.py            # binds 0.0.0.0:3000
  PORT=3010 python webserver/server.py  # override port via env var
  python webserver/server.py 8080       # or via CLI arg

Routes:
  GET /           - simple HTML landing page
  GET /health     - JSON health check {"status": "ok"}
  GET /env        - JSON subset of relevant environment variables

This is intended for environments (like cloud workspaces) that need
an HTTP process to attach a web preview panel.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict


def _get_port() -> int:
    # CLI arg takes precedence
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            pass
    # Then PORT env var
    try:
        port_env = os.environ.get("PORT")
        if port_env:
            return int(port_env)
    except ValueError:
        pass
    # Default
    return 3000


INDEX_HTML = b"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Workspace Web Preview</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #eaeaea; background: #1e1e1e; }
      .wrap { max-width: 880px; margin: 0 auto; }
      h1 { margin-top: 0; }
      code, pre { background: #2a2a2a; padding: 0.2rem 0.4rem; border-radius: 4px; }
      .card { background: #242424; border: 1px solid #333; border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }
      a { color: #7fd1ff; }
      .muted { color: #aaa; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
      @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class=\"wrap\">
      <h1>Workspace Web Preview</h1>
      <p>This tiny server is running. Use it to verify the web preview panel is connected.</p>

      <div class=\"grid\">
        <div class=\"card\">
          <h3>Endpoints</h3>
          <ul>
            <li><a href=\"/\">/</a> – this page</li>
            <li><a href=\"/health\">/health</a> – JSON health check</li>
            <li><a href=\"/env\">/env</a> – selected environment variables</li>
          </ul>
          <p class=\"muted\">Change the port with <code>PORT=3010</code> or <code>python webserver/server.py 3010</code></p>
        </div>
        <div class=\"card\">
          <h3>Tips</h3>
          <ul>
            <li>Bind to <code>0.0.0.0</code> so the preview can reach it.</li>
            <li>If the panel is blank, the port might be busy. Try <code>--port 3010</code>.</li>
          </ul>
        </div>
      </div>

      <p class=\"muted\">Server path: <code>webserver/server.py</code></p>
    </div>
  </body>
  </html>
"""


def _env_subset() -> Dict[str, str]:
    keys = [
        # vector backends
        "CODEX_VECTOR_BASE_URL",
        "CODEX_VECTOR_TENANT",
        "CODEX_VECTOR_DB",
        "CODEX_VECTOR_COLLECTION",
        "CODEX_VECTOR_BACKEND",
        # meili
        "CODEX_MEILI_URL",
        # profile
        "MINDSTACK_PROFILE",
        # generic
        "PORT",
    ]
    out: Dict[str, str] = {}
    for k in keys:
        v = os.environ.get(k)
        if v:
            out[k] = v
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "TinyWS/1.0"

    def _set_json(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def _set_html(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._set_html(HTTPStatus.OK)
            self.wfile.write(INDEX_HTML)
            return
        if path == "/health":
            self._set_json(HTTPStatus.OK)
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return
        if path == "/env":
            self._set_json(HTTPStatus.OK)
            self.wfile.write(json.dumps(_env_subset(), indent=2).encode("utf-8"))
            return

        self._set_json(HTTPStatus.NOT_FOUND)
        self.wfile.write(json.dumps({"error": "not found", "path": path}).encode("utf-8"))


def main() -> None:
    host = "0.0.0.0"
    port = _get_port()

    httpd = HTTPServer((host, port), Handler)

    def _shutdown(*_args) -> None:
        try:
            httpd.shutdown()
        except Exception:
            pass

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Print a single line so terminals show where to connect
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "localhost"
    print(f"Serving on http://{host}:{port} (host={hostname})")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

