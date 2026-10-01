import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8765
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


class FormHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/Index.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/search":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "La búsqueda no es válida."})
            return

        nombre = str(payload.get("nombre", "")).strip()
        calle = str(payload.get("calle", "")).strip()
        if len(nombre) < 2:
            self.send_json(400, {"error": "Escribí el nombre del lugar."})
            return

        api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
        if not api_key:
            self.send_json(
                500,
                {
                    "error": (
                        "Falta configurar GOOGLE_MAPS_API_KEY en el servidor local. "
                        "La búsqueda real necesita una clave de Google con Places API (New)."
                    )
                },
            )
            return

        consulta = f"{nombre}, {calle}" if calle else nombre
        request_body = json.dumps(
            {
                "textQuery": consulta[:200],
                "languageCode": "es",
                "regionCode": "AR",
                "maxResultCount": 5,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            PLACES_URL,
            data=request_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": (
                    "places.id,places.displayName,places.formattedAddress"
                ),
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read()).get("error", {}).get("message", "")
            except (ValueError, json.JSONDecodeError):
                detail = ""
            message = detail or "Google rechazó la búsqueda. Revisá la API key."
            self.send_json(error.code, {"error": message})
            return
        except (urllib.error.URLError, TimeoutError):
            self.send_json(502, {"error": "No se pudo conectar con Google."})
            return

        lugares = []
        for place in body.get("places", []):
            place_id = place.get("id")
            if not place_id:
                continue
            lugares.append(
                {
                    "id": place_id,
                    "nombre": place.get("displayName", {}).get("text", "Sin nombre"),
                    "direccion": place.get("formattedAddress", ""),
                    "url": (
                        "https://search.google.com/local/writereview?placeid="
                        + place_id
                    ),
                }
            )

        self.send_json(200, {"lugares": lugares})

    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"Formulario disponible en http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), FormHandler).serve_forever()
