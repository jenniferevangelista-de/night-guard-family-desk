"""Tiny local proxy that turns off Gemma's thinking mode for the agent.

Agent-Native talks to Ollama through the AI SDK, which does not forward
Ollama's `think` flag. On a CPU, thinking makes every turn about 5x slower,
so this proxy adds `"think": false` to /api/chat requests and passes
everything else through unchanged (streaming included).

Usage: python3 scripts/ollama-no-think.py   # listens on 127.0.0.1:11435
Then set OLLAMA_BASE_URL=http://127.0.0.1:11435 in .env.
"""

import http.client
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = os.environ.get("OLLAMA_UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("OLLAMA_UPSTREAM_PORT", "11434"))
LISTEN_PORT = int(os.environ.get("PROXY_PORT", "11435"))
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "content-length", "host"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if self.path.startswith("/api/chat") and body:
            try:
                payload = json.loads(body)
                payload["think"] = False
                body = json.dumps(payload).encode()
            except ValueError:
                pass
        upstream = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=900)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
        headers["Content-Length"] = str(len(body))
        upstream.request(self.command, self.path, body=body, headers=headers)
        resp = upstream.getresponse()
        self.send_response(resp.status)
        for key, value in resp.getheaders():
            if key.lower() not in HOP_HEADERS:
                self.send_header(key, value)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        while True:
            chunk = resp.read1(65536)
            if not chunk:
                break
            self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        upstream.close()

    do_GET = do_POST = do_HEAD = do_DELETE = _forward

    def log_message(self, *_args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Proxy).serve_forever()
