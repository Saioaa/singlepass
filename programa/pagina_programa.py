# -*- coding: utf-8 -*-
"""Pagina Programa: parametros de la secuencia, grafico de la barra a escala,
arranque/parada de la secuencia real y simulacion.

El grafico dibuja la barra (2200 mm) con sus modulos, los perfiles de
velocidad y la mesa como un rectangulo que se mueve con la posicion del eje:
la real cuando hay maquina, la del MotorSimulado durante una simulacion.

Botones del .ui: bt_pg_prog_start (secuencia real), bt_pg_prog_stop (para las
dos), bt_pg_prog_simulacion (solo simulada: no toca D1 ni M-Duino ni PMB).
"""

import time

from PySide6.QtCore import QEvent, QLocale, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QDoubleValidator, QFont, QPen
from PySide6.QtWidgets import (QFrame, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsTextItem)

import config
from secuencia import ParametrosPrograma

# ===== MODULOS DE LA BARRA =====
PRIMER_MODULO = 1
ULTIMO_MODULO = 8
TIPOS_CABEZAL = ("PMB-C8", "PMB-C2", "APMB4")   # confirmar si SM-200 imprime
MODULO_VACIO  = "-"
TIPO_NIR      = "NIR"
TIPO_SECADOR  = "Air dryver"
COLOR_NIR     = "#CC9B62"
COLOR_SECADOR = "#CC7662"
COLOR_CABEZAL = "#62CBC9"
GRADOS_POR_GIRO = 90   # rotacion del nombre del modulo en el grafico

# ===== GRAFICO DE LA BARRA (px) =====
MARGEN_SUPERIOR_MODULO = 10
ALTO_RESERVADO_MODULO  = 40    # alto de la vista menos esto = alto del rectangulo
Y_NUMERO_MODULO        = 12
MARGEN_MESETA          = 15
GROSOR_PERFIL          = 2
ALTO_BARRA_PX          = 10    # linea negra que representa el eje
ALTO_MESA_PX           = 22    # rectangulo de la mesa sobre el eje
ALTO_IMAGEN_PX         = 8     # imagen dibujada sobre la mesa
MARGEN_TEXTO_PX        = 6
TAMANO_TEXTO_ESTADO_PT = 10
COLOR_BARRA   = "#111111"
COLOR_MESA    = "#FFFFFF"
COLOR_BORDE_MESA = "#333333"
COLOR_IMAGEN  = "#7F8C8D"
COLOR_TEXTO   = "#FFFFFF"
COLOR_PULSO   = "#E74C3C"
DURACION_AVISO_PULSO_S = 0.6

# recorrido (mm) de los dos bordes del carro durante la impresion
PERFIL_IMPRESION_DELANTERO = (50, 1900)
PERFIL_IMPRESION_TRASERO   = (300, 2150)
DESFASE_BORDE_TRASERO_MM   = 250
FIN_CARRERA_DELANTERO_MM   = 1900
FIN_CARRERA_TRASERO_MM     = 2150
COLOR_IMPR_DELANTERO = "#2E86C1"
COLOR_IMPR_TRASERO   = "#C0392B"
COLOR_CUR_DELANTERO  = "#27AE60"
COLOR_CUR_TRASERO    = "#F39C12"

# ===== TEMPORIZACION =====
PERIODO_ANIMACION_MS = 40   # refresco de la mesa en el grafico


def _leer_float(campo, por_defecto=None):
    """float del texto de un QLineEdit, o por_defecto si esta vacio o no es numero."""
    try:
        return float(campo.text())
    except ValueError:
        return por_defecto


class PaginaPrograma(QObject):

    def __init__(self, ui, secuencia_real, secuencia_sim, motor_sim, mduino_sim,
                 pmb_lista, abortar_pmb, geometria_imagen, posicion_real, registrar,
                 parent=None):
        super().__init__(parent)
        self.ui = ui
        self.secuencia_real = secuencia_real
        self.secuencia_sim = secuencia_sim
        self.motor_sim = motor_sim
        self.mduino_sim = mduino_sim
        self._pmb_lista = pmb_lista              # callable -> bool
        self._abortar_pmb = abortar_pmb          # callable
        self._geometria_imagen = geometria_imagen  # callable -> (x_mm, ancho_mm) | None
        self._posicion_real = posicion_real      # callable -> mm | None
        self.registrar = registrar               # callable(texto)

        self.mostrar_simulada = False   # que posicion mueve la mesa del grafico
        self._t_ultimo_pulso = 0.0

        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))
        for campo in (self.ui.pg_prog_acel_curado, self.ui.pg_prog_acel_impresion,
                      self.ui.pg_prog_cant_pasadas_curado, self.ui.pg_prog_decel_curado,
                      self.ui.pg_prog_decel_impresion, self.ui.pg_prog_vel_impresion,
                      self.ui.pg_prog_vel_curado):
            campo.setValidator(validador)

        self.ui.bt_pg_prog_start.clicked.connect(self.start)
        self.ui.bt_pg_prog_stop.clicked.connect(self.stop)
        self.ui.bt_pg_prog_simulacion.clicked.connect(self.simular)

        self.mduino_sim.pulso_enviado.connect(self._pulso_simulado)
        self.mduino_sim.lamparas_cambiadas.connect(lambda _pwm: self.actualizar_animacion())
        self.secuencia_sim.terminada.connect(lambda: self.registrar("[SIMULACION] Secuencia terminada"))

        # grafico de la barra a escala
        self.escena = QGraphicsScene(self)
        self.ui.pg_vista.setScene(self.escena)
        self.ui.pg_vista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setFrameShape(QFrame.NoFrame)
        self.ui.pg_vista.viewport().installEventFilter(self)
        self._mesa_item = None
        self._imagen_item = None
        self._texto_estado = None
        self._escala = 1.0
        self._y_base = 0.0

        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            self.combo_modulo(i).currentIndexChanged.connect(self.dibujar_modulos)
            self.campo_distancia(i).textChanged.connect(self.dibujar_modulos)
        for campo in (self.ui.pg_prog_vel_impresion, self.ui.pg_prog_acel_impresion,
                      self.ui.pg_prog_decel_impresion, self.ui.pg_prog_vel_curado,
                      self.ui.pg_prog_acel_curado, self.ui.pg_prog_decel_curado,
                      self.ui.pg_prog_inicio_curado):
            campo.textChanged.connect(self.dibujar_modulos)

        self.timer_animacion = QTimer(self)
        self.timer_animacion.setInterval(PERIODO_ANIMACION_MS)
        self.timer_animacion.timeout.connect(self.actualizar_animacion)
        self.timer_animacion.start()

    def eventFilter(self, objeto, evento):
        if evento.type() == QEvent.Resize:
            QTimer.singleShot(0, self.dibujar_modulos)   # solo esta filtrado el viewport de pg_vista
        return False

    # ===== widgets repetidos =====
    def combo_modulo(self, i):
        return getattr(self.ui, f"modulo{i}")

    def campo_distancia(self, i):
        return getattr(self.ui, f"M{i}D")

    # ===== parametros =====
    def leer_parametros(self):
        pasadas = _leer_float(self.ui.pg_prog_cant_pasadas_curado, por_defecto=0)
        return ParametrosPrograma(
            vel_impresion=float(self.ui.pg_prog_vel_impresion.text()),
            acel_impresion=float(self.ui.pg_prog_acel_impresion.text()),
            decel_impresion=float(self.ui.pg_prog_decel_impresion.text()),
            vel_curado=float(self.ui.pg_prog_vel_curado.text()),
            acel_curado=float(self.ui.pg_prog_acel_curado.text()),
            decel_curado=float(self.ui.pg_prog_decel_curado.text()),
            pasadas_curado=int(pasadas),
            inicio_curado=_leer_float(self.ui.pg_prog_inicio_curado),
        )

    # ===== arranque / parada =====
    def start(self):
        """Secuencia real: D1 + M-Duino + PMB armado."""
        try:
            parametros = self.leer_parametros()
        except ValueError:
            self.registrar("[PROGRAMA] Faltan parametros de impresion o curado")
            return
        if self.secuencia_sim.en_marcha():
            self.registrar("[PROGRAMA] Hay una simulacion en marcha: parala antes")
            return
        if not self._pmb_lista():
            self.registrar("[PROGRAMA] El PMB no esta armado: pulsa Print en la pagina PMB-8")
            return
        self.mostrar_simulada = False
        if not self.secuencia_real.start(parametros):
            self.registrar("[PROGRAMA] No se puede arrancar: seta o referencia pendiente")

    def simular(self):
        """Solo el grafico: mueve el MotorSimulado con la secuencia, sin tocar la maquina."""
        try:
            parametros = self.leer_parametros()
        except ValueError:
            self.registrar("[SIMULACION] Faltan parametros de impresion o curado")
            return
        if self.secuencia_real.en_marcha():
            self.registrar("[SIMULACION] La secuencia real esta en marcha")
            return
        self.mostrar_simulada = True
        self.mduino_sim.lamparas(0)
        if self.secuencia_sim.start(parametros):
            self.registrar("[SIMULACION] Secuencia iniciada")

    def stop(self):
        if self.secuencia_sim.en_marcha():
            self.secuencia_sim.stop()
            self.registrar("[SIMULACION] Parada")
        if self.secuencia_real.en_marcha():
            self.secuencia_real.stop()
            if self._pmb_lista():
                self._abortar_pmb()   # el PMB no debe quedarse esperando un print go que no llegara

    def _pulso_simulado(self):
        self._t_ultimo_pulso = time.monotonic()
        self.registrar("[SIMULACION] PULSE (print go)")

    # ===== modulos =====
    def leer_modulos(self):
        """[(indice, tipo, posicion_mm), ...] de las ranuras ocupadas."""
        modulos = []
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            tipo = self.combo_modulo(i).currentText()
            distancia = _leer_float(self.campo_distancia(i))
            if tipo in (MODULO_VACIO, "") or distancia is None:
                continue
            modulos.append((i, tipo, distancia))
        return modulos

    def posicion_cabezal(self):
        """Posicion del primer cabezal de impresion sobre el recorrido, en mm."""
        cabezales = sorted((m for m in self.leer_modulos() if m[1] in TIPOS_CABEZAL),
                           key=lambda m: m[2])
        return cabezales[0][2] if cabezales else None

    # ===== grafico estatico =====
    def _dibujar_perfil(self, v, a, dec, inicio_mm, fin_mm, escala, y_base, altura, color):
        """Perfil trapezoidal de velocidad de un borde del carro."""
        if v <= 0 or a <= 0 or dec <= 0:
            return
        dist_acel = v * v / (2 * a)
        dist_decel = v * v / (2 * dec)
        recorrido = fin_mm - inicio_mm
        if dist_acel + dist_decel > recorrido:   # no cabe la meseta: triangulo
            dist_acel = recorrido * a / (a + dec)
            dist_decel = recorrido - dist_acel
        x0 = inicio_mm * escala
        x1 = (inicio_mm + dist_acel) * escala
        x2 = (fin_mm - dist_decel) * escala
        x3 = fin_mm * escala
        y_pico = y_base - altura
        lapiz = QPen(QColor(color))
        lapiz.setWidth(GROSOR_PERFIL)
        self.escena.addLine(x0, y_base, x1, y_pico, lapiz)
        self.escena.addLine(x1, y_pico, x2, y_pico, lapiz)
        self.escena.addLine(x2, y_pico, x3, y_base, lapiz)

    def dibujar_modulos(self):
        self.escena.clear()
        self._mesa_item = self._imagen_item = self._texto_estado = None

        ancho_px = self.ui.pg_vista.viewport().width()
        alto_px = self.ui.pg_vista.viewport().height()
        self.escena.setSceneRect(0, 0, ancho_px, alto_px)
        self._escala = ancho_px / config.BARRA_MM   # px por mm
        escala = self._escala

        # eje: linea negra a lo ancho, pegada abajo
        y_barra = alto_px - ALTO_BARRA_PX
        self.escena.addRect(QRectF(0, y_barra, ancho_px, ALTO_BARRA_PX),
                            QPen(Qt.NoPen), QBrush(QColor(COLOR_BARRA)))
        self._y_base = y_barra - ALTO_MESA_PX   # sobre la mesa arrancan los perfiles

        alto_rect = self._y_base - ALTO_RESERVADO_MODULO
        for i, tipo, distancia in self.leer_modulos():
            x = distancia * escala
            w = config.MODULO_MM * escala
            color = {TIPO_NIR: COLOR_NIR, TIPO_SECADOR: COLOR_SECADOR}.get(tipo, COLOR_CABEZAL)
            rect = QGraphicsRectItem(QRectF(x, MARGEN_SUPERIOR_MODULO, w, alto_rect))
            rect.setBrush(QBrush(QColor(color)))
            self.escena.addItem(rect)
            num = QGraphicsTextItem(str(i))
            num.setPos(x + (w - num.boundingRect().width()) / 2, Y_NUMERO_MODULO)
            self.escena.addItem(num)
            nombre = QGraphicsTextItem(tipo)
            r = nombre.boundingRect()
            nombre.setRotation(GRADOS_POR_GIRO)
            nombre.setPos(x + w / 2 + r.height() / 2,
                          MARGEN_SUPERIOR_MODULO + alto_rect / 2 - r.width() / 2)
            self.escena.addItem(nombre)

        # perfiles de velocidad de los dos bordes del carro
        y_base = self._y_base
        altura_max = y_base - MARGEN_MESETA
        v_impr = _leer_float(self.ui.pg_prog_vel_impresion, por_defecto=0)
        a_impr = _leer_float(self.ui.pg_prog_acel_impresion, por_defecto=0)
        d_impr = _leer_float(self.ui.pg_prog_decel_impresion, por_defecto=0)
        v_cur = _leer_float(self.ui.pg_prog_vel_curado, por_defecto=0)
        a_cur = _leer_float(self.ui.pg_prog_acel_curado, por_defecto=0)
        d_cur = _leer_float(self.ui.pg_prog_decel_curado, por_defecto=0)
        if v_impr > 0:
            self._dibujar_perfil(v_impr, a_impr, d_impr, *PERFIL_IMPRESION_DELANTERO,
                                 escala, y_base, altura_max, COLOR_IMPR_DELANTERO)
            self._dibujar_perfil(v_impr, a_impr, d_impr, *PERFIL_IMPRESION_TRASERO,
                                 escala, y_base, altura_max, COLOR_IMPR_TRASERO)
        inicio_cur = _leer_float(self.ui.pg_prog_inicio_curado)
        if v_impr > 0 and v_cur > 0 and inicio_cur is not None:
            altura_cur = altura_max * (v_cur / v_impr)
            self._dibujar_perfil(v_cur, a_cur, d_cur, inicio_cur, FIN_CARRERA_DELANTERO_MM,
                                 escala, y_base, altura_cur, COLOR_CUR_DELANTERO)
            self._dibujar_perfil(v_cur, a_cur, d_cur,
                                 inicio_cur + DESFASE_BORDE_TRASERO_MM, FIN_CARRERA_TRASERO_MM,
                                 escala, y_base, altura_cur, COLOR_CUR_TRASERO)

        # elementos animados: mesa, imagen sobre la mesa y texto de estado
        self._mesa_item = self.escena.addRect(
            QRectF(0, 0, config.MESA_ANCHO_MM * escala, ALTO_MESA_PX),
            QPen(QColor(COLOR_BORDE_MESA)), QBrush(QColor(COLOR_MESA)))
        self._imagen_item = self.escena.addRect(
            QRectF(0, 0, 0, ALTO_IMAGEN_PX), QPen(Qt.NoPen), QBrush(QColor(COLOR_IMAGEN)))
        self._texto_estado = QGraphicsSimpleTextItem()
        self._texto_estado.setBrush(QBrush(QColor(COLOR_TEXTO)))
        self._texto_estado.setFont(QFont("", TAMANO_TEXTO_ESTADO_PT))
        self.escena.addItem(self._texto_estado)
        self.actualizar_animacion()

    # ===== grafico animado =====
    def posicion_mostrada(self):
        """Posicion del eje que mueve la mesa del grafico, en mm."""
        if self.mostrar_simulada:
            return self.motor_sim.leer_posicion()
        posicion = self._posicion_real()
        return posicion if posicion is not None else self.motor_sim.leer_posicion()

    def actualizar_animacion(self):
        if self._mesa_item is None:
            return
        escala = self._escala
        x_mesa = self.posicion_mostrada() * escala
        self._mesa_item.setPos(x_mesa, self._y_base)

        geometria = self._geometria_imagen()
        if geometria is None:
            self._imagen_item.setVisible(False)
        else:
            x_imagen, ancho_imagen = geometria
            self._imagen_item.setRect(0, 0, ancho_imagen * escala, ALTO_IMAGEN_PX)
            self._imagen_item.setPos(x_mesa + x_imagen * escala,
                                     self._y_base + (ALTO_MESA_PX - ALTO_IMAGEN_PX) / 2)
            self._imagen_item.setVisible(True)

        if self.mostrar_simulada:
            fuente = "SIM"
            etapa = self.secuencia_sim.etapa
            pwm = self.mduino_sim.pwm_lamparas
        else:
            fuente = "REAL"
            etapa = self.secuencia_real.etapa
            pwm = self.secuencia_real.senal_lamparas
        hace_pulso = time.monotonic() - self._t_ultimo_pulso < DURACION_AVISO_PULSO_S
        texto = (f"{fuente}  pos {self.posicion_mostrada():.1f} mm   etapa {etapa}   "
                 f"lamparas {pwm}%" + ("   PRINT GO" if hace_pulso else ""))
        self._texto_estado.setText(texto)
        self._texto_estado.setBrush(QBrush(QColor(COLOR_PULSO if hace_pulso else COLOR_TEXTO)))
        self._texto_estado.setPos(MARGEN_TEXTO_PX, MARGEN_TEXTO_PX)
