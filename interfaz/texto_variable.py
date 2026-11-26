# -*- coding: utf-8 -*-
"""Ventana de "Insertar Texto" (boton texto_variable de Print Server AEWA). De
la app MBD-F-500.

Texto libre y casillas para anadir debajo los parametros del trabajo
(resolucion, velocidad, curado); cada casilla muestra el valor que se
imprimiria ahora. El tamano no se elige aqui: el texto entra a
config.TEXTO_PUNTOS_INICIAL y se ajusta tirando de las esquinas en la mesa.

editar() devuelve (accion, contenido, parametros), accion una de ACEPTAR,
QUITAR o CANCELAR.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QVBoxLayout)

from programa.aewa.texto_trabajo import NOMBRES_PARAMETROS, PARAMETROS, texto_parametro

ACEPTAR = "aceptar"
QUITAR = "quitar"
CANCELAR = "cancelar"

TITULO = "INSERTAR TEXTO"
TEXTO_ACEPTAR = "INSERTAR"
TEXTO_ACTUALIZAR = "ACTUALIZAR"
TEXTO_QUITAR = "QUITAR TEXTO"
TEXTO_CANCELAR = "CANCELAR"
TEXTO_VACIO = "Escriba un texto o marque algún parámetro"
ANCHO_CAMPO_PX = 700
ALTO_CAMPO_PX = 200
MARGEN_PX = 40
ESPACIADO_PX = 20
ESTILO = """
QDialog { background-color: #3F4D4C; border: 4px solid #62CBC9; border-radius: 16px; }
QDialog QLabel { background-color: transparent; border: none; font-family: nunito; }
QLabel#titulo { color: #62CBC9; font-size: 30px; font-weight: bold; }
QLabel#error { color: #FF5252; font-size: 18px; font-weight: bold; }
QPlainTextEdit { background-color: #FFFFFF; color: #000000; border: 2px solid #62CBC9;
                 border-radius: 5px; padding: 8px; font-size: 24px; font-family: nunito; }
QCheckBox { background-color: transparent; color: #FFFFFF; font-size: 22px; font-family: nunito; spacing: 14px; }
QCheckBox::indicator { width: 26px; height: 26px; border: 2px solid #62CBC9;
                       border-radius: 5px; background-color: #FFFFFF; }
QCheckBox::indicator:checked { background-color: #62CBC9; border-color: #FFFFFF; }
QPushButton { background-color: #62CBC9; color: #FFFFFF; border: 2px solid #333333;
              border-radius: 5px; font-size: 20px; font-family: nunito; font-weight: bold;
              min-height: 60px; padding: 0 20px; }
QPushButton:pressed { background-color: rgb(206, 255, 252); color: #333333; }
QPushButton#cancelar { background-color: #555555; }
QPushButton#quitar { background-color: #E30000; }
"""


class VentanaTexto(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet(ESTILO)
        self._accion = CANCELAR

        titulo = QLabel(TITULO)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        self.campo = QPlainTextEdit()
        self.campo.setFixedSize(ANCHO_CAMPO_PX, ALTO_CAMPO_PX)
        self.casillas = {clave: QCheckBox() for clave in PARAMETROS}
        self.error = QLabel()
        self.error.setObjectName("error")

        self.cancelar_boton = QPushButton(TEXTO_CANCELAR)
        self.cancelar_boton.setObjectName("cancelar")
        self.cancelar_boton.clicked.connect(lambda: self._terminar(CANCELAR))
        self.quitar_boton = QPushButton(TEXTO_QUITAR)
        self.quitar_boton.setObjectName("quitar")
        self.quitar_boton.clicked.connect(lambda: self._terminar(QUITAR))
        self.aceptar_boton = QPushButton()
        self.aceptar_boton.setObjectName("aceptar")
        self.aceptar_boton.clicked.connect(self._aceptar)

        botones = QHBoxLayout()
        botones.addWidget(self.cancelar_boton)
        botones.addWidget(self.quitar_boton)
        botones.addWidget(self.aceptar_boton)

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(MARGEN_PX, MARGEN_PX, MARGEN_PX, MARGEN_PX)
        disposicion.setSpacing(ESPACIADO_PX)
        disposicion.addWidget(titulo)
        disposicion.addWidget(self.campo)
        for clave in PARAMETROS:
            disposicion.addWidget(self.casillas[clave])
        disposicion.addWidget(self.error)
        disposicion.addLayout(botones)

    def editar(self, contenido, parametros, valores, existe):
        """contenido y parametros: los del texto actual (vacios si no hay).
        valores: los de texto_trabajo.texto_parametro. existe: ya hay texto en la mesa."""
        self.campo.setPlainText(contenido)
        for clave, casilla in self.casillas.items():
            casilla.setText(f"{NOMBRES_PARAMETROS[clave]}:  {texto_parametro(clave, valores)}")
            casilla.setChecked(clave in parametros)
        self.error.clear()
        self.error.hide()
        self.quitar_boton.setVisible(existe)
        self.aceptar_boton.setText(TEXTO_ACTUALIZAR if existe else TEXTO_ACEPTAR)
        self._accion = CANCELAR
        self.adjustSize()
        pantalla = self.parent().screen().availableGeometry()
        self.move(pantalla.center() - self.rect().center())
        self.campo.setFocus()
        self.exec()
        return self._accion, self.campo.toPlainText(), self.parametros()

    def parametros(self):
        return [clave for clave in PARAMETROS if self.casillas[clave].isChecked()]

    def _aceptar(self):
        if not self.campo.toPlainText().strip() and not self.parametros():
            self.error.setText(TEXTO_VACIO)
            self.error.show()
            self.adjustSize()
            return
        self._terminar(ACEPTAR)

    def _terminar(self, accion):
        self._accion = accion
        if accion == CANCELAR:
            self.reject()
        else:
            self.accept()
