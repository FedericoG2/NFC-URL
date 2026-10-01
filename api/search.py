import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


def buscar_lugares(nombre, calle):
    nombre = str(nombre or "").strip()
    calle = str(calle or "").strip()
    if len(nombre) < 2:
        return 400, {"error": "Escribí el nombre del lugar."}

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return 500, {
            "error": "Falta configurar GOOGLE_MAPS_API_KEY en las variables de entorno."
        }

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
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
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
        return error.code, {"error": message}
    except (urllib.error.URLError, TimeoutError):
        return 502, {"error": "No se pudo conectar con Google."}

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
                "url": "https://search.google.com/local/writereview?placeid=" + place_id,
            }
        )
    return 200, {"lugares": lugares}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
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
