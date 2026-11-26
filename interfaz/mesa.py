# -*- coding: utf-8 -*-
"""Vista de la mesa de impresion a escala.

La escena trabaja en milimetros: 1 unidad de escena = 1 mm. La mesa se dibuja
en blanco a la mayor escala que cabe en el recuadro, centrada; lo que sobra
del recuadro (la proporcion del recuadro no es la de la mesa) se pinta del
color del fondo de la pagina, asi los bordes de la mesa se ven y la imagen
cargada, arrastrable con el raton, llega hasta ellos.

Uso:
    self.mesa = MesaImpresion(ancho_mm, alto_mm, parent=self.ui.PMB8)
    self.mesa.posicion_cambiada.connect(self.actualizar_posicion)
    self.mesa.mostrar_imagen(pixmap, ancho_mm, alto_mm)
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QTransform
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPixmapItem, QGraphicsScene,
                               QGraphicsView)

from programa import config

POSICION_INICIAL_MM = 0.0
COLOR_MESA = QColor("#FFFFFF")
COLOR_FUERA_MESA = QColor("#3F4D4C")   # fondo de las paginas del .ui
# texto (Print Server AEWA): recuadro arrastrable y escalable por las esquinas
Z_TEXTO = 1                      # encima de la imagen
LADO_ASA_PX = 14                 # esquinas para redimensionar, en px de pantalla
COLOR_RECUADRO = "#62CBC9"
GROSOR_RECUADRO_PX = 1.5
COLOR_ASA = "#3F4D4C"
DECIMALES_PUNTOS = 1


def _limitar_a_mesa(punto, ancho_mm, alto_mm, mesa_mm):
    """Recorta la posicion para que el recuadro no salga de la mesa."""
    max_x = mesa_mm.width() - ancho_mm
    max_y = mesa_mm.height() - alto_mm
    x = min(max(punto.x(), min(0.0, max_x)), max(0.0, max_x))
    y = min(max(punto.y(), min(0.0, max_y)), max(0.0, max_y))
    return QPointF(x, y)




class ImagenMesa(QGraphicsPixmapItem):
    """Imagen arrastrable, escalada a sus dimensiones reales en mm y
    confinada dentro de la mesa."""

    def __init__(self, pixmap, ancho_mm, alto_mm, mesa_mm, al_mover):
        super().__init__(pixmap)
        self.ancho_mm = ancho_mm
        self.alto_mm = alto_mm
        self.mesa_mm = mesa_mm          # QRectF con el tamano de la mesa
        self._al_mover = al_mover       # callable(x_mm, y_mm)
        self.setFlags(QGraphicsPixmapItem.ItemIsMovable
                      | QGraphicsPixmapItem.ItemSendsGeometryChanges)
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setCursor(Qt.OpenHandCursor)
        # pixeles -> mm (dpi distintos en cada eje, por eso dos factores)
        self.setTransform(QTransform().scale(ancho_mm / pixmap.width(),
                                             alto_mm / pixmap.height()))

    def _limitar(self, punto):
        """Recorta la posicion para que la imagen no salga de la mesa."""
        max_x = self.mesa_mm.width() - self.ancho_mm
        max_y = self.mesa_mm.height() - self.alto_mm
        x = min(max(punto.x(), min(0.0, max_x)), max(0.0, max_x))
        y = min(max(punto.y(), min(0.0, max_y)), max(0.0, max_y))
        return QPointF(x, y)

    def itemChange(self, cambio, valor):
        if cambio == QGraphicsPixmapItem.ItemPositionChange:
            return self._limitar(valor)
        if cambio == QGraphicsPixmapItem.ItemPositionHasChanged:
            self._al_mover(valor.x(), valor.y())
        return super().itemChange(cambio, valor)

    def mousePressEvent(self, evento):
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(evento)


class TextoMesa(QGraphicsItem):
    """Texto (trazado en mm) arrastrable y escalable por las esquinas, confinado
    en la mesa. al_cambiar(x_mm, y_mm, puntos): al moverlo y al soltar una esquina.
    al_borrar(): Supr con el texto seleccionado."""

    def __init__(self, trazado_mm, ancho_mm, alto_mm, puntos, mesa_mm, al_cambiar, al_borrar):
        super().__init__()
        self._trazado = trazado_mm         # a puntos_base
        self._ancho_base = ancho_mm
        self._alto_base = alto_mm
        self._puntos_base = puntos
        self.puntos = puntos
        self.mesa_mm = mesa_mm
        self._al_cambiar = al_cambiar
        self._al_borrar = al_borrar
        self._ancla = None                 # esquina fija mientras se redimensiona (escena)
        self._sentido = None               # (+1/-1, +1/-1) de la esquina arrastrada
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges
                      | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.setZValue(Z_TEXTO)
        self.setCursor(Qt.OpenHandCursor)

    # ===== tamano =====
    @property
    def escala(self):
        return self.puntos / self._puntos_base

    @property
    def ancho_mm(self):
        return self._ancho_base * self.escala

    @property
    def alto_mm(self):
        return self._alto_base * self.escala

    def _lado_asa_mm(self):
        vistas = self.scene().views() if self.scene() else []
        escala_vista = vistas[0].transform().m11() if vistas else 1.0
        return LADO_ASA_PX / escala_vista

    def actualizar_vista(self):
        """La vista ha cambiado de escala: las esquinas tienen tamano en px."""
        self.prepareGeometryChange()

    def boundingRect(self):
        margen = self._lado_asa_mm()
        return QRectF(-margen, -margen, self.ancho_mm + 2 * margen, self.alto_mm + 2 * margen)

    def _esquinas(self):
        w, h = self.ancho_mm, self.alto_mm
        return {(-1, -1): QPointF(0, 0), (1, -1): QPointF(w, 0),
                (-1, 1): QPointF(0, h), (1, 1): QPointF(w, h)}

    def _esquina_en(self, punto):
        """Sentido de la esquina bajo el punto (coordenadas del item), o None."""
        lado = self._lado_asa_mm()
        for sentido, esquina in self._esquinas().items():
            if abs(punto.x() - esquina.x()) <= lado and abs(punto.y() - esquina.y()) <= lado:
                return sentido
        return None

    # ===== dibujo =====
    def paint(self, pintor, _opcion, _widget=None):
        pintor.save()
        pintor.scale(self.escala, self.escala)
        pintor.fillPath(self._trazado, QColor(config.TEXTO_COLOR))
        pintor.restore()
        pluma = QPen(QColor(COLOR_RECUADRO), GROSOR_RECUADRO_PX, Qt.DashLine)
        pluma.setCosmetic(True)
        pintor.setPen(pluma)
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRect(QRectF(0, 0, self.ancho_mm, self.alto_mm))
        lado = self._lado_asa_mm()
        pluma.setStyle(Qt.SolidLine)
        pintor.setPen(pluma)
        pintor.setBrush(QBrush(QColor(COLOR_ASA)))
        for esquina in self._esquinas().values():
            pintor.drawRect(QRectF(esquina.x() - lado / 2, esquina.y() - lado / 2, lado, lado))

    # ===== mover =====
    def itemChange(self, cambio, valor):
        if cambio == QGraphicsItem.ItemPositionChange:
            return _limitar_a_mesa(valor, self.ancho_mm, self.alto_mm, self.mesa_mm)
        if cambio == QGraphicsItem.ItemPositionHasChanged and self._ancla is None:
            self._al_cambiar(valor.x(), valor.y(), self.puntos)
        return super().itemChange(cambio, valor)

    def hoverMoveEvent(self, evento):
        sentido = self._esquina_en(evento.pos())
        if sentido is None:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.SizeFDiagCursor if sentido[0] == sentido[1] else Qt.SizeBDiagCursor)
        super().hoverMoveEvent(evento)

    # ===== quitar con Supr =====
    def keyPressEvent(self, evento):
        if evento.key() == Qt.Key_Delete:
            evento.accept()
            self._al_borrar()
            return
        super().keyPressEvent(evento)

    # ===== redimensionar por las esquinas =====
    def mousePressEvent(self, evento):
        self.setFocus()                    # para recibir Supr
        sentido = self._esquina_en(evento.pos())
        if sentido is None or evento.button() != Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            super().mousePressEvent(evento)
            return
        opuesta = self._esquinas()[(-sentido[0], -sentido[1])]
        self._ancla = self.mapToScene(opuesta)
        self._sentido = sentido
        evento.accept()

    def mouseMoveEvent(self, evento):
        if self._ancla is None:
            super().mouseMoveEvent(evento)
            return
        sx, sy = self._sentido
        punto = evento.scenePos()
        # escala que pide el raton: la mayor de las dos direcciones
        escala = max(sx * (punto.x() - self._ancla.x()) / self._ancho_base,
                     sy * (punto.y() - self._ancla.y()) / self._alto_base)
        # sin salir de la mesa por el lado de la esquina arrastrada
        hueco_x = self.mesa_mm.width() - self._ancla.x() if sx > 0 else self._ancla.x()
        hueco_y = self.mesa_mm.height() - self._ancla.y() if sy > 0 else self._ancla.y()
        escala = min(escala, hueco_x / self._ancho_base, hueco_y / self._alto_base)
        puntos = self._puntos_base * escala
        puntos = min(max(puntos, config.TEXTO_PUNTOS_MIN), config.TEXTO_PUNTOS_MAX)
        self.prepareGeometryChange()
        self.puntos = round(puntos, DECIMALES_PUNTOS)
        x = self._ancla.x() - (self.ancho_mm if sx < 0 else 0.0)
        y = self._ancla.y() - (self.alto_mm if sy < 0 else 0.0)
        self.setPos(x, y)
        evento.accept()

    def mouseReleaseEvent(self, evento):
        self.setCursor(Qt.OpenHandCursor)
        if self._ancla is None:
            super().mouseReleaseEvent(evento)
            return
        self._ancla = None
        self._sentido = None
        self._al_cambiar(self.pos().x(), self.pos().y(), self.puntos)
        evento.accept()


class MesaImpresion(QGraphicsView):

    posicion_cambiada = Signal(float, float)   # x_mm, y_mm de la esquina superior izquierda
    texto_cambiado = Signal(float, float, float)   # x_mm, y_mm, puntos del texto
    texto_borrado = Signal()                       # Supr con el texto seleccionado

    def __init__(self, ancho_mm, alto_mm, parent=None):
        super().__init__(parent)
        self.mesa_mm = QRectF(0, 0, ancho_mm, alto_mm)
        self.item = None
        self.texto = None

        self.setScene(QGraphicsScene(self.mesa_mm, self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)

    # ===== ajuste de la vista al recuadro =====
    def _ajustar(self):
        """Mayor escala con la que la mesa entera cabe en el recuadro, sin los
        margenes que anade fitInView; la mesa queda centrada."""
        recuadro = self.viewport().rect()
        if recuadro.isEmpty():
            return
        escala = min(recuadro.width() / self.mesa_mm.width(),
                     recuadro.height() / self.mesa_mm.height())
        self.resetTransform()
        self.scale(escala, escala)
        self.centerOn(self.mesa_mm.center())
        if self.texto is not None:
            self.texto.actualizar_vista()

    def drawBackground(self, pintor, rect):
        pintor.fillRect(rect, COLOR_FUERA_MESA)
        pintor.fillRect(self.mesa_mm.intersected(rect), COLOR_MESA)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._ajustar()

    def showEvent(self, evento):
        super().showEvent(evento)
        self._ajustar()

    # ===== imagen =====
    def tiene_imagen(self):
        return self.item is not None

    def mostrar_imagen(self, pixmap, ancho_mm, alto_mm, x_mm=None, y_mm=None):
        """Coloca la imagen en la mesa. Si no se indica posicion, conserva la
        de la imagen anterior (util al rotar o espejar)."""
        if x_mm is None or y_mm is None:
            if self.item is not None:
                x_mm, y_mm = self.item.pos().x(), self.item.pos().y()
            else:
                x_mm, y_mm = POSICION_INICIAL_MM, POSICION_INICIAL_MM
        self.limpiar()
        self.item = ImagenMesa(pixmap, ancho_mm, alto_mm, self.mesa_mm,
                               self.posicion_cambiada.emit)
        self.scene().addItem(self.item)
        self.item.setPos(x_mm, y_mm)          # pasa por _limitar y emite la posicion
        self.posicion_cambiada.emit(self.item.pos().x(), self.item.pos().y())

    def mover_imagen(self, x_mm, y_mm):
        if self.item is not None:
            self.item.setPos(x_mm, y_mm)

    def posicion_imagen_mm(self):
        """(x_mm, y_mm) de la esquina superior izquierda, o None si no hay imagen."""
        if self.item is None:
            return None
        return self.item.pos().x(), self.item.pos().y()

    def limpiar(self):
        if self.item is not None:
            self.scene().removeItem(self.item)
            self.item = None

    # ===== texto =====
    def tiene_texto(self):
        return self.texto is not None

    def mostrar_texto(self, trazado_mm, ancho_mm, alto_mm, puntos, x_mm=None, y_mm=None):
        """Pone (o sustituye) el texto. Sin posicion conserva la del anterior."""
        if (x_mm is None or y_mm is None) and self.texto is not None:
            x_mm, y_mm = self.texto.pos().x(), self.texto.pos().y()
        elif x_mm is None or y_mm is None:
            x_mm, y_mm = POSICION_INICIAL_MM, POSICION_INICIAL_MM
        self.quitar_texto()
        self.texto = TextoMesa(trazado_mm, ancho_mm, alto_mm, puntos, self.mesa_mm,
                               self.texto_cambiado.emit, self.texto_borrado.emit)
        self.scene().addItem(self.texto)
        self.texto.setPos(x_mm, y_mm)
        self.texto_cambiado.emit(self.texto.pos().x(), self.texto.pos().y(), self.texto.puntos)

    def geometria_texto(self):
        """(x_mm, y_mm, ancho_mm, alto_mm, puntos) del texto, o None."""
        if self.texto is None:
            return None
        t = self.texto
        return t.pos().x(), t.pos().y(), t.ancho_mm, t.alto_mm, t.puntos

    def quitar_texto(self):
        if self.texto is not None:
            self.scene().removeItem(self.texto)
            self.texto = None
