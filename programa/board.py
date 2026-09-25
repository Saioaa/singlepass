# -*- coding: utf-8 -*-
"""Interfaz comun de las boards de impresion (PMB-C8/C2 via GIS Print Server,
SM-200 via API REST, APMB4 mas adelante).

La pagina Print Server no sabe de protocolos: prepara un Trabajo (imagen y su
posicion en la mesa) y se lo pasa a cada board activa junto con la posicion de
su cabezal en la barra. Cada board ripea, calcula su propio offset, se arma y
avisa de su estado por senales.

Geometria comun (config.py): la mesa avanza hacia +X y el cabezal esta mas
adelante; el borde de la imagen que llega primero al cabezal es x + ancho.
"""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

import config

# ===== ESTADOS DE UNA BOARD (en orden creciente de preparacion) =====
ESTADO_SIN_TRABAJO  = "sin_trabajo"    # nada ripeado
ESTADO_RENDER_LISTO = "render_listo"   # trabajo ripeado, falta armar
ESTADO_ARMANDO      = "armando"        # armado en curso
ESTADO_LISTO        = "listo"          # armada: espera el print go
ORDEN_ESTADOS = (ESTADO_SIN_TRABAJO, ESTADO_RENDER_LISTO, ESTADO_ARMANDO, ESTADO_LISTO)


@dataclass
class Trabajo:
    """Imagen a imprimir y su colocacion en la mesa (mm)."""
    ruta_imagen: str
    ancho_mm: float
    alto_mm: float
    x_mm: float
    y_mm: float
    rotacion: int = 0
    espejo_x: bool = False
    espejo_y: bool = False


def calcular_offset_x(x_cabezal_mm, x_imagen_mm, ancho_imagen_mm):
    """Distancia (mm) que recorre el carro desde el PULSE hasta que la imagen
    empieza a pasar bajo el cabezal (borde lejano: x_imagen + ancho)."""
    return x_cabezal_mm - (x_imagen_mm + ancho_imagen_mm) - config.POSICION_PULSE_MM


def recorrido_impresion_mm(x_cabezal_mm, x_imagen_mm, ancho_imagen_mm):
    """Posicion del eje en la que la board termina de imprimir: el borde cercano
    de la imagen (x_imagen) pasa bajo el cabezal."""
    return x_cabezal_mm - x_imagen_mm


class Board(QObject):
    """Clase base. Las subclases implementan los metodos marcados."""

    nombre = "board"          # etiqueta en los mensajes: [PMB], [EPSON]...
    tipos_modulo = ()         # tipos de modulo de la pagina Programa que gobierna esta board

    mensaje = Signal(str)
    modos_recibidos = Signal(list)
    dpi_recibido = Signal(int, int)
    estado_cambiado = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado = ESTADO_SIN_TRABAJO
        self.carpeta_trabajo = None

    # ----- estado -----
    def _poner_estado(self, estado):
        if estado != self.estado:
            self.estado = estado
            self.estado_cambiado.emit(estado)

    def esta_lista(self):
        return self.estado == ESTADO_LISTO

    def registrar(self, texto):
        self.mensaje.emit(f"[{self.nombre}] {texto}")

    # ----- a implementar por cada board -----
    def conectar(self):
        """Abre la comunicacion. Devuelve True si esta disponible."""
        raise NotImplementedError

    def esta_conectada(self):
        raise NotImplementedError

    def pedir_modos(self):
        """Pide la lista de modos; llegan por modos_recibidos."""
        raise NotImplementedError

    def seleccionar_modo(self, modo):
        """Activa un modo; su resolucion llega por dpi_recibido."""
        raise NotImplementedError

    def preparar(self, trabajo, x_cabezal_mm):
        """Ripea el trabajo para esta board. Al terminar pasa a RENDER_LISTO."""
        raise NotImplementedError

    def armar(self, posicion_eje_mm):
        """Deja la board esperando el print go. Devuelve False si no puede."""
        raise NotImplementedError

    def abortar(self):
        raise NotImplementedError

    def descartar(self):
        """Olvida el trabajo actual."""
        self.carpeta_trabajo = None
        self._poner_estado(ESTADO_SIN_TRABAJO)

    def cargar_carpeta(self, carpeta):
        """Adopta un trabajo ya ripeado. Devuelve False si no es de esta board."""
        return False

    def planos_render(self):
        """Rutas de los bitmaps por color del trabajo actual, para las previews."""
        return []

    def geometria_trabajo(self):
        """(x_mm, ancho_mm) del trabajo ripeado, o None."""
        return None

    def print_go_software(self):
        """Solo las boards que lo admiten (PMB): print go por software."""
        return False
