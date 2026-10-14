# -*- coding: utf-8 -*-
"""Temperatura del cabezal a traves del Print Server (PMB).

Equivalente a aprint_cabezal.py de MBD-F-500, pero preguntando al PMB. Cada
PERIODO_LECTURA_MS pide al Print Controller el parametro de temperatura real
(config.PARAMETRO_TEMPERATURA_CABEZAL) y, menos a menudo, la consigna
(config.PARAMETRO_CONSIGNA_CABEZAL); las respuestas llegan por
ClientePMB.parametro_recibido y de ahi sale la senal lectura(real, consigna).

Solo pregunta mientras el PMB esta conectado (se conecta al entrar en la pagina
Print Server). Si no hay respuesta, la interfaz sigue mostrando "--".

PROVISIONAL: los nombres de los parametros y el formato del comando de lectura
estan en config.py y pmb.py y hay que confirmarlos con el manual del Print Server.
"""

import re

from PySide6.QtCore import QObject, QTimer, Signal

import config

PERIODO_LECTURA_MS = 2000       # temperatura real
LECTURAS_POR_CONSIGNA = 5       # la consigna se pide una de cada N lecturas
PATRON_NUMERO = re.compile(r"-?\d+(?:[.,]\d+)?")


class TemperaturaCabezal(QObject):

    lectura = Signal(object, object)   # (real ºC o None, consigna ºC o None)
    mensaje = Signal(str)

    def __init__(self, pmb, parent=None):
        super().__init__(parent)
        self.pmb = pmb
        self._real = None
        self._consigna = None
        self._contador = 0
        self._avisado_sin_conexion = False
        pmb.parametro_recibido.connect(self._parametro_recibido)
        pmb.conexion_perdida.connect(lambda _motivo: self._sin_dato())

        self._timer = QTimer(self)
        self._timer.setInterval(PERIODO_LECTURA_MS)
        self._timer.timeout.connect(self._pedir)
        self._timer.start()

    def cerrar(self):
        self._timer.stop()

    # ===== consigna =====
    def fijar_consigna(self, grados):
        if not self.pmb.conectado():
            self.mensaje.emit("[CABEZAL] PMB no conectado: consigna de temperatura no enviada")
            return
        self.pmb.escribir_parametro(config.PARAMETRO_CONSIGNA_CABEZAL, f"{grados:g}")
        self.mensaje.emit(f"[CABEZAL] Consigna de temperatura enviada: {grados:g} ºC")
        self._consigna = grados
        self.lectura.emit(self._real, self._consigna)

    # ===== lectura periodica =====
    def _pedir(self):
        if not self.pmb.conectado():
            self._sin_dato()
            return
        self._contador = (self._contador + 1) % LECTURAS_POR_CONSIGNA
        parametro = (config.PARAMETRO_CONSIGNA_CABEZAL if self._contador == 0
                     else config.PARAMETRO_TEMPERATURA_CABEZAL)
        self.pmb.leer_parametro(parametro)

    def _parametro_recibido(self, parametro, texto):
        valor = self._extraer_numero(texto)
        if valor is None:
            self.mensaje.emit(f"[CABEZAL] Respuesta no numerica a {parametro}: {texto}")
            return
        if parametro == config.PARAMETRO_TEMPERATURA_CABEZAL:
            self._real = valor
        elif parametro == config.PARAMETRO_CONSIGNA_CABEZAL:
            self._consigna = valor
        else:
            return   # otro parametro leido por otro modulo
        self.lectura.emit(self._real, self._consigna)

    def _sin_dato(self):
        if self._real is not None or self._consigna is not None:
            self._real = None
            self._consigna = None
            self.lectura.emit(None, None)

    @staticmethod
    def _extraer_numero(texto):
        encontrado = PATRON_NUMERO.search(texto or "")
        if encontrado is None:
            return None
        return float(encontrado.group(0).replace(",", "."))
