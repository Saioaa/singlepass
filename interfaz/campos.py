# -*- coding: utf-8 -*-
"""Utilidades comunes de los campos de la interfaz.

poner_sufijo: texto fijo (unidades, %) dentro de un QLineEdit, a la derecha.
No se puede borrar ni seleccionar y convive con el numero: se reserva su ancho
como margen de texto del campo (tambien tras reescalar la interfaz).
"""

import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel

COLOR_SUFIJO = "#555555"
SEPARACION_SUFIJO_PX = 6
PATRON_TAMANO_FUENTE = re.compile(r"font-size:\s*(\d+px)")
PATRON_PADDING = re.compile(r"padding:\s*(\d+)px")
# el .ui pone la fuente por hoja de estilo (font-family: nunito, font-size: Npx);
# el sufijo copia el tamano del campo y hereda la familia
ESTILO_SUFIJO = ("background: transparent; border: none; padding: 0px; "
                 "color: {color}; font-size: {tamano};")
TAMANO_FUENTE_POR_DEFECTO = "16px"
PADDING_POR_DEFECTO_PX = 10
NOMBRE_OBJETO_SUFIJO = "sufijo"


class _AjusteSufijo(QObject):
    """Reserva a la derecha del campo el ancho del sufijo para que el numero
    no se escriba debajo (tambien tras escalar la interfaz)."""

    def __init__(self, campo, sufijo):
        super().__init__(campo)
        self._campo = campo
        self._sufijo = sufijo
        campo.installEventFilter(self)
        self._ajustar()

    def eventFilter(self, objeto, evento):
        if evento.type() in (QEvent.Resize, QEvent.StyleChange, QEvent.Show):
            self._ajustar()
        return False

    def _ajustar(self):
        margenes = self._campo.textMargins()
        ancho = self._sufijo.sizeHint().width() + SEPARACION_SUFIJO_PX
        if margenes.right() != ancho:
            self._campo.setTextMargins(margenes.left(), margenes.top(), ancho, margenes.bottom())


def poner_sufijo(campo, texto, color=COLOR_SUFIJO):
    """Texto fijo a la derecha dentro de un QLineEdit (unidades, %)."""
    hoja = campo.styleSheet()
    tamano = PATRON_TAMANO_FUENTE.search(hoja)
    padding = PATRON_PADDING.search(hoja)
    relleno = int(padding.group(1)) if padding else PADDING_POR_DEFECTO_PX

    sufijo = QLabel(texto, campo)
    sufijo.setObjectName(NOMBRE_OBJETO_SUFIJO)
    sufijo.setAttribute(Qt.WA_TransparentForMouseEvents)
    sufijo.setStyleSheet(ESTILO_SUFIJO.format(
        color=color, tamano=tamano.group(1) if tamano else TAMANO_FUENTE_POR_DEFECTO))

    disposicion = QHBoxLayout(campo)
    disposicion.setContentsMargins(0, 0, relleno, 0)
    disposicion.addStretch()
    disposicion.addWidget(sufijo)
    campo.setPlaceholderText("")
    _AjusteSufijo(campo, sufijo)
    return sufijo
