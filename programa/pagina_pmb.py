# -*- coding: utf-8 -*-
"""Pagina PMB-8: modos de sistema, imagen a imprimir, ripeo y envio al cabezal.

Recibe el objeto ui ya construido, el ClientePMB y una funcion que devuelve
la posicion del primer cabezal (la conoce la pagina de programa).
Todo lo que falta por programar del PMB va aqui.

Widgets de la pagina sin funcion todavia:
    pos_x_target, pos_y_target, pos_x_real, pos_y_real, load_previews
"""

import os
import re

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import QFileDialog

import vpi

# ===== IMAGEN A IMPRIMIR =====
FILTRO_IMAGENES = "Imagenes (*.tif *.tiff *.bmp *.jpg *.jpeg *.png)"
MM_POR_PULGADA  = 25.4
GRADOS_POR_GIRO = 90
GRADOS_VUELTA   = 360
POSICION_Y_MM   = 0.0   # la hoja va siempre a la misma altura
PATRON_DPI      = r"(\d+)\s*dpi"


class PaginaPMB(QObject):

    def __init__(self, ui, pmb, posicion_cabezal, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.pmb = pmb
        self._posicion_cabezal = posicion_cabezal   # callable -> mm o None

        self.dpi_actual = None
        self.ruta_imagen = None
        self.ancho_imagen_mm = None
        self.alto_imagen_mm = None
        self.rotacion_imagen = 0
        self.espejo_x = False
        self.espejo_y = False
        self.carpeta_trabajo = None
        self.render_pendiente = None

        self.ui.txtMessage.setReadOnly(True)

        # senales del cliente PMB
        self.pmb.mensaje.connect(self.registrar)
        self.pmb.modos_recibidos.connect(self.cargar_modos)
        self.pmb.dpi_recibido.connect(self.guardar_dpi)
        self.pmb.comando_completado.connect(self.tras_completar)

        # botones de la pagina
        self.ui.btnUpdateMode.clicked.connect(self.cargar_modos_pmb)
        self.ui.systemode.currentTextChanged.connect(self.modo_seleccionado)
        self.ui.btnSelect.clicked.connect(self.seleccionar_trabajo)
        self.ui.btnPrint.clicked.connect(self.imprimir)
        self.ui.btnNewjob.clicked.connect(self.cargar_imagen)
        self.ui.btnRotate.clicked.connect(self.rotar_imagen)
        self.ui.btnMirrorX.clicked.connect(self.espejar_x)
        self.ui.btnMirrorY.clicked.connect(self.espejar_y)
        self.ui.btnRip.clicked.connect(self.generar_trabajo)
        self.ui.btn_clear.clicked.connect(self.limpiar_imagen)

    # ===== utilidades =====
    def registrar(self, texto):
        self.ui.txtMessage.append(texto)

    def entrar(self):
        """Muestra la pagina y conecta con el PMB si aun no lo esta."""
        self.ui.stackedWidget.setCurrentWidget(self.ui.PMB8)
        if not self.pmb.conectado():
            self.pmb.conectar()

    # ===== modos de sistema =====
    def cargar_modos_pmb(self):
        if not self.pmb.conectado() and not self.pmb.conectar():
            return
        self.ui.systemode.clear()
        self.pmb.pedir_modos()

    def cargar_modos(self, modos):
        self.ui.systemode.clear()
        self.ui.systemode.addItems(modos)

    def modo_seleccionado(self, modo):
        if not modo:
            return
        resolucion = re.findall(PATRON_DPI, modo, re.IGNORECASE)
        if len(resolucion) == 2:
            self.guardar_dpi(int(resolucion[0]), int(resolucion[1]))
        else:
            self.registrar(f"[PMB] No se ha podido leer la resolucion de: {modo}")
        self.pmb.pedir_info_modo(modo)

    def guardar_dpi(self, dpi_x, dpi_y):
        self.dpi_actual = (dpi_x, dpi_y)
        self.registrar(f"[PMB] Modo activo: {dpi_x} x {dpi_y} dpi")

    # ===== imagen =====
    def _mostrar_pixmap(self, pixmap):
        dpi_x, dpi_y = self.dpi_actual
        self.ancho_imagen_mm = pixmap.width() * MM_POR_PULGADA / dpi_x
        self.alto_imagen_mm = pixmap.height() * MM_POR_PULGADA / dpi_y
        self.ui.labelImage.setPixmap(pixmap.scaled(
            self.ui.labelImage.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.ui.labelImage.setAlignment(Qt.AlignCenter)
        self.ui.lblSizeValue.setText(
            f"{self.ancho_imagen_mm:.2f} mm x\n{self.alto_imagen_mm:.2f} mm")

    def cargar_imagen(self):
        """Carga la imagen a imprimir y la muestra ajustada al recuadro."""
        if self.dpi_actual is None:
            self.registrar("[PMB] Selecciona antes un modo de sistema")
            return

        ruta, _ = QFileDialog.getOpenFileName(self.ui.labelImage.window(),
                                              "Seleccionar imagen", "", FILTRO_IMAGENES)
        if not ruta:
            return

        pixmap = QPixmap(ruta)
        if pixmap.isNull():
            self.registrar(f"[PMB] No se ha podido abrir: {ruta}")
            return

        self.ruta_imagen = os.path.normpath(ruta)
        self.rotacion_imagen = 0
        self.espejo_x = False
        self.espejo_y = False
        self._mostrar_pixmap(pixmap)
        self.registrar(
            f"[PMB] Imagen: {pixmap.width()} x {pixmap.height()} px "
            f"({self.ancho_imagen_mm:.2f} x {self.alto_imagen_mm:.2f} mm)")

    def _refrescar_vista(self):
        """Redibuja la imagen aplicando rotacion y espejos."""
        if self.ruta_imagen is None:
            return
        transformacion = QTransform()
        transformacion.rotate(self.rotacion_imagen)
        transformacion.scale(-1 if self.espejo_x else 1, -1 if self.espejo_y else 1)
        pixmap = QPixmap(self.ruta_imagen).transformed(transformacion, Qt.SmoothTransformation)
        self._mostrar_pixmap(pixmap)

    def rotar_imagen(self):
        self.rotacion_imagen = (self.rotacion_imagen + GRADOS_POR_GIRO) % GRADOS_VUELTA
        self._refrescar_vista()

    def espejar_x(self):
        self.espejo_x = not self.espejo_x
        self._refrescar_vista()

    def espejar_y(self):
        self.espejo_y = not self.espejo_y
        self._refrescar_vista()

    def limpiar_imagen(self):
        """Descarta la imagen cargada y vacia el recuadro."""
        self.ruta_imagen = None
        self.ancho_imagen_mm = None
        self.alto_imagen_mm = None
        self.rotacion_imagen = 0
        self.espejo_x = False
        self.espejo_y = False
        self.ui.labelImage.clear()
        self.ui.lblSizeValue.clear()
        self.registrar("[PMB] Imagen descartada")

    # ===== trabajo (ripeo e impresion) =====
    def generar_trabajo(self):
        """Genera el VPI, lo carga en el servidor y lanza el rasterizado."""
        if self.ruta_imagen is None:
            self.registrar("[PMB] No hay ninguna imagen cargada")
            return

        posicion_x = self._posicion_cabezal()
        if posicion_x is None:
            self.registrar("[PMB] No hay ningun cabezal configurado en la pagina de programa")
            return

        try:
            ruta_vpi = vpi.generar_vpi(
                ruta_imagen=self.ruta_imagen,
                ancho_mm=self.ancho_imagen_mm,
                alto_mm=self.alto_imagen_mm,
                pos_x_mm=posicion_x,
                pos_y_mm=POSICION_Y_MM,
                rotacion=self.rotacion_imagen,
                espejo_x=self.espejo_x,
                espejo_y=self.espejo_y)
        except (OSError, ValueError) as e:
            self.registrar(f"[PMB] No se ha podido generar el VPI: {e}")
            return

        self.carpeta_trabajo = os.path.dirname(ruta_vpi)
        self.registrar(f"[PMB] Trabajo generado: {ruta_vpi}")
        self.render_pendiente = vpi.ruta_render(ruta_vpi)
        self.pmb.cargar_vpi(ruta_vpi)

    def tras_completar(self, id_comando):
        """Lanza el render cuando el servidor confirma la carga del VPI."""
        if self.render_pendiente is None:
            return
        ruta = self.render_pendiente
        self.render_pendiente = None
        self.pmb.renderizar(ruta)

    def seleccionar_trabajo(self):
        carpeta = QFileDialog.getExistingDirectory(self.ui.labelImage.window(),
                                                   "Seleccionar carpeta de trabajo")
        if not carpeta:
            return
        self.carpeta_trabajo = os.path.normpath(carpeta)
        self.registrar(f"[PMB] Trabajo: {self.carpeta_trabajo}")

    def imprimir(self):
        if self.carpeta_trabajo is None:
            self.registrar("[PMB] No hay ninguna carpeta de trabajo seleccionada")
            return
        self.pmb.imprimir(os.path.join(self.carpeta_trabajo, vpi.NOMBRE_RENDER))

    def armar_impresion(self):
        """Arma los cabezales: el PMB queda esperando la senal de print go."""
        if self.carpeta_trabajo is None:
            self.registrar("[PMB] No hay ningun trabajo rasterizado")
            return False
        self.pmb.imprimir(os.path.join(self.carpeta_trabajo, vpi.NOMBRE_RENDER))
        self.registrar("[PMB] Cabezales armados, esperando print go")
        return True
