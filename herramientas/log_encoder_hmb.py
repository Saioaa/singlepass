# -*- coding: utf-8 -*-
"""Registra la cola de impresion del HMB (encoder, PD, disparos) durante una pasada.

Muestrea /api/headManagerBoards/0/printQueues/0 del HMB y guarda una linea por
muestra en Descargas. Al terminar calcula en que posicion de encoder quedo
registrado el PD (reconstruido desde el primer disparo) y lo imprime.

Uso:  py log_encoder_hmb.py [segundos]
      Lanzarlo ANTES de pulsar Start en la app. Por defecto registra 30 s.
      Ctrl+C corta el registro y escribe el resumen igualmente.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ===== HMB =====
IP_HMB       = "192.168.79.134"
PUERTO_HMB   = 8080
INDICE_HMB   = 0
INDICE_COLA  = 0
RUTA_COLA    = f"/api/headManagerBoards/{INDICE_HMB}/printQueues/{INDICE_COLA}"
TIMEOUT_S    = 2

# ===== MUESTREO =====
SEGUNDOS_POR_DEFECTO = 30
PERIODO_S            = 0.2

# ===== GEOMETRIA (para el resumen) =====
PASO_PIXEL_MM = 25.4 / 1200       # 21.17 um: un disparo por linea de 1200 dpi

# ===== SALIDA =====
CARPETA_SALIDA  = Path.home() / "Downloads"
PREFIJO_FICHERO = "pq0_log"
FORMATO_HORA    = "%H:%M:%S.%f"


def leer_cola():
    """Devuelve el JSON de la cola o None si el HMB no responde."""
    url = f"http://{IP_HMB}:{PUERTO_HMB}{RUTA_COLA}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[HMB] Sin respuesta: {e}")
        return None


def muestra(cola):
    """Extrae los campos de interes de una lectura de la cola."""
    encoder = cola.get("encoder", {})
    diag = encoder.get("diagnostics", {})
    return {
        "estado":   cola.get("state", {}).get("name", "?"),
        "pdOffset": encoder.get("pdOffset", 0),
        "paso_mm":  encoder.get("positionEventPitchInMillimetres", 0.0),
        "pdCount":  diag.get("pdCount", 0),
        "pos":      diag.get("position", 0),
        "fire":     diag.get("fireRequests", 0),
        "ops":      len(cola.get("printOperations", [])),
    }


def linea_registro(m):
    hora = datetime.now().strftime(FORMATO_HORA)[:-3]
    return (f"{hora} state={m['estado']} pdOffset={m['pdOffset']} "
            f"pdCount={m['pdCount']} pos={m['pos']} fire={m['fire']} ops={m['ops']}")


def resumen(muestras):
    """Reconstruye la posicion del PD y la longitud de la pasada."""
    con_disparo = [m for m in muestras if m["fire"] > 0]
    if not con_disparo:
        print("Resumen: no se ha registrado ningun disparo (no hubo PD o no hubo pasada).")
        return
    primera = con_disparo[0]
    ultima = con_disparo[-1]
    paso_mm = primera["paso_mm"] or max(m["paso_mm"] for m in muestras)
    eventos_por_disparo = PASO_PIXEL_MM / paso_mm
    pos_primer_disparo = primera["pos"] - primera["fire"] * eventos_por_disparo
    pos_pd = pos_primer_disparo - primera["pdOffset"]
    print("Resumen:")
    print(f"  paso de encoder      : {paso_mm * 1000:.2f} um")
    print(f"  pdOffset             : {primera['pdOffset']} eventos = {primera['pdOffset'] * paso_mm:.2f} mm")
    print(f"  PD registrado en pos : {pos_pd:.0f} eventos = {pos_pd * paso_mm:.1f} mm "
          f"(0 = mesa parada al dar el PULSE)")
    print(f"  recorrido con cola   : {ultima['pos']} eventos = {ultima['pos'] * paso_mm:.1f} mm")
    print(f"  disparos             : {ultima['fire']} = {ultima['fire'] * PASO_PIXEL_MM:.1f} mm de pagina")


def main():
    segundos = float(sys.argv[1]) if len(sys.argv) > 1 else SEGUNDOS_POR_DEFECTO
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    fichero = CARPETA_SALIDA / f"{PREFIJO_FICHERO}_{datetime.now():%y%m%d_%H%M%S}.txt"
    print(f"Registrando {segundos:.0f} s en {fichero}  (Ctrl+C para cortar)")

    muestras = []
    fin = time.time() + segundos
    with open(fichero, "w", encoding="utf-8") as salida:
        try:
            while time.time() < fin:
                cola = leer_cola()
                if cola is not None:
                    m = muestra(cola)
                    muestras.append(m)
                    linea = linea_registro(m)
                    salida.write(linea + "\n")
                    salida.flush()
                    print(linea)
                time.sleep(PERIODO_S)
        except KeyboardInterrupt:
            print("Registro cortado por el usuario.")

    resumen(muestras)
    print(f"Fichero: {fichero}")


if __name__ == "__main__":
    main()
