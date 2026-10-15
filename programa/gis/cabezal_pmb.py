# -*- coding: utf-8 -*-
"""Temperatura del cabezal a traves del Print Server (PMB).

Equivalente a aprint_cabezal.py de MBD-F-500, pero con el PMB:

  - Lectura: el Print Controller envia a sus listeners el estado de cabezales
    (I,<id>,H,<xml>, manual GIS 6.7). pmb.py lo parsea y lo emite por
    estado_cabezales como [{"nombre", "temperatura", "objetivo", "activo"}, ...];
    aqui se toma el primer cabezal activo (o el primero si ninguno lo esta).
  - Consigna: se escribe el parametro TargetControllerTemp del Print Controller
    (config.PARAMETRO_CONSIGNA_CABEZAL) con ClientePMB.cambiar_parametro_pc.

Si el PMB no esta conectado o deja de enviar estados, la interfaz muestra "--".
"""

from PySide6.QtCore import QObject, QTimer, Signal

from programa import config

CLAVE_TEMPERATURA = "temperatura"
CLAVE_OBJETIVO = "objetivo"
CLAVE_ACTIVO = "activo"
SIN_ESTADO_S = 10.0            # sin estado de cabezales durante este tiempo -> "--"
PERIODO_VIGILANCIA_MS = 2000


class TemperaturaCabezal(QObject):

    lectura = Signal(object, object)   # (real ºC o None, consigna ºC o None)
    mensaje = Signal(str)

    def __init__(self, pmb, parent=None):
        super().__init__(parent)
        self.pmb = pmb
        self._real = None
        self._consigna = None
        self._sin_estado_s = 0.0
        pmb.estado_cabezales.connect(self._estado_cabezales)
        pmb.conexion_perdida.connect(lambda _motivo: self._sin_dato())

        self._timer = QTimer(self)
        self._timer.setInterval(PERIODO_VIGILANCIA_MS)
        self._timer.timeout.connect(self._vigilar)
        self._timer.start()

    def cerrar(self):
        self._timer.stop()

    # ===== consigna =====
    def fijar_consigna(self, grados):
        if not self.pmb.conectado():
            self.mensaje.emit("[CABEZAL] PMB no conectado: consigna de temperatura no enviada")
            return
        self.pmb.cambiar_parametro_pc(config.PARAMETRO_CONSIGNA_CABEZAL, f"{grados:g}")
        self.mensaje.emit(f"[CABEZAL] Consigna de temperatura enviada: {grados:g} ºC")

    # ===== estado de cabezales =====
    def _estado_cabezales(self, cabezales):
        if not cabezales:
            return
        cabezal = next((c for c in cabezales if c.get(CLAVE_ACTIVO)), cabezales[0])
        self._sin_estado_s = 0.0
        self._real = cabezal.get(CLAVE_TEMPERATURA)
        self._consigna = cabezal.get(CLAVE_OBJETIVO)
        self.lectura.emit(self._real, self._consigna)

    def _vigilar(self):
        self._sin_estado_s += PERIODO_VIGILANCIA_MS / 1000
        if self._sin_estado_s >= SIN_ESTADO_S or not self.pmb.conectado():
            self._sin_dato()

    def _sin_dato(self):
        if self._real is not None or self._consigna is not None:
            self._real = None
            self._consigna = None
            self.lectura.emit(None, None)
