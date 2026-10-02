# -*- coding: utf-8 -*-
"""Registro de la aplicacion en fichero: un archivo por dia.

Todo lo que el programa escribe por consola (print y tracebacks) se duplica en
<carpeta>/singlepass_AAAA-MM-DD.log con la hora delante de cada linea. No hace
falta tocar los modulos: siguen usando print(); la consola sigue viendose igual.

Uso (lo primero en main(), antes de crear nada):
    registro.iniciar(config.CARPETA_LOGS)
"""

import os
import sys
import traceback
from datetime import date, datetime

PREFIJO_FICHERO = "singlepass"
EXTENSION       = ".log"
FORMATO_FECHA   = "%Y-%m-%d"
FORMATO_HORA    = "%H:%M:%S.%f"
DECIMALES_HORA  = 3            # milisegundos
CODIFICACION    = "utf-8"
MARCA_ARRANQUE  = "===== arranque ====="
MARCA_CIERRE    = "===== cierre ====="


class _Duplicador:
    """Escribe en la consola original y en el fichero del dia (cambia de fichero
    sola a medianoche). Cada linea del fichero lleva la hora delante."""

    def __init__(self, consola, carpeta):
        self._consola = consola
        self._carpeta = carpeta
        self._fichero = None
        self._dia = None
        self._inicio_de_linea = True

    def _abrir_si_toca(self):
        hoy = date.today()
        if self._fichero is not None and self._dia == hoy:
            return
        if self._fichero is not None:
            self._fichero.close()
        nombre = f"{PREFIJO_FICHERO}_{hoy.strftime(FORMATO_FECHA)}{EXTENSION}"
        self._fichero = open(os.path.join(self._carpeta, nombre), "a", encoding=CODIFICACION)
        self._dia = hoy

    def write(self, texto):
        if self._consola is not None:
            self._consola.write(texto)
        if not texto:
            return
        self._abrir_si_toca()
        hora = datetime.now().strftime(FORMATO_HORA)[:-(6 - DECIMALES_HORA)]
        for trozo in texto.splitlines(keepends=True):
            if self._inicio_de_linea:
                self._fichero.write(f"{hora} ")
            self._fichero.write(trozo)
            self._inicio_de_linea = trozo.endswith("\n")
        self._fichero.flush()

    def flush(self):
        if self._consola is not None:
            self._consola.flush()
        if self._fichero is not None:
            self._fichero.flush()

    def cerrar(self):
        if self._fichero is not None:
            self._fichero.close()
            self._fichero = None


_duplicador = None


def iniciar(carpeta):
    """Desvia stdout y stderr al fichero del dia (ademas de la consola) y registra
    tambien las excepciones no capturadas. Devuelve la carpeta usada."""
    global _duplicador
    os.makedirs(carpeta, exist_ok=True)
    _duplicador = _Duplicador(sys.stdout, carpeta)
    sys.stdout = _duplicador
    sys.stderr = _duplicador   # tracebacks y avisos de Qt (qt.gui.imageio, etc.)

    def excepcion_sin_capturar(tipo, valor, pila):
        _duplicador.write("".join(traceback.format_exception(tipo, valor, pila)))

    sys.excepthook = excepcion_sin_capturar
    print(MARCA_ARRANQUE)
    return carpeta


def cerrar():
    if _duplicador is not None:
        print(MARCA_CIERRE)
        _duplicador.cerrar()
