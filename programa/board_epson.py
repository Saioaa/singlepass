# -*- coding: utf-8 -*-
"""Board SM-200 (cabezales Epson) via API REST de GIS. PENDIENTE de implementar.

Datos conocidos: HMB en 192.168.79.134 (modos, imagen, render), encoder en
192.168.79.1; ripea por su cuenta; print go y encoder le llegan por su propio
cableado (el pulso del M-Duino funciona con ella).

Por ahora cada metodo avisa de que esta pendiente, de modo que si en Programa
hay un SM-200 activo la pagina Print Server lo dice y la secuencia no arranca.
"""

from board import Board

HOST_HMB      = "192.168.79.134"
HOST_ENCODER  = "192.168.79.1"


class BoardEpson(Board):

    nombre = "EPSON"
    tipos_modulo = ("SM-200",)

    def __init__(self, host=HOST_HMB, parent=None):
        super().__init__(parent)
        self.host = host

    def _pendiente(self, accion):
        self.registrar(f"{accion}: comunicacion con el SM-200 pendiente de implementar")
        return False

    def conectar(self):
        return self._pendiente("conectar")

    def esta_conectada(self):
        return False

    def pedir_modos(self):
        self._pendiente("pedir modos")

    def seleccionar_modo(self, modo):
        self._pendiente("seleccionar modo")

    def preparar(self, trabajo, x_cabezal_mm):
        return self._pendiente("ripear")

    def armar(self, posicion_eje_mm):
        return self._pendiente("armar")

    def abortar(self):
        self._pendiente("abortar")
