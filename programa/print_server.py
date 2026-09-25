# -*- coding: utf-8 -*-
"""Pagina Print Server: imagen, colocacion en la mesa, modos, ripeo y armado
de todas las boards de impresion activas en la pagina Programa.

No habla ningun protocolo: cada board (board_pmb.py, epson.py...) implementa
la interfaz de board.py. La pagina reparte el mismo Trabajo a cada board
activa con la posicion de su cabezal en la barra, y el boton Print refleja
el estado conjunto: verde solo cuando todas estan armadas.

Widgets del .ui:
    pagina:  print_server (o PMB8, nombre antiguo)
    modos:   btnUpdateMode (pide a todas las activas) y un combo por board,
             segun COMBOS_MODO; un combo se habilita solo si su board esta activa
    imagen:  btnNewjob, btnRotate, btnMirrorX, btnMirrorY, btn_clear, labelImage (-> MesaImpresion),
             lblSizeValue, pos_x_real/pos_y_real, pos_x_target/pos_y_target
    trabajo: btnRip (ripear en todas), btnSelect (carpeta), btnPrint (armar), btnAbort
    previews: rip1..rip4
"""

import os
import re
import time

from PySide6.QtCore import QLocale, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QFileDialog

import config
from board import (ESTADO_ARMANDO, ESTADO_LISTO, ESTADO_RENDER_LISTO, ESTADO_SIN_TRABAJO,
                   ORDEN_ESTADOS, Trabajo)
from mesa import MesaImpresion

# ===== WIDGETS =====
NOMBRES_PAGINA = ("print_server", "PMB8")           # objectName de la pagina, nuevo y antiguo
COMBOS_MODO = {"PMB": "systemode", "EPSON": "systemode_epson"}   # board.nombre -> combo del .ui
NOMBRES_REGISTRO = ("txtMessage", "txtMessage_2", "txtMessage_3")

# ===== IMAGEN A IMPRIMIR =====
FILTRO_IMAGENES = "Imagenes (*.tif *.tiff *.bmp *.jpg *.jpeg *.png)"
MM_POR_PULGADA  = 25.4
GRADOS_POR_GIRO = 90
GRADOS_VUELTA   = 360
PATRON_DPI      = r"(\d+)\s*dpi"
POSICION_INICIAL_X_MM = 0.0   # donde aparece una imagen recien cargada
POSICION_INICIAL_Y_MM = 0.0
DECIMALES_POSICION = 2

# ===== PREVIEWS DE LOS PLANOS DE COLOR =====
COLOR_FONDO_PREVIEW = "white"
COLORES_PLANOS = ("#00AEEF", "#EC008C", "#FFF100", "#000000")   # CMYK, orden del render

# ===== REGISTRO Y BOTON PRINT =====
VENTANA_DUPLICADOS_S = 2.0    # un mensaje identico al anterior dentro de esta ventana no se repite
TEXTO_PRINT   = "Print"
TEXTO_LISTO   = "Ready\nto\nPrint"
COLOR_AVISO   = "#F39C12"     # naranja: hay render, falta armar
COLOR_LISTO   = "#27AE60"     # verde: todas las boards armadas
PERIODO_PARPADEO_MS = 500


class PrintServer(QObject):

    def __init__(self, ui, boards, cabezales_activos, posicion_eje, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.boards = list(boards)                      # todas las boards conocidas
        self._cabezales_activos = cabezales_activos     # callable -> [(tipo_modulo, x_mm), ...]
        self._posicion_eje = posicion_eje               # callable -> mm | None
        self._board_por_tipo = {tipo: b for b in self.boards for tipo in b.tipos_modulo}

        self.dpi_actual = None
        self.ruta_imagen = None
        self.ancho_imagen_mm = None
        self.alto_imagen_mm = None
        self.rotacion_imagen = 0
        self.espejo_x = False
        self.espejo_y = False
        self._ultimo_mensaje = ("", 0.0)

        self.pagina = next(getattr(self.ui, n) for n in NOMBRES_PAGINA if hasattr(self.ui, n))
        self._registros = [getattr(self.ui, n) for n in NOMBRES_REGISTRO if hasattr(self.ui, n)]
        for registro in self._registros:
            registro.setReadOnly(True)

        # boton Print: estado conjunto
        self._estilo_print_base = self.ui.btnPrint.styleSheet()
        self._parpadeo_encendido = False
        self.timer_parpadeo = QTimer(self)
        self.timer_parpadeo.setInterval(PERIODO_PARPADEO_MS)
        self.timer_parpadeo.timeout.connect(self._parpadear)
        self.estado = ESTADO_SIN_TRABAJO

        # mesa de impresion en lugar del QLabel del disenador
        self.mesa = MesaImpresion(config.MESA_ANCHO_MM, config.MESA_ALTO_MM, self.pagina)
        self.mesa.setGeometry(self.ui.labelImage.geometry())
        self.mesa.setStyleSheet(self.ui.labelImage.styleSheet())
        self.ui.labelImage.hide()
        self.mesa.posicion_cambiada.connect(self.actualizar_posicion)

        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))
        self.ui.pos_x_target.setValidator(validador)
        self.ui.pos_y_target.setValidator(validador)
        self.ui.pos_x_target.editingFinished.connect(self.ir_a_posicion)
        self.ui.pos_y_target.editingFinished.connect(self.ir_a_posicion)

        # boards: senales y combos de modo
        self._combos = {}
        for board in self.boards:
            board.mensaje.connect(self.registrar)
            board.estado_cambiado.connect(lambda _e: self._actualizar_estado())
            board.modos_recibidos.connect(lambda modos, b=board: self._cargar_modos(b, modos))
            board.dpi_recibido.connect(lambda dx, dy, b=board: self._guardar_dpi(b, dx, dy))
            combo = getattr(self.ui, COMBOS_MODO.get(board.nombre, ""), None)
            if combo is not None:
                self._combos[board.nombre] = combo
                combo.currentTextChanged.connect(lambda modo, b=board: self._modo_seleccionado(b, modo))

        # botones
        self.ui.btnUpdateMode.clicked.connect(self.cargar_modos)
        self.ui.btnSelect.clicked.connect(self.seleccionar_trabajo)
        self.ui.btnPrint.clicked.connect(self.imprimir)
        self.ui.btnAbort.clicked.connect(self.abortar)
        self.ui.btnNewjob.clicked.connect(self.cargar_imagen)
        self.ui.btnRotate.clicked.connect(self.rotar_imagen)
        self.ui.btnMirrorX.clicked.connect(self.espejar_x)
        self.ui.btnMirrorY.clicked.connect(self.espejar_y)
        self.ui.btnRip.clicked.connect(self.generar_trabajo)
        self.ui.btn_clear.clicked.connect(self.limpiar_imagen)
        self._recuadros_preview = [self.ui.rip1, self.ui.rip2, self.ui.rip3, self.ui.rip4]

    # ===== utilidades =====
    def registrar(self, texto):
        ahora = time.monotonic()
        anterior, instante = self._ultimo_mensaje
        if texto == anterior and ahora - instante < VENTANA_DUPLICADOS_S:
            return   # el PMB repite los avisos (listener + comando): se muestra uno
        self._ultimo_mensaje = (texto, ahora)
        for registro in self._registros:
            registro.append(texto)

    def entrar(self):
        """Muestra la pagina, actualiza que combos estan activos y conecta las boards activas."""
        self.ui.stackedWidget.setCurrentWidget(self.pagina)
        self._actualizar_combos()
        for board, _x in self.boards_activas():
            board.conectar()

    # ===== boards activas =====
    def boards_activas(self):
        """[(board, x_cabezal_mm), ...] de los cabezales activos en Programa que tienen board.
        Avisa de los tipos sin board conocida."""
        activas = []
        for tipo, x_mm in self._cabezales_activos():
            board = self._board_por_tipo.get(tipo)
            if board is None:
                self.registrar(f"[PRINT SERVER] El modulo {tipo} no tiene board asociada todavia")
                continue
            if board not in [b for b, _ in activas]:
                activas.append((board, x_mm))
        return activas

    def esta_lista(self):
        """True si hay al menos una board activa y todas estan armadas."""
        activas = self.boards_activas()
        return bool(activas) and all(b.esta_lista() for b, _ in activas)

    def print_go_software(self):
        for board, _x in self.boards_activas():
            board.print_go_software()

    def _actualizar_combos(self):
        activos = {b.nombre for b, _ in self.boards_activas()}
        for nombre, combo in self._combos.items():
            combo.setEnabled(nombre in activos)

    # ===== modos =====
    def cargar_modos(self):
        self._actualizar_combos()
        activas = self.boards_activas()
        if not activas:
            self.registrar("[PRINT SERVER] No hay ningun cabezal activo en la pagina Programa")
        for board, _x in activas:
            combo = self._combos.get(board.nombre)
            if combo is not None:
                combo.clear()
            board.pedir_modos()

    def _cargar_modos(self, board, modos):
        combo = self._combos.get(board.nombre)
        if combo is not None:
            combo.clear()
            combo.addItems(modos)

    def _modo_seleccionado(self, board, modo):
        if not modo:
            return
        resolucion = re.findall(PATRON_DPI, modo, re.IGNORECASE)
        if len(resolucion) == 2 and self.dpi_actual is None:
            self.dpi_actual = (int(resolucion[0]), int(resolucion[1]))
        board.seleccionar_modo(modo)

    def _guardar_dpi(self, board, dpi_x, dpi_y):
        """La resolucion fija el tamano fisico de la imagen; si dos boards difieren, manda la primera."""
        if self.dpi_actual is not None and self.dpi_actual != (dpi_x, dpi_y):
            self.registrar(f"[{board.nombre}] Modo a {dpi_x} x {dpi_y} dpi; el tamano de la imagen "
                           f"se calcula con {self.dpi_actual[0]} x {self.dpi_actual[1]} dpi")
            return
        self.dpi_actual = (dpi_x, dpi_y)
        self.registrar(f"[{board.nombre}] Modo activo: {dpi_x} x {dpi_y} dpi")

    # ===== posicion en la mesa =====
    def actualizar_posicion(self, x_mm, y_mm):
        self.ui.pos_x_real.setText(f"{x_mm:.{DECIMALES_POSICION}f}")
        self.ui.pos_y_real.setText(f"{y_mm:.{DECIMALES_POSICION}f}")

    def ir_a_posicion(self):
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

    def geometria_imagen(self):
        """(x_mm, ancho_mm) de la imagen sobre la mesa, o None."""
        posicion = self.mesa.posicion_imagen_mm()
        if posicion is None or self.ancho_imagen_mm is None:
            return None
        return posicion[0], self.ancho_imagen_mm

    # ===== imagen =====
    def _mostrar_pixmap(self, pixmap, x_mm=None, y_mm=None):
        dpi_x, dpi_y = self.dpi_actual
        self.ancho_imagen_mm = pixmap.width() * MM_POR_PULGADA / dpi_x
        self.alto_imagen_mm = pixmap.height() * MM_POR_PULGADA / dpi_y
        self.mesa.mostrar_imagen(pixmap, self.ancho_imagen_mm, self.alto_imagen_mm, x_mm, y_mm)
        self.ui.lblSizeValue.setText(f"{self.ancho_imagen_mm:.1f} x {self.alto_imagen_mm:.1f} mm")

    def cargar_imagen(self):
        if self.dpi_actual is None:
            self.registrar("[PRINT SERVER] Selecciona antes un modo de impresion")
            return
        ruta, _ = QFileDialog.getOpenFileName(self.mesa.window(), "Seleccionar imagen", "", FILTRO_IMAGENES)
        if not ruta:
            return
        pixmap = QPixmap(ruta)
        if pixmap.isNull():
            self.registrar(f"[PRINT SERVER] No se ha podido abrir: {ruta}")
            return
        self.ruta_imagen = os.path.normpath(ruta)
        self.rotacion_imagen = 0
        self.espejo_x = False
        self.espejo_y = False
        self._mostrar_pixmap(pixmap, POSICION_INICIAL_X_MM, POSICION_INICIAL_Y_MM)
        self.registrar(f"[PRINT SERVER] Imagen: {pixmap.width()} x {pixmap.height()} px "
                       f"({self.ancho_imagen_mm:.2f} x {self.alto_imagen_mm:.2f} mm)")

    def _refrescar_vista(self):
        if self.ruta_imagen is None:
            return
        transformacion = QTransform()
        transformacion.rotate(self.rotacion_imagen)
        transformacion.scale(-1 if self.espejo_x else 1, -1 if self.espejo_y else 1)
        self._mostrar_pixmap(QPixmap(self.ruta_imagen).transformed(transformacion, Qt.SmoothTransformation))

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
        self.limpiar_previews()
        for board in self.boards:
            board.descartar()
        self.registrar("[PRINT SERVER] Imagen descartada")

    # ===== trabajo =====
    def _trabajo(self):
        x_mm, y_mm = self.mesa.posicion_imagen_mm()
        return Trabajo(ruta_imagen=self.ruta_imagen, ancho_mm=self.ancho_imagen_mm,
                       alto_mm=self.alto_imagen_mm, x_mm=x_mm, y_mm=y_mm,
                       rotacion=self.rotacion_imagen, espejo_x=self.espejo_x, espejo_y=self.espejo_y)

    def generar_trabajo(self):
        """Ripea el trabajo en todas las boards activas, cada una con su cabezal."""
        if self.ruta_imagen is None:
            self.registrar("[PRINT SERVER] No hay ninguna imagen cargada")
            return
        activas = self.boards_activas()
        if not activas:
            self.registrar("[PRINT SERVER] No hay ningun cabezal activo en la pagina Programa")
            return
        trabajo = self._trabajo()
        self.limpiar_previews()
        for board, x_cabezal in activas:
            board.preparar(trabajo, x_cabezal)

    def seleccionar_trabajo(self):
        """Adopta una carpeta de trabajo ya ripeada en las boards que la reconozcan."""
        carpeta = QFileDialog.getExistingDirectory(self.mesa.window(), "Seleccionar carpeta de trabajo")
        if not carpeta:
            return
        carpeta = os.path.normpath(carpeta)
        adoptada = [b.nombre for b, _ in self.boards_activas() if b.cargar_carpeta(carpeta)]
        if adoptada:
            self.registrar(f"[PRINT SERVER] Trabajo {carpeta} cargado en {', '.join(adoptada)}")
        else:
            self.registrar(f"[PRINT SERVER] Ninguna board activa reconoce el trabajo {carpeta}")

    def imprimir(self):
        """Boton Print: arma todas las boards activas. La mesa la mueve la pagina Programa."""
        activas = self.boards_activas()
        if not activas:
            self.registrar("[PRINT SERVER] No hay ningun cabezal activo en la pagina Programa")
            return
        posicion = self._posicion_eje()
        for board, _x in activas:
            board.armar(posicion)

    def abortar(self):
        for board, _x in self.boards_activas():
            board.abortar()

    # ===== estado conjunto y boton Print =====
    def _actualizar_estado(self):
        activas = [b for b, _ in self.boards_activas()]
        if not activas:
            estado = ESTADO_SIN_TRABAJO
        else:
            estado = min((b.estado for b in activas), key=ORDEN_ESTADOS.index)
        if estado != self.estado:
            anterior = self.estado
            self.estado = estado
            self._pintar_estado()
            if estado == ESTADO_RENDER_LISTO and ORDEN_ESTADOS.index(anterior) < ORDEN_ESTADOS.index(estado):
                self.cargar_previews()   # todas han terminado de ripear

    def _pintar_print(self, color=None, texto=TEXTO_PRINT):
        hoja = self._estilo_print_base
        if color is not None:
            hoja += f"\nQPushButton {{ background-color: {color}; }}"
        self.ui.btnPrint.setStyleSheet(hoja)
        self.ui.btnPrint.setText(texto)

    def _parpadear(self):
        self._parpadeo_encendido = not self._parpadeo_encendido
        self._pintar_print(COLOR_AVISO if self._parpadeo_encendido else None)

    def _pintar_estado(self):
        self.timer_parpadeo.stop()
        if self.estado in (ESTADO_RENDER_LISTO, ESTADO_ARMANDO):
            self._pintar_print()
            self._parpadeo_encendido = False
            self.timer_parpadeo.start()
        elif self.estado == ESTADO_LISTO:
            self._pintar_print(COLOR_LISTO, TEXTO_LISTO)
        else:
            self._pintar_print()

    # ===== previews =====
    def cargar_previews(self):
        """Planos de la primera board activa que los tenga, a escala de la mesa y con
        el desplazamiento X del trabajo. El alto del render ya es el de la mesa."""
        self.limpiar_previews()
        for board, _x in self.boards_activas():
            planos = board.planos_render()
            geometria = board.geometria_trabajo()
            if not planos or geometria is None:
                continue
            x_mm, ancho_mm = geometria
            cargados = 0
            for recuadro, ruta, color in zip(self._recuadros_preview, planos, COLORES_PLANOS):
                plano = QPixmap(ruta)
                if plano.isNull():
                    continue
                recuadro.setPixmap(self._componer_preview(recuadro.size(), plano, x_mm, ancho_mm, color))
                cargados += 1
            if cargados:
                return
        self.registrar("[PRINT SERVER] No se han encontrado planos rasterizados para las previews")

    @staticmethod
    def _tenir_plano(plano, color):
        """Negro = tinta. max(pixel, color) deja el blanco intacto y el negro pasa a color."""
        tenido = QPixmap(plano)
        pintor = QPainter(tenido)
        pintor.setCompositionMode(QPainter.CompositionMode_Lighten)
        pintor.fillRect(tenido.rect(), QColor(color))
        pintor.end()
        return tenido

    @classmethod
    def _componer_preview(cls, tamano, plano, x_mm, ancho_mm, color):
        escala = tamano.width() / config.MESA_ANCHO_MM   # px por mm
        reducido = plano.scaled(round(ancho_mm * escala), tamano.height(),
                                Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        lienzo = QPixmap(tamano)
        lienzo.fill(QColor(COLOR_FONDO_PREVIEW))
        pintor = QPainter(lienzo)
        pintor.drawPixmap(round(x_mm * escala), 0, cls._tenir_plano(reducido, color))
        pintor.end()
        return lienzo

    def limpiar_previews(self):
        for recuadro in self._recuadros_preview:
            recuadro.clear()
