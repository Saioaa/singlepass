# -*- coding: utf-8 -*-
"""Envia un VPI a Atlas Server con la cola de impresion PARADA y registra por
que estados pasa el trabajo. Al final cancela y borra el trabajo y vuelve a
arrancar la cola. No dispara ninguna impresion.

Uso:  py probar_epson.py <ruta.vpi> [modo]
      modo por defecto: "1200dpi x 1200dpi 1bpp Black GL2"
Rutas y parametros tomados del Swagger de Atlas Server (AtlasServices 1.0.10).
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST_ATLAS   = "localhost"
PUERTO_API   = 5000
JOB_STORE    = "Vpi1"
MODO_DEFECTO = "1200dpi x 1200dpi 1bpp Black GL2"
NOMBRE_TRABAJO = "prueba singlepass"
MIME_VPI     = "application/x.gis.vpi"
MIME_JSON    = "application/json"
CAMPO_PROPIEDADES = "jobProperties"   # JSON con las propiedades del trabajo (el servidor lo exige)
FRONTERA     = "------singlepass------trabajo"
SEGUNDOS_OBSERVACION = 20
PERIODO_S    = 0.5
TIMEOUT_S    = 10
CODIGOS_OK   = (200, 201, 202)


def peticion(metodo, ruta, cuerpo=None, tipo=None):
    """Devuelve (codigo HTTP, respuesta decodificada como JSON si lo es)."""
    url = f"http://{HOST_ATLAS}:{PUERTO_API}{ruta}"
    cabeceras = {"Accept": "application/json"}
    if tipo:
        cabeceras["Content-Type"] = tipo
    if tipo and tipo.startswith("multipart/"):
        cabeceras["Accept"] = "multipart/form-data"   # como Atlas Professional
    req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            texto = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        return None, str(e)
    try:
        return r.status, json.loads(texto) if texto.strip() else ""
    except ValueError:
        return r.status, texto


def multipart_trabajo(ruta_archivo, mime, job_store, propiedades):
    """Cuerpo multipart tal como lo envia Atlas Professional (capturado con espia_atlas.py):
    primero los datos, en una parte llamada como el job store y con filename = nombre del
    trabajo; despues jobProperties (JSON) con filename=- . Sin filename Atlas ignora la parte."""
    with open(ruta_archivo, "rb") as f:
        datos = f.read()
    nombre = propiedades["Name"]
    parte_datos = ((f"--{FRONTERA}\r\n"
                    f"Content-Type: {mime}\r\n"
                    f'Content-Disposition: form-data; name={job_store}; filename="{nombre}"\r\n\r\n').encode()
                   + datos + b"\r\n")
    parte_props = ((f"--{FRONTERA}\r\n"
                    f"Content-Type: {MIME_JSON}; charset=utf-8\r\n"
                    f"Content-Disposition: form-data; name={CAMPO_PROPIEDADES}; filename=-\r\n\r\n").encode()
                   + json.dumps(propiedades).encode("utf-8") + b"\r\n")
    cuerpo = parte_datos + parte_props + f"--{FRONTERA}--\r\n".encode()
    return cuerpo, f'multipart/form-data; boundary="{FRONTERA}"'


def estado(objeto):
    if not isinstance(objeto, dict):
        return str(objeto)[:80]
    e = objeto.get("state", {})
    texto = str(e.get("name"))
    if e.get("isError"):
        texto += f" (error: {e.get('error')})"
    return texto


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    ruta_vpi = sys.argv[1]
    modo = sys.argv[2] if len(sys.argv) > 2 else MODO_DEFECTO
    cola = urllib.parse.quote(modo)

    codigo, hmbs = peticion("GET", "/api/HeadManagerBoards")
    if codigo is None:
        print("Atlas Server no responde:", hmbs)
        return
    print("HMB:", [(h.get("id"), estado(h)) for h in hmbs])
    codigo, _ = peticion("POST", f"/api/PrintQueues/{cola}/stop")
    print(f"cola '{modo}' parada -> {codigo}")

    propiedades = {"Name": NOMBRE_TRABAJO, "JobStoreId": JOB_STORE, "FrameStart": 0, "FrameCount": 1,
                   "JobMode": modo, "RecognitionId": None, "WidthInMillimetres": 0.0,
                   "HeightInMillimetres": 0.0, "Arguments": None}
    cuerpo, tipo = multipart_trabajo(ruta_vpi, MIME_VPI, JOB_STORE, propiedades)
    codigo, trabajo = peticion("POST", "/api/Jobs", cuerpo, tipo)
    print(f"POST /api/Jobs -> {codigo}")
    if codigo not in CODIGOS_OK:
        print(trabajo)
        peticion("POST", f"/api/PrintQueues/{cola}/start")
        return
    id_trabajo = trabajo["id"]
    print(f"trabajo {id_trabajo}: estado inicial {estado(trabajo)} | jobStoreId {trabajo.get('jobStoreId')} "
          f"| {trabajo.get('widthInMillimetres')} x {trabajo.get('heightInMillimetres')} mm")

    vistos = []
    t0 = time.time()
    while time.time() - t0 < SEGUNDOS_OBSERVACION:
        _c, t = peticion("GET", f"/api/Jobs/{id_trabajo}")
        _c, ops = peticion("GET", "/api/PrintOperations")
        if not isinstance(t, dict):
            print("respuesta inesperada:", t)
            break
        linea = (estado(t), t.get("jobStoreId"),
                 [(p.get("jobStoreId"), estado(p)) for p in t.get("progress", []) if isinstance(p, dict)],
                 [(o.get("id"), estado(o), o.get("startedPrintCount"), o.get("finishedPrintCount"))
                  for o in ops] if isinstance(ops, list) else ops)
        if not vistos or linea != vistos[-1]:
            vistos.append(linea)
            print(f"{time.time() - t0:5.1f}s  trabajo {linea[0]:<18} store {str(linea[1]):<12} "
                  f"progreso {linea[2]}  ops {linea[3]}")
        if t.get("state", {}).get("isTerminal"):
            break
        time.sleep(PERIODO_S)

    print("cancelar ->", peticion("POST", f"/api/Jobs/{id_trabajo}/Cancel")[0])
    time.sleep(1)
    print("borrar   ->", peticion("DELETE", f"/api/Jobs/{id_trabajo}")[0])
    print("cola en marcha ->", peticion("POST", f"/api/PrintQueues/{cola}/start")[0])


if __name__ == "__main__":
    main()
