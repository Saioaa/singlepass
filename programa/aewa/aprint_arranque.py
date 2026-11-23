# -*- coding: utf-8 -*-
"""Arranque de APRINT desde la app (solo Windows).

La app conecta con APRINT por TCP (aprint_comunicacion). Si no responde,
Aprint.conectar usa este modulo: si APRINT no esta abierto lo abre (minimizado
u oculto segun config.MODO_ARRANQUE_APRINT) y espera a que escuche.

  buscar_ejecutable()   ruta de APRINT (config.RUTA_APRINT o busqueda)
  en_ejecucion(ruta)    True si hay un proceso con ese ejecutable
  abrir(ruta, modo)     lanza APRINT sin bloquear y sin consola

Opciones de linea de comandos de APRINT (guia APRINT-Remote 2.5):
  -hidden  sin ventana; se cierra con QuitAPRINT ("gq" por el protocolo remoto)
"""

import subprocess
import sys
from pathlib import Path

from programa import config

ES_WINDOWS = sys.platform == "win32"

# ===== BUSQUEDA DEL EJECUTABLE =====
PATRON_EJECUTABLE = "APRINT*.exe"
NOMBRE_PREFERIDO = "aprint.exe"
# ejecutables de la instalacion que no son APRINT (desinstalador, utilidades remotas)
EXCLUIR_SI_CONTIENE = ("remote", "unins", "setup", "update")
PROFUNDIDAD_BUSQUEDA = 4          # carpeta/APRINT.exe ... carpeta/AEWA/APRINT/bin/APRINT.exe

# ===== MODOS DE ARRANQUE =====
MODO_MINIMIZADO = "minimizado"
MODO_OCULTO = "oculto"
OPCION_OCULTO = "-hidden"
SW_SHOWMINNOACTIVE = 7            # minimizada y sin quitar el foco a la app

# ===== PROCESOS =====
COMANDO_TAREAS = "tasklist"
TIMEOUT_TAREAS_S = 10.0
CODIFICACION_CONSOLA = "mbcs" if ES_WINDOWS else "utf-8"


def _sin_consola():
    """Flags de subprocess para no abrir ventana de consola (con --windowed)."""
    return subprocess.CREATE_NO_WINDOW if ES_WINDOWS else 0


def _valido(ruta):
    nombre = ruta.name.lower()
    return not any(texto in nombre for texto in EXCLUIR_SI_CONTIENE)


def buscar_ejecutable():
    """Ruta de APRINT o None. Usa config.RUTA_APRINT si esta puesta."""
    if config.RUTA_APRINT is not None:
        ruta = Path(config.RUTA_APRINT)
        return ruta if ruta.is_file() else None
    candidatos = []
    for carpeta in config.CARPETAS_BUSQUEDA_APRINT:
        if not carpeta.is_dir():
            continue
        for nivel in range(PROFUNDIDAD_BUSQUEDA):
            patron = "/".join(["*"] * nivel + [PATRON_EJECUTABLE])
            try:
                candidatos += [r for r in carpeta.glob(patron) if r.is_file() and _valido(r)]
            except OSError:      # carpetas sin permiso de lectura
                continue
    if not candidatos:
        return None
    # primero APRINT.exe exacto; si hay varias versiones, la mas reciente
    candidatos.sort(key=lambda r: (r.name.lower() == NOMBRE_PREFERIDO, r.stat().st_mtime),
                    reverse=True)
    return candidatos[0]


def en_ejecucion(ruta):
    """True si hay un proceso con el nombre de ese ejecutable (None si no se sabe)."""
    if not ES_WINDOWS:
        return None
    try:
        salida = subprocess.run(
            [COMANDO_TAREAS, "/FI", f"IMAGENAME eq {ruta.name}", "/NH"],
            capture_output=True, timeout=TIMEOUT_TAREAS_S, creationflags=_sin_consola())
    except (OSError, subprocess.SubprocessError):
        return None
    return ruta.name.lower() in salida.stdout.decode(CODIFICACION_CONSOLA, "replace").lower()


def abrir(ruta, modo=None):
    """Lanza APRINT y vuelve enseguida (no espera a que arranque). OSError si falla."""
    modo = modo or config.MODO_ARRANQUE_APRINT
    argumentos = [str(ruta)]
    opciones = {"cwd": str(ruta.parent)}   # APRINT busca sus ficheros junto al .exe
    if modo == MODO_OCULTO:
        argumentos.append(OPCION_OCULTO)
    elif ES_WINDOWS:
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = SW_SHOWMINNOACTIVE
        opciones["startupinfo"] = info
    if ES_WINDOWS:
        # que APRINT no se cierre con la app ni herede su consola
        opciones["creationflags"] = subprocess.DETACHED_PROCESS | \
            subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(argumentos, close_fds=True, **opciones)
