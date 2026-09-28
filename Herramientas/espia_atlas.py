# -*- coding: utf-8 -*-
"""Espia entre Atlas Professional y Atlas Server: registra cada peticion HTTP.

Escucha en PUERTO_ESCUCHA, reenvia todo a Atlas Server (PUERTO_ATLAS) y
escribe en pantalla y en espia_atlas_<fecha>.log cada peticion con sus
cabeceras y su cuerpo (las partes multipart en claro, los binarios recortados).

Uso:
  1. py herramientas\\espia_atlas.py
  2. En Atlas Professional: Server connection -> localhost, puerto 5001
  3. Crear e imprimir un trabajo desde Atlas Professional
  4. Ctrl+C y enviar el .log

Solo reenvia: no cambia nada de lo que Atlas Professional pide.
"""

import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO_ESCUCHA   = 5001
HOST_ATLAS       = "localhost"
PUERTO_ATLAS     = 5000
TIMEOUT_S        = 120          # los long poll pueden tardar
MAX_TEXTO        = 4000         # caracteres de cuerpo textual que se registran
MAX_BINARIO      = 200          # bytes de cada parte binaria que se registran
CABECERAS_SALTO  = ("host", "content-length", "transfer-encoding", "connection")
RUTAS_SILENCIO   = ("longpoll=",)   # sondeos: se anotan en una linea, sin cuerpo

archivo_log = None


def escribir(texto):
    print(texto)
    archivo_log.write(texto + "\n")
    archivo_log.flush()


def resumen_cuerpo(cuerpo, tipo):
    """Cuerpo legible: multipart por partes, texto entero (recortado), binario en hex."""
    if not cuerpo:
        return "(sin cuerpo)"
    m = re.search(r'boundary="?([^";]+)"?', tipo or "")
    if m:
        frontera = m.group(1).encode()
        salida = [f"multipart, frontera={m.group(1)}, {len(cuerpo)} bytes"]
        for parte in cuerpo.split(b"--" + frontera)[1:]:
            if parte.strip() in (b"", b"--"):
                continue
            cab, _, datos = parte.partition(b"\r\n\r\n")
            datos = datos.rstrip(b"\r\n")
            cab_txt = cab.decode("utf-8", errors="replace").strip()
            try:
                if len(datos) > MAX_TEXTO or b"\x00" in datos[:512]:
                    raise UnicodeDecodeError("utf-8", b"", 0, 1, "binario")
                cuerpo_txt = datos.decode("utf-8")
            except UnicodeDecodeError:
                cuerpo_txt = f"<{len(datos)} bytes> {datos[:MAX_BINARIO]!r}"
            salida.append(f"  --- parte ---\n  {cab_txt}\n  {cuerpo_txt[:MAX_TEXTO]}")
        return "\n".join(salida)
    try:
        return cuerpo.decode("utf-8")[:MAX_TEXTO]
    except UnicodeDecodeError:
        return f"<{len(cuerpo)} bytes binarios> {cuerpo[:MAX_BINARIO]!r}"


class Espia(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        pass

    def _reenviar(self):
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(longitud) if longitud else None
        silencioso = any(s in self.path for s in RUTAS_SILENCIO)
        marca = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if silencioso:
            escribir(f"{marca} {self.command} {self.path}  (sondeo)")
        else:
            escribir("=" * 78 + f"\n{marca} {self.command} {self.path}")
            for k, v in self.headers.items():
                if k.lower() not in CABECERAS_SALTO:
                    escribir(f"  {k}: {v}")
            escribir(resumen_cuerpo(cuerpo, self.headers.get("Content-Type")))

        cabeceras = {k: v for k, v in self.headers.items() if k.lower() not in CABECERAS_SALTO}
        req = urllib.request.Request(f"http://{HOST_ATLAS}:{PUERTO_ATLAS}{self.path}",
                                     data=cuerpo, method=self.command, headers=cabeceras)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                codigo, resp_cab, resp_cuerpo = r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            codigo, resp_cab, resp_cuerpo = e.code, e.headers, e.read()
        except (urllib.error.URLError, OSError) as e:
            escribir(f"  !! Atlas Server no responde: {e}")
            self.send_response(502)
            self.end_headers()
            return

        if not silencioso:
            escribir(f"  -> {codigo}\n{resumen_cuerpo(resp_cuerpo, resp_cab.get('Content-Type'))}")
        self.send_response(codigo)
        for k, v in resp_cab.items():
            if k.lower() not in CABECERAS_SALTO:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(resp_cuerpo)))
        self.end_headers()
        self.wfile.write(resp_cuerpo)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _reenviar


def main():
    global archivo_log
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        f"espia_atlas_{datetime.now():%y%m%d_%H%M%S}.log")
    archivo_log = open(ruta, "w", encoding="utf-8")
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO_ESCUCHA
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Espia)
    print(f"Espia en http://localhost:{puerto} -> Atlas Server {HOST_ATLAS}:{PUERTO_ATLAS}")
    print(f"Registro: {ruta}\nApunta Atlas Professional a localhost:{puerto}. Ctrl+C para terminar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        archivo_log.close()


if __name__ == "__main__":
    main()
