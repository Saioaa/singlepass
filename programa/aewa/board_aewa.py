# -*- coding: utf-8 -*-
"""Board APMB4 (cabezal Ricoh de Aewa) gobernada por APRINT: interfaz Board de
programa/gis/board.py sobre el protocolo remoto (aprint_comunicacion).

  preparar: crea la carpeta del trabajo (RIPOutput), convierte la imagen a un
            PDF del tamano fisico exacto (pixeles / dpi del modo, como las
            boards GIS: APRINT escala los mapas de bits por los dpi grabados en
            el archivo, el PDF evita esa dependencia) y prepara el job en APRINT:
            "pd" cierra el dialogo, "jc" cierra el job, "pp" resoluciones y sin
            multipass, "ji" inserta el PDF con el offset X (distancia desde el
            PULSE hasta la imagen, como el XOffset del PMB: el "blanco por
            delante" de MBD-F-500) y "jv" guarda el .ajb en la carpeta.
  armar:    "pd" abre el dialogo de impresion y "ps" arranca: con Printing mode
            "Single pass - External trigger" APRINT queda esperando el pulso
            del M-Duino (una franja = todo el trabajo).
  abortar:  "px" para, espera con "pi" y "pd" cierra el dialogo.

Todo lo que habla con APRINT va en un hilo (puede tardar); el resultado vuelve
por senal al hilo de Qt. Sin modos: la resolucion la fija la pagina
(seleccionar_resolucion) y se anuncia por dpi_recibido como en las demas boards.
"""

import os
import struct
import threading
import time
from datetime import datetime

from PySide6.QtCore import QMarginsF, QSizeF, Signal
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from programa import config
from programa.aewa.aprint_comunicacion import (OPCION_RESERVADA, TODAS_LAS_IMPRESORAS, ErrorAprint,
                                               i32, texto, u16, u32)
from programa.aewa.aprint_propiedades import (MODO_MULTIPASS_NINGUNO, PARAM_DPI_HORIZONTAL,
                                              PARAM_DPI_VERTICAL, PARAM_MODO_MULTIPASS)
from programa.gis import vpi
from programa.gis.board import (ESTADO_ARMANDO, ESTADO_LISTO, ESTADO_RENDER_LISTO,
                                ESTADO_SIN_TRABAJO, Board, calcular_offset_x)

DECIMALES_MM = 2
ESCALA_MILES = 1000
PD_ABRIR = 1
PD_CERRAR = 0
JC_SIN_GUARDAR = 0
SIN_ESCALAR = 0
EXTENSION_JOB = ".ajb"
EXTENSION_PDF = ".pdf"
PREFIJO_CARPETA = "aewa"
FORMATO_MARCA = "%Y%m%d_%H%M%S"
TAM_ESTADO_PI = 2              # "pi": 2 bytes, un bit por impresora (1 = imprimiendo)
ESPERA_PARADA_S = 10.0
SONDEO_PARADA_S = 0.2
# La app gira en sentido horario; APRINT guarda el angulo en sentido antihorario
GRADOS_VUELTA = 360
CODIGO_GIRO = {0: 0, 90: 1, 180: 2, 270: 3}   # angulo APRINT -> bits 3..2 de Option2 de "ji"
DESPLAZAMIENTO_GIRO = 2
BIT_ESPEJO_X = 0x0001
BIT_ESPEJO_Y = 0x0002


def giro_aprint(rotacion_horaria):
    return (GRADOS_VUELTA - rotacion_horaria) % GRADOS_VUELTA


def mm_a_pixeles(mm):
    """Posicion de "ji" (X o Y) en pixeles a config.APRINT_DPI_POSICION."""
    return round(mm / config.MM_POR_PULGADA * config.APRINT_DPI_POSICION)


def imagen_a_pdf(ruta_imagen, ruta_pdf, ancho_mm, alto_mm, dpi):
    """PDF de una pagina del tamano fisico dado con la imagen a toda pagina.
    Debe llamarse desde el hilo de Qt (QPainter)."""
    imagen = QImage(ruta_imagen)
    if imagen.isNull():
        raise ValueError(f"no se puede leer la imagen {ruta_imagen}")
    escritor = QPdfWriter(ruta_pdf)
    escritor.setResolution(dpi)
    escritor.setPageLayout(QPageLayout(QPageSize(QSizeF(ancho_mm, alto_mm), QPageSize.Millimeter),
                                       QPageLayout.Portrait, QMarginsF(0, 0, 0, 0)))
    pintor = QPainter(escritor)
    pintor.drawImage(escritor.pageLayout().paintRectPixels(dpi), imagen)
    pintor.end()


class BoardAewa(Board):

    nombre = "AEWA"
    tipos_modulo = ("APMB4",)

    _hecho = Signal(str, bool, list)   # interno: (operacion, correcto, lineas de log) desde el hilo

    def __init__(self, aprint, parent=None):
        super().__init__(parent)
        self.aprint = aprint                 # programa.aewa.aprint_comunicacion.Aprint
        self.res_horizontal = config.RESOLUCIONES_HORIZONTALES_AEWA_DPI[0]
        self.res_vertical = config.RESOLUCION_VERTICAL_AEWA_POR_DEFECTO
        self._ruta_job = None
        self._geometria = None               # (x_mm, ancho_mm) del trabajo preparado
        self._ocupada = False
        self._hecho.connect(self._tras_operacion)

    # ===== conexion y resolucion =====
    def conectar(self):
        if not self.aprint.conectado:
            self.aprint.conectar()           # en segundo plano; de momento no esta
        return self.aprint.conectado

    def esta_conectada(self):
        return self.aprint.conectado

    def pedir_modos(self):
        self.modos_recibidos.emit([])        # sin modos: resoluciones (pagina AEWA)

    def seleccionar_modo(self, modo):
        pass

    def seleccionar_resolucion(self, horizontal_dpi, vertical_dpi):
        """La pagina AEWA la fija desde sus desplegables. Se anuncia como los dpi
        del modo: con ellos se mide la imagen en la mesa (X = sentido del
        movimiento = vertical de APRINT; Y = a lo largo del cabezal = horizontal)."""
        self.res_horizontal = horizontal_dpi
        self.res_vertical = vertical_dpi
        self.dpi_recibido.emit(vertical_dpi, horizontal_dpi)

    # ===== trabajo =====
    def preparar(self, trabajo, x_cabezal_mm):
        if self._ocupada:
            self.registrar("Ocupada con otra orden")
            return False
        if not self.aprint.conectado:
            self.registrar("APRINT no conectado")
            self.conectar()
            return False
        offset_x_mm = calcular_offset_x(x_cabezal_mm, trabajo.x_mm, trabajo.ancho_mm)
        if offset_x_mm < 0:
            self.registrar(f"La imagen ya esta bajo el cabezal en reposo (offset X = "
                           f"{offset_x_mm:.{DECIMALES_MM}f} mm): aleja el reposo o acerca la "
                           "imagen al 0 de la mesa")
            return False
        y_mm = trabajo.y_mm - config.Y_CABEZAL_AEWA_MM
        if y_mm < 0:
            self.registrar(f"La imagen queda {-y_mm:.{DECIMALES_MM}f} mm por encima del cabezal "
                           f"(Y del cabezal en la mesa: {config.Y_CABEZAL_AEWA_MM} mm)")
            return False
        self.registrar(f"Imagen en mesa: X={trabajo.x_mm:.{DECIMALES_MM}f} mm, "
                       f"Y={trabajo.y_mm:.{DECIMALES_MM}f} mm; cabezal a "
                       f"{x_cabezal_mm:.{DECIMALES_MM}f} mm -> offset X = "
                       f"{offset_x_mm:.{DECIMALES_MM}f} mm")

        nombre = os.path.splitext(os.path.basename(trabajo.ruta_imagen))[0]
        marca = datetime.now().strftime(FORMATO_MARCA)
        carpeta = os.path.join(vpi.CARPETA_SALIDA, f"{marca}_{PREFIJO_CARPETA}_{nombre}")
        ruta_pdf = os.path.join(carpeta, nombre + EXTENSION_PDF)
        ruta_job = os.path.join(carpeta, nombre + EXTENSION_JOB)
        try:
            os.makedirs(carpeta, exist_ok=True)
            # el tamano fisico de la imagen en la mesa ya esta en mm (pixeles / dpi del modo)
            imagen_a_pdf(trabajo.ruta_imagen, ruta_pdf, trabajo.ancho_mm, trabajo.alto_mm,
                         max(self.res_horizontal, self.res_vertical))
        except (OSError, ValueError) as e:
            self.registrar(f"No se ha podido preparar el trabajo: {e}")
            return False
        self.registrar(f"Trabajo generado: {ruta_pdf}")

        giro = giro_aprint(trabajo.rotacion)
        # la mesa avanza hacia +X y el cabezal esta delante: el borde x + ancho de la
        # imagen pasa primero bajo el cabezal, es decir, en el job de APRINT (X = sentido
        # de impresion) la imagen va espejada en X respecto a la mesa
        espejo_x = trabajo.espejo_x != config.INVERTIR_X_AEWA
        opciones = CODIGO_GIRO[giro] << DESPLAZAMIENTO_GIRO
        if espejo_x:
            opciones |= BIT_ESPEJO_X
        if trabajo.espejo_y:
            opciones |= BIT_ESPEJO_Y
        x_px = mm_a_pixeles(offset_x_mm)
        y_px = mm_a_pixeles(y_mm)
        self.carpeta_trabajo = carpeta
        self._ruta_job = ruta_job
        self._geometria = (trabajo.x_mm, trabajo.ancho_mm)
        self._poner_estado(ESTADO_SIN_TRABAJO)
        self._ocupada = True

        def tarea():
            c = self.aprint.cliente
            lineas = []
            try:
                with self.aprint.candado_dialogo:
                    try:
                        c.comando("pd", u16(PD_CERRAR))
                    except ErrorAprint as e:
                        lineas.append(f"Cierre previo del dialogo de impresion: {e}")
                    c.comando("jc", u16(JC_SIN_GUARDAR))
                    c.escribir_parametro(PARAM_DPI_HORIZONTAL, self.res_horizontal * ESCALA_MILES)
                    c.escribir_parametro(PARAM_DPI_VERTICAL, self.res_vertical * ESCALA_MILES)
                    c.escribir_parametro(PARAM_MODO_MULTIPASS, MODO_MULTIPASS_NINGUNO)
                    c.comando("ji", u16(OPCION_RESERVADA) + u16(opciones) + i32(x_px) + i32(y_px)
                              + u32(SIN_ESCALAR) + u32(SIN_ESCALAR) + texto(ruta_pdf))
                    c.comando("jv", u16(OPCION_RESERVADA) + texto(ruta_job))
                    leidos = (c.leer_parametro(PARAM_DPI_HORIZONTAL) / ESCALA_MILES,
                              c.leer_parametro(PARAM_DPI_VERTICAL) / ESCALA_MILES)
            except (OSError, ErrorAprint) as e:
                lineas.append(f"Error al preparar el job en APRINT: {c.describir(e)}")
                self._hecho.emit("preparar", False, lineas)
                return
            lineas.append(f"Job {os.path.basename(ruta_job)}: offset X {offset_x_mm:.{DECIMALES_MM}f}"
                          f" mm = {x_px} px, Y {y_mm:.{DECIMALES_MM}f} mm = {y_px} px a "
                          f"{config.APRINT_DPI_POSICION} dpi; giro APRINT {giro}, espejo X "
                          f"{espejo_x}, espejo Y {trabajo.espejo_y}; APRINT a "
                          f"{leidos[0]:g} x {leidos[1]:g} dpi (H x V)")
            if leidos != (self.res_horizontal, self.res_vertical):
                lineas.append(f"AVISO: se pidieron {self.res_horizontal} x {self.res_vertical} dpi")
            self._hecho.emit("preparar", True, lineas)

        threading.Thread(target=tarea, daemon=True).start()
        return True

    def geometria_trabajo(self):
        return self._geometria if self.estado != ESTADO_SIN_TRABAJO else None

    def cargar_carpeta(self, carpeta):
        return False   # pendiente: abrir un .ajb guardado ("jo")

    # ===== armado =====
    def armar(self, posicion_eje_mm):
        if self.estado != ESTADO_RENDER_LISTO:
            self.registrar("No hay ningun job preparado: pulsa Render")
            return False
        if self._ocupada:
            self.registrar("Ocupada con otra orden")
            return False
        self._ocupada = True
        self._poner_estado(ESTADO_ARMANDO)

        def tarea():
            c = self.aprint.cliente
            try:
                with self.aprint.candado_dialogo:
                    try:
                        c.comando("pd", u16(PD_CERRAR))
                    except ErrorAprint:
                        pass
                    c.comando("pd", u16(PD_ABRIR))
                    c.comando("ps", u16(TODAS_LAS_IMPRESORAS) + u16(OPCION_RESERVADA))
                    self.aprint.impresion_en_marcha = True
            except (OSError, ErrorAprint) as e:
                motivo = c.describir(e)
                self._cerrar_dialogo(c)
                self._hecho.emit("armar", False, [f"No se ha podido armar: {motivo}"])
                return
            self._hecho.emit("armar", True, ["Armada: APRINT espera el pulso de print go (pd + ps)"])

        threading.Thread(target=tarea, daemon=True).start()
        return True

    def abortar(self):
        if self.estado not in (ESTADO_ARMANDO, ESTADO_LISTO):
            return
        self._ocupada = True
        self._poner_estado(ESTADO_RENDER_LISTO)

        def tarea():
            c = self.aprint.cliente
            lineas = []
            with self.aprint.candado_dialogo:
                try:
                    c.comando("px", u16(TODAS_LAS_IMPRESORAS) + u16(OPCION_RESERVADA))
                except (OSError, ErrorAprint) as e:
                    lineas.append(f"AVISO: no se ha podido parar la impresion: {c.describir(e)}")
                self._esperar_parada(c, lineas)
                self.aprint.impresion_en_marcha = False
                self._cerrar_dialogo(c, lineas)
            lineas.append("Desarmada (px + pd cerrado)")
            self._hecho.emit("abortar", True, lineas)

        threading.Thread(target=tarea, daemon=True).start()

    def descartar(self):
        self._ruta_job = None
        self._geometria = None
        super().descartar()

    # ===== hilo -> Qt =====
    def _tras_operacion(self, operacion, correcto, lineas):
        self._ocupada = False
        for linea in lineas:
            self.registrar(linea)
        if operacion == "preparar":
            self._poner_estado(ESTADO_RENDER_LISTO if correcto else ESTADO_SIN_TRABAJO)
        elif operacion == "armar":
            self._poner_estado(ESTADO_LISTO if correcto else ESTADO_RENDER_LISTO)

    @staticmethod
    def _esperar_parada(c, lineas):
        limite = time.monotonic() + ESPERA_PARADA_S
        while True:
            try:
                estado = struct.unpack("<H", c.comando("pi", retorno=TAM_ESTADO_PI))[0]
            except (OSError, ErrorAprint, struct.error) as e:
                lineas.append(f"Estado de impresion no disponible: {e}")
                return
            if not estado:
                return
            if time.monotonic() >= limite:
                lineas.append(f"Sigue imprimiendo tras {ESPERA_PARADA_S:g} s: se cierra el dialogo "
                              "igualmente")
                return
            time.sleep(SONDEO_PARADA_S)

    @staticmethod
    def _cerrar_dialogo(c, lineas=None):
        try:
            c.comando("pd", u16(PD_CERRAR))
        except (OSError, ErrorAprint) as e:
            if lineas is not None:
                lineas.append(f"AVISO: no se ha podido cerrar el dialogo de impresion: {c.describir(e)}")
