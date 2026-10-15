# -*- coding: utf-8 -*-
"""Vuelca la API REST de Atlas Server (el servicio del PC que gobierna el HMB y
el SM-200) a un archivo de texto, y descarga su Swagger a un .json aparte.

Uso (desde cualquier carpeta, con Atlas Professional abierto):
    py explorar_epson.py            (localhost)
    py explorar_epson.py <host>
Solo hace GET: no cambia nada.
"""

import json
import sys
import os
import urllib.error
import urllib.request
from datetime import datetime

HOST_ATLAS     = "localhost"   # Atlas Server corre en el PC, no en la board
PUERTO_API     = 5000
TIMEOUT_S      = 10
MAX_CARACTERES = 200_000   # recorte por respuesta, por si alguna coleccion es enorme

# rutas fijas del documento "How to use RESTful API" + candidatas habituales
RUTAS = [
    "/api",
    "/api/jobs", "/api/jobstores", "/api/printqueues", "/api/printqueues/default",
    "/api/printoperations", "/api/bitmaps", "/api/separatedimages",
    "/api/HeadManagerBoards", "/api/EventManagerBoards", "/api/flowcontrollers",
    "/api/licences", "/api/Temperatures/HeadManagerBoards", "/api/version",
]
RUTA_SWAGGER = "/swagger/AtlasServer/swagger.json"


def obtener(url):
    peticion = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_S) as r:
            cuerpo = r.read().decode("utf-8", errors="replace")
            return r.status, r.headers.get("Content-Type", ""), cuerpo
    except urllib.error.HTTPError as e:
        return e.code, "", e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        return None, "", str(e)


def formatear(cuerpo):
    try:
        return json.dumps(json.loads(cuerpo), indent=2, ensure_ascii=False)
    except ValueError:
        return cuerpo


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST_ATLAS
    base = f"http://{host}:{PUERTO_API}"
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          f"epson_api_{datetime.now():%y%m%d_%H%M%S}.txt")
    # Swagger: la definicion completa de la API, a un archivo aparte
    estado, _tipo, cuerpo = obtener(base + RUTA_SWAGGER)
    if estado == 200:
        ruta_json = salida.replace(".txt", "_swagger.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            f.write(formatear(cuerpo))
        print(f"Swagger guardado en: {ruta_json}")
    else:
        print(f"Swagger no disponible ({estado}): {cuerpo[:100]}")

    with open(salida, "w", encoding="utf-8") as f:
        f.write(f"Atlas Server {base}  {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        for ruta in RUTAS:
            estado, tipo, cuerpo = obtener(base + ruta)
            f.write("=" * 78 + f"\nGET {ruta}  ->  {estado} {tipo}\n" + "=" * 78 + "\n")
            if estado is None:
                f.write(f"(sin respuesta: {cuerpo})\n\n")
                print(f"{ruta:32} sin respuesta: {cuerpo}")
                continue
            texto = formatear(cuerpo)
            f.write(texto[:MAX_CARACTERES] + ("\n... (recortado)\n" if len(texto) > MAX_CARACTERES else "\n") + "\n")
            print(f"{ruta:32} {estado}  {len(cuerpo)} bytes")
    print(f"\nVolcado en: {salida}")


if __name__ == "__main__":
    main()
