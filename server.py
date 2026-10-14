import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EMAIL = os.environ.get("EXAM_EMAIL", "24f3002937@ds.study.iitm.ac.in").strip().lower()

TOOL = {
    "name": "solve_challenge",
    "description": "Solves the exam challenge using the X-Exam-Challenge header.",
    "inputSchema": {"type": "object", "properties": {}},
}


def rpc_result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def rpc_error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle(msg, headers):
    method = msg.get("method")
    id_ = msg.get("id")
    if id_ is None:  # notification, e.g. notifications/initialized
        return None
    if method == "initialize":
        requested = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        return rpc_result(id_, {
            "protocolVersion": requested,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        })
    if method == "ping":
        return rpc_result(id_, {})
    if method == "tools/list":
        return rpc_result(id_, {"tools": [TOOL]})
    if method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return rpc_error(id_, -32602, f"Unknown tool: {name}")
        challenge = headers.get("X-Exam-Challenge", "")
        digest = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
        return rpc_result(id_, {"content": [{"type": "text", "text": digest}], "isError": False})
    return rpc_error(id_, -32601, f"Method not found: {method}")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", "*")
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        if self.path in ("/", "/health"):
            self._send(200, {"status": "ok"})
        else:
            self._send(405)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw)
        except Exception:
            return self._send(400, rpc_error(None, -32700, "Parse error"))
        if isinstance(body, list):
            out = [r for r in (handle(m, self.headers) for m in body) if r is not None]
            return self._send(200, out) if out else self._send(202)
        resp = handle(body, self.headers)
        if resp is None:
            return self._send(202)
        self._send(200, resp)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
