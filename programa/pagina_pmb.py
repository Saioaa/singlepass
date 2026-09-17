# -*- coding: utf-8 -*-
"""Pagina PMB-8: modos de sistema, imagen a imprimir, ripeo y envio al cabezal.

Recibe el objeto ui ya construido, el ClientePMB y una funcion que devuelve
la posicion del primer cabezal (la conoce la pagina de programa).
Todo lo que falta por programar del PMB va aqui.

El recuadro de imagen (labelImage en el .ui) se sustituye en tiempo de
ejecucion por una MesaImpresion (mesa.py) con la misma geometria y estilo.

El boton Print cambia de aspecto segun el estado del trabajo:
    sin trabajo      -> aspecto del disenador, "Print"
    render listo     -> parpadea en naranja, "Print"
    armando          -> naranja fijo, "Arming..."
    listo            -> verde fijo, "Ready to Print"

Widgets de la pagina sin funcion todavia:
    load_previews, rip1..rip4
"""

import os
import re

from PySide6.QtCore import QLocale, QObject, Qt, QTimer
from PySide6.QtGui import QDoubleValidator, QPixmap, QTransform
from PySide6.QtWidgets import QFileDialog

import config
import vpi
from mesa import MesaImpresion

# ===== IMAGEN A IMPRIMIR =====
FILTRO_IMAGENES = "Imagenes (*.tif *.tiff *.bmp *.jpg *.jpeg *.png)"
MM_POR_PULGADA  = 25.4
GRADOS_POR_GIRO = 90
GRADOS_VUELTA   = 360
PATRON_DPI      = r"(\d+)\s*dpi"

# ===== ESTADOS DEL BOTON PRINT =====
ESTADO_SIN_TRABAJO  = "sin_trabajo"
ESTADO_RENDER_LISTO = "render_listo"
ESTADO_ARMANDO      = "armando"
ESTADO_LISTO        = "listo"

TEXTO_PRINT   = "Print"
TEXTO_ARMANDO = "Arming..."
TEXTO_LISTO   = "Ready to Print"
COLOR_AVISO   = "#F39C12"   # naranja: hay render, falta armar
COLOR_LISTO   = "#27AE60"   # verde: PMB armado
PERIODO_PARPADEO_MS = 500
DECIMALES_POSICION = 2
POSICION_INICIAL_X_MM = 0.0   # donde aparece una imagen recien cargada
POSICION_INICIAL_Y_MM = 0.0


def calcular_offset_x(x_cabezal_mm, x_imagen_mm):
    """Distancia que recorre el carro desde el PULSE hasta que el borde de la
    imagen pasa bajo el cabezal."""
    return x_cabezal_mm - x_imagen_mm - config.POSICION_PULSE_MM


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
        self._tras_completar = None   # accion a ejecutar cuando el PMB confirme el comando en curso

        # estado del boton Print
        self._estilo_print_base = self.ui.btnPrint.styleSheet()
        self._parpadeo_encendido = False
        self.timer_parpadeo = QTimer(self)
        self.timer_parpadeo.setInterval(PERIODO_PARPADEO_MS)
        self.timer_parpadeo.timeout.connect(self._parpadear)
        self.estado = ESTADO_SIN_TRABAJO

        self.ui.txtMessage.setReadOnly(True)

        # mesa de impresion en lugar del QLabel del disenador
        self.mesa = MesaImpresion(config.MESA_ANCHO_MM, config.MESA_ALTO_MM, self.ui.PMB8)
        self.mesa.setGeometry(self.ui.labelImage.geometry())
        self.mesa.setStyleSheet(self.ui.labelImage.styleSheet())
        self.ui.labelImage.hide()
        self.mesa.posicion_cambiada.connect(self.actualizar_posicion)

        # posicion objetivo escrita a mano
        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))
        self.ui.pos_x_target.setValidator(validador)
        self.ui.pos_y_target.setValidator(validador)
        self.ui.pos_x_target.editingFinished.connect(self.ir_a_posicion)
        self.ui.pos_y_target.editingFinished.connect(self.ir_a_posicion)

        # senales del cliente PMB
        self.pmb.mensaje.connect(self.registrar)
        self.pmb.modos_recibidos.connect(self.cargar_modos)
        self.pmb.dpi_recibido.connect(self.guardar_dpi)
        self.pmb.comando_completado.connect(self.tras_completar)
        self.pmb.comando_fallido.connect(self.tras_fallo)
        self.pmb.impresion_terminada.connect(self.tras_fin_impresion)
        self.pmb.listo_para_imprimir.connect(self._armado)
        self.pmb.conexion_perdida.connect(lambda _motivo: self._poner_estado(ESTADO_SIN_TRABAJO))

        # botones de la pagina
        self.ui.btnUpdateMode.clicked.connect(self.cargar_modos_pmb)
        self.ui.systemode.currentTextChanged.connect(self.modo_seleccionado)
        self.ui.btnSelect.clicked.connect(self.seleccionar_trabajo)
        self.ui.btnPrint.clicked.connect(self.imprimir)
        self.ui.btnAbort.clicked.connect(self.abortar)
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

    # ===== posicion en la mesa =====
    def actualizar_posicion(self, x_mm, y_mm):
        """La mesa avisa cada vez que la imagen se mueve."""
        self.ui.pos_x_real.setText(f"{x_mm:.{DECIMALES_POSICION}f}")
        self.ui.pos_y_real.setText(f"{y_mm:.{DECIMALES_POSICION}f}")

    def ir_a_posicion(self):
        """Mueve la imagen a la posicion escrita en los campos objetivo."""
        posicion = self.mesa.posicion_imagen_mm()
        if posicion is None:
            return
        x_mm, y_mm = posicion
        try:
            if self.ui.pos_x_target.text():
                x_mm = float(self.ui.pos_x_target.text())
            if self.ui.pos_y_target.text():
                y_mm = float(self.ui.pos_y_target.text())
        except ValueError:
            return
        self.mesa.mover_imagen(x_mm, y_mm)

    # ===== imagen =====
    def _mostrar_pixmap(self, pixmap, x_mm=None, y_mm=None):
        dpi_x, dpi_y = self.dpi_actual
        self.ancho_imagen_mm = pixmap.width() * MM_POR_PULGADA / dpi_x
        self.alto_imagen_mm = pixmap.height() * MM_POR_PULGADA / dpi_y
        self.mesa.mostrar_imagen(pixmap, self.ancho_imagen_mm, self.alto_imagen_mm, x_mm, y_mm)
        self.ui.lblSizeValue.setText(
            f"{self.ancho_imagen_mm:.2f} mm x\n{self.alto_imagen_mm:.2f} mm")

    def cargar_imagen(self):
        """Carga la imagen a imprimir y la muestra ajustada al recuadro."""
        if self.dpi_actual is None:
            self.registrar("[PMB] Selecciona antes un modo de sistema")
            return

        ruta, _ = QFileDialog.getOpenFileName(self.mesa.window(),
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
        self._mostrar_pixmap(pixmap, POSICION_INICIAL_X_MM, POSICION_INICIAL_Y_MM)
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
        self.mesa.limpiar()
        self.ui.lblSizeValue.clear()
        self.ui.pos_x_real.clear()
        self.ui.pos_y_real.clear()
        self._poner_estado(ESTADO_SIN_TRABAJO)
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

        x_mesa_mm, y_mesa_mm = self.mesa.posicion_imagen_mm()
        offset_x_mm = calcular_offset_x(posicion_x, x_mesa_mm)
        self.registrar(f"[PMB] Imagen en mesa: X={x_mesa_mm:.{DECIMALES_POSICION}f} mm, "
                       f"Y={y_mesa_mm:.{DECIMALES_POSICION}f} mm; "
                       f"cabezal a {posicion_x:.{DECIMALES_POSICION}f} mm -> "
                       f"{config.PARAMETRO_OFFSET_X} = {offset_x_mm:.{DECIMALES_POSICION}f} mm")

        try:
            ruta_vpi = vpi.generar_vpi(
                ruta_imagen=self.ruta_imagen,
                ancho_mm=self.ancho_imagen_mm,
                alto_mm=self.alto_imagen_mm,
                pos_y_mm=y_mesa_mm,
                offset_x_mm=offset_x_mm,
                x_imagen_mm=x_mesa_mm,
                x_cabezal_mm=posicion_x,
                rotacion=self.rotacion_imagen,
                espejo_x=self.espejo_x,
                espejo_y=self.espejo_y)
        except (OSError, ValueError) as e:
            self.registrar(f"[PMB] No se ha podido generar el VPI: {e}")
            return

        self.carpeta_trabajo = os.path.dirname(ruta_vpi)
        self.registrar(f"[PMB] Trabajo generado: {ruta_vpi}")
        ruta_bmp = vpi.ruta_render(ruta_vpi)
        self._poner_estado(ESTADO_SIN_TRABAJO)
        self._encadenar(self._lanzar_render, ruta_bmp)
        self.pmb.cargar_vpi(ruta_vpi)

    def _lanzar_render(self, ruta_bmp):
        self._encadenar(self._render_listo)
        self.pmb.renderizar(ruta_bmp)

    def _render_listo(self):
        self.registrar("[PMB] Render terminado, listo para armar")
        self._poner_estado(ESTADO_RENDER_LISTO)

    # ===== estado del boton Print =====
    def _pintar_print(self, color=None, texto=TEXTO_PRINT):
        hoja = self._estilo_print_base
        if color is not None:
            hoja += f"\nQPushButton {{ background-color: {color}; }}"
        self.ui.btnPrint.setStyleSheet(hoja)
        self.ui.btnPrint.setText(texto)

    def _parpadear(self):
        self._parpadeo_encendido = not self._parpadeo_encendido
        self._pintar_print(COLOR_AVISO if self._parpadeo_encendido else None)

    def _poner_estado(self, estado):
        self.estado = estado
        self.timer_parpadeo.stop()
        if estado == ESTADO_RENDER_LISTO:
            self._pintar_print()
            self._parpadeo_encendido = False
            self.timer_parpadeo.start()
        elif estado == ESTADO_ARMANDO:
            self._pintar_print(COLOR_AVISO, TEXTO_ARMANDO)
        elif estado == ESTADO_LISTO:
            self._pintar_print(COLOR_LISTO, TEXTO_LISTO)
        else:
            self._pintar_print()

    def tras_fallo(self, id_comando, codigo):
        """Un comando ha fallado: se descarta lo encadenado y se vuelve al estado anterior."""
        self._tras_completar = None
        if self.estado == ESTADO_ARMANDO:
            self._poner_estado(ESTADO_RENDER_LISTO)

    def tras_fin_impresion(self):
        """El PMB ha terminado de imprimir (I,<id>,EP): el trabajo sigue disponible."""
        self.registrar("[PMB] Fin de impresion")
        self._poner_estado(ESTADO_RENDER_LISTO)

    def abortar(self):
        if self.pmb.abortar_impresion():
            self._tras_completar = None
            self._poner_estado(ESTADO_RENDER_LISTO if self.carpeta_trabajo else ESTADO_SIN_TRABAJO)

    # ===== encadenado de comandos =====
    def _encadenar(self, accion, *argumentos):
        """Registra la accion que se ejecutara cuando el PMB complete el siguiente comando."""
        self._tras_completar = (accion, argumentos)

    def tras_completar(self, id_comando):
        """El PMB ha completado un comando: ejecutar la accion encadenada, si la hay."""
        if self._tras_completar is None:
            return
        accion, argumentos = self._tras_completar
        self._tras_completar = None
        accion(*argumentos)

    def _enviar_offset_y_luego(self, accion):
        """Aplica el XOffset del trabajo y, cuando el Print Controller lo confirme, ejecuta accion.
        Devuelve False si el trabajo no tiene offset guardado."""
        offset_x_mm = vpi.leer_offset_x(self.carpeta_trabajo)
        if offset_x_mm is None:
            self.registrar("[PMB] El trabajo no tiene offset X guardado (falta position_x.json)")
            return False
        self.registrar(f"[PMB] {config.PARAMETRO_OFFSET_X} = {offset_x_mm:.{DECIMALES_POSICION}f} mm")
        self._encadenar(accion)
        self.pmb.cambiar_parametro_pc(config.PARAMETRO_OFFSET_X, offset_x_mm)
        return True

    def seleccionar_trabajo(self):
        carpeta = QFileDialog.getExistingDirectory(self.mesa.window(),
                                                   "Seleccionar carpeta de trabajo")
        if not carpeta:
            return
        self.carpeta_trabajo = os.path.normpath(carpeta)
        self.registrar(f"[PMB] Trabajo: {self.carpeta_trabajo}")
        self._poner_estado(ESTADO_RENDER_LISTO)

    def _ruta_bmp(self):
        return os.path.join(self.carpeta_trabajo, vpi.NOMBRE_RENDER)

    def imprimir(self):
        """Boton Print: arma el PMB (XOffset + P,P). La mesa la mueve la pagina Programa."""
        if self.carpeta_trabajo is None:
            self.registrar("[PMB] No hay ninguna carpeta de trabajo seleccionada")
            return
        self.armar_impresion()

    def armar_impresion(self):
        """Aplica el XOffset y arma los cabezales: el PMB queda esperando el print go."""
        if self.carpeta_trabajo is None:
            self.registrar("[PMB] No hay ningun trabajo rasterizado")
            return False
        if self.estado == ESTADO_LISTO:
            return True   # ya armado, no repetir P,P (daria -201 Print Controller busy)
        self._poner_estado(ESTADO_ARMANDO)
        if not self._enviar_offset_y_luego(self._enviar_print):
            self._poner_estado(ESTADO_RENDER_LISTO)
            return False
        return True

    def _enviar_print(self):
        # P,P no completa hasta el FIN de la impresion: el "listo" llega por I,<id>,RTP
        self.pmb.imprimir(self._ruta_bmp())

    def _armado(self):
        if self.estado != ESTADO_ARMANDO:
            return
        self.registrar("[PMB] Cabezales armados, esperando print go")
        self._poner_estado(ESTADO_LISTO)

    def esta_lista(self):
        """True si el PMB esta armado y solo espera el print go."""
        return self.estado == ESTADO_LISTO
