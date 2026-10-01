import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from api.search import buscar_lugares

HOST = "127.0.0.1"
PORT = 8765
PUBLIC = str(Path(__file__).resolve().parent / "public")


class FormHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC, **kwargs)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/search":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.responder(400, {"error": "La búsqueda no es válida."})
            return

        status, body = buscar_lugares(payload.get("nombre"), payload.get("calle"))
        self.responder(status, body)

    def responder(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"Formulario disponible en http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), FormHandler).serve_forever()
