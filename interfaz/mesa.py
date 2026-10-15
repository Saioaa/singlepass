# -*- coding: utf-8 -*-
"""Vista de la mesa de impresion a escala.

La escena trabaja en milimetros: 1 unidad de escena = 1 mm. La vista se
ajusta al recuadro manteniendo la proporcion de la mesa, y la imagen cargada
se puede arrastrar con el raton sin salirse de la mesa.

Uso:
    self.mesa = MesaImpresion(ancho_mm, alto_mm, parent=self.ui.PMB8)
    self.mesa.posicion_cambiada.connect(self.actualizar_posicion)
    self.mesa.mostrar_imagen(pixmap, ancho_mm, alto_mm)
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

POSICION_INICIAL_MM = 0.0


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


class MesaImpresion(QGraphicsView):

    posicion_cambiada = Signal(float, float)   # x_mm, y_mm de la esquina superior izquierda

    def __init__(self, ancho_mm, alto_mm, parent=None):
        super().__init__(parent)
        self.mesa_mm = QRectF(0, 0, ancho_mm, alto_mm)
        self.item = None

        self.setScene(QGraphicsScene(self.mesa_mm, self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)

    # ===== ajuste de la vista al recuadro =====
    def _ajustar(self):
        self.fitInView(self.mesa_mm, Qt.KeepAspectRatio)

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
