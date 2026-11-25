# -*- coding: utf-8 -*-
"""Pagina Print Server AEWA: la logica comun de print_server.py (PrintServer con
WIDGETS_AEWA) sobre la board APMB4 (programa/aewa/board_aewa.py, APRINT), mas
lo propio de esta pagina:

  - desplegables de resolucion (select_res_horizontal, select_res_vertical) con
    las opciones de la impresora "Singlepass BW" de APRINT: fijan la resolucion
    de la board y, con ella, el tamano de la imagen en la mesa; se guardan en
    ajustes.json. Cambiarlas invalida el render, como cambiar de modo en GIS.
  - test_cabezal y texto_variable: pendientes (se traeran de MBD-F-500).

Una sola pasada y la velocidad la fija la pagina Programa: sin desplegables de
pasos ni de velocidad.
"""

from programa import config
from interfaz.print_server import (MOTIVO_MODO_CAMBIADO, TEXTOS_PRINT_AEWA, WIDGETS_AEWA,
                                   PrintServer)

SUFIJO_DPI = "dpi"
CLAVE_RES_HORIZONTAL = "res_horizontal"
CLAVE_RES_VERTICAL = "res_vertical"
TEXTO_PENDIENTE = "[AEWA] Pendiente: {}"


class PrintServerAewa(PrintServer):

    def __init__(self, ui, board, cabezales_activos, posicion_eje, iniciar_programa,
                 parar_programa, programa_en_marcha, parent=None):
        super().__init__(ui, [board], cabezales_activos, posicion_eje, iniciar_programa,
                         parar_programa, programa_en_marcha, widgets=WIDGETS_AEWA,
                         textos_print=TEXTOS_PRINT_AEWA, parent=parent)
        self.board = board

        # ===== resoluciones =====
        for dpi in config.RESOLUCIONES_HORIZONTALES_AEWA_DPI:
            ui.select_res_horizontal.addItem(f"{dpi} {SUFIJO_DPI}", dpi)
        for dpi in config.RESOLUCIONES_VERTICALES_AEWA_DPI:
            ui.select_res_vertical.addItem(f"{dpi} {SUFIJO_DPI}", dpi)
        # con una sola opcion el desplegable no tiene nada que elegir
        ui.select_res_horizontal.setEnabled(len(config.RESOLUCIONES_HORIZONTALES_AEWA_DPI) > 1)
        self._seleccionar(ui.select_res_vertical, config.RESOLUCION_VERTICAL_AEWA_POR_DEFECTO)
        ui.select_res_horizontal.currentIndexChanged.connect(self._resolucion_cambiada)
        ui.select_res_vertical.currentIndexChanged.connect(self._resolucion_cambiada)
        self._aplicar_resolucion()

        # ===== pendientes =====
        ui.test_cabezal.clicked.connect(lambda: self.registrar(TEXTO_PENDIENTE.format("test de cabezal")))
        ui.texto_variable.clicked.connect(lambda: self.registrar(TEXTO_PENDIENTE.format("insertar texto")))

    # ===== resoluciones =====
    def res_horizontal(self):
        return self.ui.select_res_horizontal.currentData()

    def res_vertical(self):
        return self.ui.select_res_vertical.currentData()

    def _resolucion_cambiada(self, _indice):
        self.invalidar_render(MOTIVO_MODO_CAMBIADO)
        self._aplicar_resolucion()

    def _aplicar_resolucion(self):
        self.board.seleccionar_resolucion(self.res_horizontal(), self.res_vertical())

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
