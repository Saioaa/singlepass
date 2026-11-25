# -*- coding: utf-8 -*-
"""Pagina Print Server AEWA: la logica comun de print_server.py (PrintServer con
WIDGETS_AEWA) sobre la board APMB4 (programa/aewa/board_aewa.py, APRINT), mas
lo propio de esta pagina:

  - desplegables de resolucion (select_res_horizontal, select_res_vertical) con
    las opciones de la impresora "Singlepass BW" de APRINT: fijan la resolucion
    de la board y, con ella, el tamano de la imagen en la mesa; se guardan en
    ajustes.json. Cambiarlas invalida el render, como cambiar de modo en GIS.
  - Nueva imagen abre solo PDF (lo que imprime APRINT); el tamano fisico es el
    de la pagina del PDF, no depende de la resolucion. La mesa muestra la
    primera pagina renderizada.
  - labelInfo_impresion: recuadro con el trabajo, la resolucion, la imagen en la
    mesa, el offset hasta el cabezal, la velocidad de Programa (y la frecuencia
    de disparo que supone) y los Printer Settings leidos de APRINT, con avisos.
    Se refresca con cada cambio (senal cambiado de PrintServer) y al conectar.
  - test_cabezal: pone el PNG del test (config.RUTA_TEST_CABEZAL, 1280 filas =
    boquillas a 600 dpi) a 600 x 600 dpi en la posicion fija de la mesa y lo
    renderiza; se imprime con START PRINT como cualquier trabajo.
  - texto_variable: pendiente (se traera de MBD-F-500 cuando este comprobada
    la orientacion del job).

Una sola pasada y la velocidad la fija la pagina Programa: sin desplegables de
pasos ni de velocidad.
"""

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtPdf import QPdfDocument

from programa import config
from programa.aewa.aprint_propiedades import (MODO_IMPRESION_EXTERNO, NOMBRES_MODO_IMPRESION,
                                              aviso_filas, _version)
from programa.gis.board import ESTADO_LISTO, ESTADO_SIN_TRABAJO, calcular_offset_x
from interfaz.print_server import (MOTIVO_MODO_CAMBIADO, TEXTOS_PRINT_AEWA, WIDGETS_AEWA,
                                   PrintServer)

SUFIJO_DPI = "dpi"
FILTRO_PDF = "PDF (*.pdf)"
EXTENSION_PDF = ".pdf"
PAGINA_IMPRESION = 0
PUNTOS_POR_PULGADA = 72
MM_POR_PUNTO = config.MM_POR_PULGADA / PUNTOS_POR_PULGADA
PX_POR_MM_VISTA = 4.0        # resolucion de la vista en la mesa (solo para verla)
LADO_MAX_VISTA_PX = 4000
COLOR_FONDO_VISTA = Qt.white # el PDF puede tener fondo transparente: sobre blanco
ESTILO_INFO_EXTRA = "font-size: 14px; font-family: nunito; color: #333333; padding: 8px;"
TEXTO_SIN_DATO = "---"
DECIMALES_MM = 2
MICRAS_POR_MM = 1000
HZ_POR_KHZ = 1000
SEPARADOR = "  \u00b7  "
CLAVE_RES_HORIZONTAL = "res_horizontal"
CLAVE_RES_VERTICAL = "res_vertical"
TEXTO_PENDIENTE = "[AEWA] Pendiente: {}"


def leer_pdf(ruta):
    """(pixmap de la primera pagina, ancho_mm, alto_mm, paginas). ValueError si no abre."""
    documento = QPdfDocument()
    error = documento.load(str(ruta))
    if error != QPdfDocument.Error.None_ or documento.pageCount() < 1:
        raise ValueError(f"no se puede abrir el PDF ({error.name})")
    tamano_pt = documento.pagePointSize(PAGINA_IMPRESION)
    ancho_mm = tamano_pt.width() * MM_POR_PUNTO
    alto_mm = tamano_pt.height() * MM_POR_PUNTO
    escala = min(PX_POR_MM_VISTA, LADO_MAX_VISTA_PX / max(ancho_mm, alto_mm))
    tamano_px = QSize(max(1, round(ancho_mm * escala)), max(1, round(alto_mm * escala)))
    pagina = documento.render(PAGINA_IMPRESION, tamano_px)
    vista = QImage(tamano_px, QImage.Format_RGB32)
    vista.fill(COLOR_FONDO_VISTA)
    pintor = QPainter(vista)
    pintor.drawImage(0, 0, pagina)
    pintor.end()
    paginas = documento.pageCount()
    documento.close()
    return QPixmap.fromImage(vista), ancho_mm, alto_mm, paginas


class PrintServerAewa(PrintServer):

    FILTRO_ARCHIVOS = FILTRO_PDF
    TITULO_ARCHIVO = "Nueva imagen (PDF)"

    def __init__(self, ui, board, cabezales_activos, posicion_eje, iniciar_programa,
                 parar_programa, programa_en_marcha, velocidad_impresion, parent=None):
        """velocidad_impresion: callable -> mm/s de la pagina Programa, o None."""
        super().__init__(ui, [board], cabezales_activos, posicion_eje, iniciar_programa,
                         parar_programa, programa_en_marcha, widgets=WIDGETS_AEWA,
                         textos_print=TEXTOS_PRINT_AEWA, parent=parent)
        self.board = board
        self._velocidad_impresion = velocidad_impresion

        # ===== recuadro de informacion =====
        info = ui.labelInfo_impresion
        info.setStyleSheet(info.styleSheet() + "\n" + ESTILO_INFO_EXTRA)
        info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info.setWordWrap(True)
        self.cambiado.connect(self.refrescar_info)
        board.aprint.conexion_terminada.connect(self.refrescar_info)

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
        self.refrescar_info()

        ui.test_cabezal.clicked.connect(self.test_cabezal)
        # ===== pendiente =====
        ui.texto_variable.clicked.connect(lambda: self.registrar(TEXTO_PENDIENTE.format("insertar texto")))

    # ===== imagen (PDF; el test de cabezal es un PNG) =====
    def _abrir_archivo(self, ruta):
        if not ruta.lower().endswith(EXTENSION_PDF):
            return super()._abrir_archivo(ruta)   # mapa de bits: pixeles / dpi del modo
        pixmap, ancho_mm, alto_mm, paginas = leer_pdf(ruta)
        if paginas > 1:
            self.registrar(f"[PRINT SERVER] AVISO: el PDF tiene {paginas} paginas, se usa la primera")
        return pixmap, (ancho_mm, alto_mm)

    # ===== test de cabezal =====
    def test_cabezal(self):
        """Trabajo de test del cabezal: PNG de la app, resolucion y posicion fijas, y render."""
        if not os.path.isfile(config.RUTA_TEST_CABEZAL):
            self.registrar(f"[TEST] Falta la imagen del test de cabezal: {config.RUTA_TEST_CABEZAL}")
            return
        self._seleccionar(self.ui.select_res_horizontal, config.TEST_CABEZAL_RES_HORIZONTAL_DPI)
        self._seleccionar(self.ui.select_res_vertical, config.TEST_CABEZAL_RES_VERTICAL_DPI)
        if not self.cargar_archivo(config.RUTA_TEST_CABEZAL, config.TEST_CABEZAL_X_MM,
                                   config.TEST_CABEZAL_Y_MM):
            return
        self.registrar("[TEST] Test de cabezal en la mesa: renderizando")
        self.generar_trabajo()

    # ===== recuadro de informacion =====
    def refrescar_info(self, *_):
        lineas = []
        if self.ruta_imagen is None:
            trabajo = TEXTO_SIN_DATO
        else:
            nombre = os.path.basename(self.ruta_imagen)
            if self.board.estado == ESTADO_LISTO:
                trabajo = f"{nombre}  [ARMADO]"
            elif self.board.estado != ESTADO_SIN_TRABAJO:
                trabajo = f"{nombre}  [RENDERIZADO]"
            else:
                trabajo = f"{nombre}  [SIN RENDERIZAR]"
        lineas.append(f"Trabajo: {trabajo}")
        lineas.append(f"Resolución: {self.res_horizontal()} x {self.res_vertical()} dpi (H x V)")

        geometria = self.mesa.posicion_imagen_mm()
        if geometria is not None and self.ancho_imagen_mm is not None:
            x_mm, y_mm = geometria
            lineas.append(f"Imagen: {self.ancho_imagen_mm:.{DECIMALES_MM}f} x "
                          f"{self.alto_imagen_mm:.{DECIMALES_MM}f} mm en X {x_mm:.{DECIMALES_MM}f}"
                          f"{SEPARADOR}Y {y_mm:.{DECIMALES_MM}f} mm")
            activas = self.boards_activas()
            if activas:
                _board, x_cabezal_mm = activas[0]
                offset_mm = calcular_offset_x(x_cabezal_mm, x_mm, self.ancho_imagen_mm)
                lineas.append(f"Cabezal APMB4 a {x_cabezal_mm:.{DECIMALES_MM}f} mm{SEPARADOR}"
                              f"offset {offset_mm:.{DECIMALES_MM}f} mm{SEPARADOR}cubre Y "
                              f"{config.Y_CABEZAL_AEWA_MM:g} a "
                              f"{config.Y_CABEZAL_AEWA_MM + config.ANCHO_CABEZAL_AEWA_MM:.{DECIMALES_MM}f} mm")
                if offset_mm < 0:
                    lineas.append("AVISO: la imagen queda bajo el cabezal antes del print go")
                if y_mm < config.Y_CABEZAL_AEWA_MM or \
                        y_mm + self.alto_imagen_mm > config.Y_CABEZAL_AEWA_MM + config.ANCHO_CABEZAL_AEWA_MM:
                    lineas.append("AVISO: la imagen sobresale del cabezal en Y")
            else:
                lineas.append("AVISO: ningún APMB4 activo en Programa")

        velocidad = self._velocidad_impresion()
        if velocidad:
            frecuencia_hz = self.res_vertical() * velocidad / config.MM_POR_PULGADA
            lineas.append(f"Velocidad (Programa): {velocidad:g} mm/s{SEPARADOR}disparo "
                          f"{frecuencia_hz / HZ_POR_KHZ:.1f} kHz a {self.res_vertical()} dpi")
        else:
            lineas.append("Velocidad (Programa): sin definir")

        aprint = self.board.aprint
        if not aprint.conectado:
            lineas.append("APRINT: no conectado")
        else:
            p = aprint.cliente.propiedades
            if not p:
                lineas.append("APRINT: conectado")
            else:
                modo = NOMBRES_MODO_IMPRESION.get(p.get("modo_impresion"), p.get("modo_impresion"))
                version = _version(p["version"]) if p.get("version") is not None else ""
                lineas.append(f"APRINT {version}: {p.get('dpi_horizontal'):g} x "
                              f"{p.get('dpi_vertical'):g} dpi{SEPARADOR}disparo {modo}{SEPARADOR}"
                              f"encoder {p.get('resolucion_encoder'):g} dpi")
                retardo = p.get("retardo_impresion_um")
                if retardo:
                    lineas.append(f"AVISO: retardo de impresión en APRINT {retardo / MICRAS_POR_MM:g} mm "
                                  "(el offset ya va en el job: debería ser 0)")
                if p.get("modo_impresion") not in (None, MODO_IMPRESION_EXTERNO):
                    lineas.append("AVISO: Printing mode debe ser Single pass - External trigger")
                aviso = aviso_filas(p)
                if aviso:
                    lineas.append(f"AVISO: {aviso}")
        self.ui.labelInfo_impresion.setText("\n".join(lineas))

    # ===== resoluciones =====
    def res_horizontal(self):
        return self.ui.select_res_horizontal.currentData()

    def res_vertical(self):
        return self.ui.select_res_vertical.currentData()

    def _resolucion_cambiada(self, _indice):
        self.invalidar_render(MOTIVO_MODO_CAMBIADO)
        self._aplicar_resolucion()
        self.refrescar_info()

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
