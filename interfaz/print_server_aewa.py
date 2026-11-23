# -*- coding: utf-8 -*-
"""Pagina Print Server AEWA (cabezal Ricoh en APMB4, gobernado por APRINT).

PRIMER PASO: solo los desplegables de resolucion, con las opciones de la
impresora "Singlepass BW" de APRINT (config.RESOLUCIONES_*_AEWA_DPI), y su
persistencia en ajustes.json. La imagen, el renderizado, el trabajo en APRINT
y la impresion se iran anadiendo a partir de la app MBD-F-500. Una sola pasada
(sin multipass) y la velocidad la fija la pagina Programa: no hay desplegables
de pasos ni de velocidad.

Widgets de la pagina print_server_aewa: select_res_horizontal,
select_res_vertical, txtMessage_printserver (en el registro comun de
print_server.py).
"""

from PySide6.QtCore import QObject

from programa import config

NOMBRE_PAGINA = "print_server_aewa"
SUFIJO_DPI = "dpi"
CLAVE_RES_HORIZONTAL = "res_horizontal"
CLAVE_RES_VERTICAL = "res_vertical"


class PrintServerAewa(QObject):

    def __init__(self, ui, aprint, registrar, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.aprint = aprint          # programa.aewa.aprint_comunicacion.Aprint
        self.registrar = registrar
        self.pagina = getattr(ui, NOMBRE_PAGINA)

        # ===== desplegables =====
        for dpi in config.RESOLUCIONES_HORIZONTALES_AEWA_DPI:
            ui.select_res_horizontal.addItem(f"{dpi} {SUFIJO_DPI}", dpi)
        for dpi in config.RESOLUCIONES_VERTICALES_AEWA_DPI:
            ui.select_res_vertical.addItem(f"{dpi} {SUFIJO_DPI}", dpi)
        # con una sola opcion el desplegable no tiene nada que elegir
        ui.select_res_horizontal.setEnabled(len(config.RESOLUCIONES_HORIZONTALES_AEWA_DPI) > 1)
        self._seleccionar(ui.select_res_vertical, config.RESOLUCION_VERTICAL_AEWA_POR_DEFECTO)

    # ===== lectura =====
    def res_horizontal(self):
        return self.ui.select_res_horizontal.currentData()

    def res_vertical(self):
        return self.ui.select_res_vertical.currentData()

    # ===== navegacion =====
    def entrar(self):
        self.ui.stackedWidget.setCurrentWidget(self.pagina)

    # ===== persistencia (la gestiona la ventana principal) =====
    def estado(self):
        return {CLAVE_RES_HORIZONTAL: self.res_horizontal(),
                CLAVE_RES_VERTICAL: self.res_vertical()}

    def restaurar(self, estado):
        estado = estado or {}
        self._seleccionar(self.ui.select_res_horizontal, estado.get(CLAVE_RES_HORIZONTAL))
        self._seleccionar(self.ui.select_res_vertical, estado.get(CLAVE_RES_VERTICAL))

    @staticmethod
    def _seleccionar(combo, dato):
        indice = combo.findData(dato)
        if indice >= 0:
            combo.setCurrentIndex(indice)
