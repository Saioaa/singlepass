# -*- coding: utf-8 -*-
"""Ventana principal: navegacion, pagina de movimientos y pagina de programa.

Los dispositivos (MotorD1, ClienteMDuino, ClientePMB) los crea main.py y
llegan por el constructor. La pagina PMB-8 vive en pagina_pmb.py.

ui_pantalla_programa.py debe generarse con:
    pyside6-uic pantalla_programa.ui -o ui_pantalla_programa.py
"""

import json
import os
import re

from PySide6.QtCore import QLocale, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QDoubleValidator, QGuiApplication, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsTextItem, QMainWindow, QWidget)

import config
from d1 import MODO_POSICION
from pagina_pmb import PaginaPMB
from secuencia import ParametrosPrograma, SecuenciaImpresion
from ui_pantalla_programa import Ui_MainWindow

# ===== CAMPOS DE TEXTO QUE SE GUARDAN ENTRE SESIONES =====
CAMPOS_TEXTO = [
    "objetivo", "vel_objetivo", "aceleracion", "deceleracion",
    "pg_prog_vel_impresion", "pg_prog_acel_impresion", "pg_prog_decel_impresion",
    "pg_prog_vel_curado", "pg_prog_acel_curado", "pg_prog_decel_curado",
    "pg_prog_cant_pasadas_curado", "pg_prog_inicio_curado",
]

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

# ===== ESCALADO A LA PANTALLA =====
# El .ui esta disenado con geometrias absolutas para esta resolucion.
ANCHO_DISENO_PX = 1960
ALTO_DISENO_PX  = 1072
TOLERANCIA_ESCALA = 0.01
PATRON_PIXELES = re.compile(r"(\d+)px")

# ===== MOVIMIENTOS MANUALES (mm/s, mm/s2) =====
VELOCIDAD_JOG_LENTA     = 100
VELOCIDAD_JOG_RAPIDA    = 500
ACELERACION_JOG_LENTA   = 100
ACELERACION_JOG_RAPIDA  = 300
DECELERACION_JOG_LENTA  = 1000
DECELERACION_JOG_RAPIDA = 1000
VELOCIDAD_REPOSO        = 40
ACELERACION_REPOSO      = 40
DECELERACION_REPOSO     = 40
SENTIDO_DERECHA   = +1
SENTIDO_IZQUIERDA = -1

# ===== TEMPORIZADORES (ms) =====
PERIODO_VIGILANCIA_JOG    = 50    # comprobacion de limites durante el jog
PERIODO_SONDEO_HOMING     = 100   # vigilancia del homing
PERIODO_REFRESCO_POSICION = 500   # refresco del campo de posicion
PERIODO_LATIDO            = 500   # lectura ligera para que el D1 no cierre la sesion

# ===== GRAFICO DE LA BARRA (px) =====
MARGEN_SUPERIOR_MODULO = 10
ALTO_RESERVADO_MODULO  = 40    # alto de la vista menos esto = alto del rectangulo
Y_NUMERO_MODULO        = 12
MARGEN_MESETA          = 15
GROSOR_PERFIL          = 2
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


def _leer_float(campo, por_defecto=None):
    """float del texto de un QLineEdit, o por_defecto si esta vacio o no es numero."""
    try:
        return float(campo.text())
    except ValueError:
        return por_defecto


class VentanaPrincipal(QMainWindow):

    def __init__(self, motor, mduino, pmb):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))

        # ===== dispositivos (creados en main.py) =====
        self.motor = motor
        self.mduino = mduino
        self.pmb = pmb

        # ===== paginas y secuencia =====
        self.pagina_pmb = PaginaPMB(self.ui, self.pmb, self.posicion_cabezal, parent=self)
        self.secuencia = SecuenciaImpresion(self.motor, self.mduino,
                                            self.pagina_pmb.armar_impresion,
                                            config.POSICION_REPOSO_MM,
                                            config.FINAL_RECORRIDO_MM, parent=self)
        self.mduino.seta_cambiada.connect(self.secuencia.set_seta)

        self.homing_en_curso = False   # impide leer la posicion durante el homing

        # ===== navegacion =====
        self.ui.bt_pg_movimientos1.clicked.connect(self.ir_pg_movimientos)
        self.ui.bt_pg_movimientos2.clicked.connect(self.ir_pg_movimientos)
        self.ui.bt_pg_menu.clicked.connect(self.ir_pg_menu)
        self.ui.bt_pg_programa.clicked.connect(self.ir_pg_programa)
        self.ui.bt_pg_programa_2.clicked.connect(self.ir_pg_programa)
        self.ui.pushButton.clicked.connect(self.pagina_pmb.entrar)

        # ===== pagina movimientos =====
        self.ui.bt_ir_objetivo.clicked.connect(self.ir_objetivo)
        self.ui.bt_mov_derecha.pressed.connect(self.mov_derecha)
        self.ui.bt_mov_izquierda.pressed.connect(self.mov_izquierda)
        self.ui.bt_mov_derecha.released.connect(self.stop_motor)
        self.ui.bt_mov_izquierda.released.connect(self.stop_motor)
        self.ui.bt_home.clicked.connect(self.home)
        self.ui.bt_mov_reposo.clicked.connect(self.mov_reposo)
        self.ui.bt_mov_derecha_rapido.pressed.connect(self.mov_derecha_rapido)
        self.ui.bt_mov_izquierda_rapido.pressed.connect(self.mov_izquierda_rapido)
        self.ui.bt_mov_derecha_rapido.released.connect(self.stop_motor)
        self.ui.bt_mov_izquierda_rapido.released.connect(self.stop_motor)

        self.ui.objetivo.setValidator(validador)
        self.ui.vel_objetivo.setValidator(validador)
        self.ui.aceleracion.setValidator(validador)
        self.ui.deceleracion.setValidator(validador)
        self.ui.posicion.setReadOnly(True)

        self.timer_jog = QTimer(self)
        self.timer_jog.setInterval(PERIODO_VIGILANCIA_JOG)

        self.timer_home = QTimer(self)
        self.timer_home.setInterval(PERIODO_SONDEO_HOMING)
        self.timer_home.timeout.connect(self.comprobar_home)

        self.timer_posicion = QTimer(self)
        self.timer_posicion.setInterval(PERIODO_REFRESCO_POSICION)
        self.timer_posicion.timeout.connect(self.refrescar_posicion)
        self.timer_posicion.start()

        self.timer_latido = QTimer(self)
        self.timer_latido.setInterval(PERIODO_LATIDO)
        self.timer_latido.timeout.connect(self.latido)
        self.timer_latido.start()

        # ===== pagina programa =====
        self.ui.bt_pg_prog_start.clicked.connect(self.start)
        self.ui.bt_pg_prog_stop.clicked.connect(self.stop)

        self.ui.pg_prog_acel_curado.setValidator(validador)
        self.ui.pg_prog_acel_impresion.setValidator(validador)
        self.ui.pg_prog_cant_pasadas_curado.setValidator(validador)
        self.ui.pg_prog_decel_curado.setValidator(validador)
        self.ui.pg_prog_decel_impresion.setValidator(validador)
        self.ui.pg_prog_vel_impresion.setValidator(validador)
        self.ui.pg_prog_vel_curado.setValidator(validador)

        # grafico de modulos a escala
        self.escena = QGraphicsScene(self)
        self.ui.pg_vista.setScene(self.escena)
        self.ui.pg_vista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setFrameShape(QFrame.NoFrame)

        # redibujar cuando el operario cambie un combo o una distancia
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            self._combo_modulo(i).currentIndexChanged.connect(self.dibujar_modulos)
            self._campo_distancia(i).textChanged.connect(self.dibujar_modulos)
        for campo in (self.ui.pg_prog_vel_impresion, self.ui.pg_prog_acel_impresion,
                      self.ui.pg_prog_decel_impresion, self.ui.pg_prog_vel_curado,
                      self.ui.pg_prog_acel_curado, self.ui.pg_prog_decel_curado,
                      self.ui.pg_prog_inicio_curado):
            campo.textChanged.connect(self.dibujar_modulos)

        self.cargar_ajustes()

    # ===== escalado =====
    def ajustar_a_pantalla(self):
        """Escala geometrias y tamanos en px de las hojas de estilo para que el
        diseno (ANCHO_DISENO_PX x ALTO_DISENO_PX) quepa en la pantalla actual."""
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        factor = min(pantalla.width() / ANCHO_DISENO_PX, pantalla.height() / ALTO_DISENO_PX)
        if abs(factor - 1.0) < TOLERANCIA_ESCALA:
            return

        def px(valor):
            return max(1, round(valor * factor))

        for widget in [self.centralWidget()] + self.findChildren(QWidget):
            g = widget.geometry()
            widget.setGeometry(px(g.x()), px(g.y()), px(g.width()), px(g.height()))
            hoja = widget.styleSheet()
            if hoja:
                widget.setStyleSheet(PATRON_PIXELES.sub(lambda m: f"{px(int(m.group(1)))}px", hoja))
            fuente = widget.font()
            if fuente.pointSizeF() > 0:
                fuente.setPointSizeF(fuente.pointSizeF() * factor)
                widget.setFont(fuente)

        self.resize(px(ANCHO_DISENO_PX), px(ALTO_DISENO_PX))
        print(f"[UI] Interfaz escalada x{factor:.2f} para {pantalla.width()}x{pantalla.height()}")

    # ===== cierre =====
    def closeEvent(self, evento):
        self.guardar_ajustes()
        super().closeEvent(evento)

    # ===== accesos a widgets repetidos =====
    def _combo_modulo(self, i):
        return getattr(self.ui, f"modulo{i}")

    def _campo_distancia(self, i):
        return getattr(self.ui, f"M{i}D")

    # ===== navegacion =====
    def ir_pg_menu(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.menu)

    def ir_pg_programa(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.programa)

    def ir_pg_movimientos(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.movimientos)

    # ===== motor: keep-alive y posicion =====
    def latido(self):
        try:
            self.motor.leer_estado()
        except Exception:
            pass

    def refrescar_posicion(self):
        """Actualiza el campo de posicion de la interfaz."""
        if self.homing_en_curso or self.secuencia.en_marcha():
            return
        try:
            self.ui.posicion.setText(f"{self.motor.leer_posicion():.2f}")
        except Exception as e:
            self.ui.posicion.setText("---")
            print(f"[POSICION] Lectura fallida: {e}")
            self.timer_posicion.stop()

    # ===== pagina programa =====
    def leer_parametros_programa(self):
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

    def start(self):
        try:
            parametros = self.leer_parametros_programa()
        except ValueError:
            self.ui.txtMessage.append("[PROGRAMA] Faltan parametros de impresion o curado")
            return
        if not self.secuencia.start(parametros):
            self.ui.txtMessage.append("[PROGRAMA] No se puede arrancar: seta o referencia pendiente")

    def stop(self):
        self.secuencia.stop()

    # ===== grafico de la barra =====
    def leer_modulos(self):
        """[(indice, tipo, posicion_mm), ...] de las ranuras ocupadas."""
        modulos = []
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            tipo = self._combo_modulo(i).currentText()
            distancia = _leer_float(self._campo_distancia(i))
            if tipo in (MODULO_VACIO, "") or distancia is None:
                continue
            modulos.append((i, tipo, distancia))
        return modulos

    def posicion_cabezal(self):
        """Posicion del primer cabezal de impresion sobre el recorrido, en mm."""
        cabezales = sorted((m for m in self.leer_modulos() if m[1] in TIPOS_CABEZAL),
                           key=lambda m: m[2])
        return cabezales[0][2] if cabezales else None

    def _dibujar_perfil(self, v, a, dec, inicio_mm, fin_mm, escala, y_base, altura, color):
        """Perfil trapezoidal de velocidad de un borde del carro."""
        if v <= 0 or a <= 0 or dec <= 0:
            return
        dist_acel = v * v / (2 * a)
        dist_decel = v * v / (2 * dec)
        recorrido = fin_mm - inicio_mm

        # si no cabe la meseta, el carro no llega a velocidad de crucero (triangulo)
        if dist_acel + dist_decel > recorrido:
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

        ancho_px = self.ui.pg_vista.viewport().width()
        alto_px = self.ui.pg_vista.viewport().height()
        self.escena.setSceneRect(0, 0, ancho_px, alto_px)
        escala = ancho_px / config.BARRA_MM   # px por mm

        # fondo: imagen de la barra, a lo ancho, sin deformar, pegada abajo
        pixmap = QPixmap(config.RUTA_GUIA_EJE).scaledToWidth(ancho_px, Qt.SmoothTransformation)
        fondo = self.escena.addPixmap(pixmap)
        fondo.setPos(0, alto_px - pixmap.height())

        alto_rect = alto_px - ALTO_RESERVADO_MODULO
        for i, tipo, distancia in self.leer_modulos():
            x = distancia * escala
            w = config.MODULO_MM * escala

            if tipo == TIPO_NIR:
                color = COLOR_NIR
            elif tipo == TIPO_SECADOR:
                color = COLOR_SECADOR
            else:
                color = COLOR_CABEZAL

            rect = QGraphicsRectItem(QRectF(x, MARGEN_SUPERIOR_MODULO, w, alto_rect))
            rect.setBrush(QBrush(QColor(color)))
            self.escena.addItem(rect)

            # numero del modulo: horizontal, centrado arriba
            num = QGraphicsTextItem(str(i))
            num.setPos(x + (w - num.boundingRect().width()) / 2, Y_NUMERO_MODULO)
            self.escena.addItem(num)

            # nombre del modulo: vertical y centrado en el modulo
            nombre = QGraphicsTextItem(tipo)
            r = nombre.boundingRect()
            cx = x + w / 2
            cy = MARGEN_SUPERIOR_MODULO + alto_rect / 2
            nombre.setRotation(GRADOS_POR_GIRO)
            nombre.setPos(cx + r.height() / 2, cy - r.width() / 2)
            self.escena.addItem(nombre)

        # perfiles de velocidad de los dos bordes del carro
        y_base = alto_px - pixmap.height()
        altura_max = y_base - MARGEN_MESETA

        v_impr = _leer_float(self.ui.pg_prog_vel_impresion, por_defecto=0)
        a_impr = _leer_float(self.ui.pg_prog_acel_impresion, por_defecto=0)
        d_impr = _leer_float(self.ui.pg_prog_decel_impresion, por_defecto=0)
        v_cur = _leer_float(self.ui.pg_prog_vel_curado, por_defecto=0)
        a_cur = _leer_float(self.ui.pg_prog_acel_curado, por_defecto=0)
        d_cur = _leer_float(self.ui.pg_prog_decel_curado, por_defecto=0)

        # impresion: siempre a altura maxima
        if v_impr > 0:
            self._dibujar_perfil(v_impr, a_impr, d_impr, *PERFIL_IMPRESION_DELANTERO,
                                 escala, y_base, altura_max, COLOR_IMPR_DELANTERO)
            self._dibujar_perfil(v_impr, a_impr, d_impr, *PERFIL_IMPRESION_TRASERO,
                                 escala, y_base, altura_max, COLOR_IMPR_TRASERO)

        # curado: altura proporcional a su velocidad respecto a la de impresion
        inicio_cur = _leer_float(self.ui.pg_prog_inicio_curado)
        if v_impr > 0 and v_cur > 0 and inicio_cur is not None:
            altura_cur = altura_max * (v_cur / v_impr)
            self._dibujar_perfil(v_cur, a_cur, d_cur, inicio_cur, FIN_CARRERA_DELANTERO_MM,
                                 escala, y_base, altura_cur, COLOR_CUR_DELANTERO)
            self._dibujar_perfil(v_cur, a_cur, d_cur,
                                 inicio_cur + DESFASE_BORDE_TRASERO_MM, FIN_CARRERA_TRASERO_MM,
                                 escala, y_base, altura_cur, COLOR_CUR_TRASERO)

    # ===== pagina movimientos =====
    def ir_objetivo(self):
        posicion = _leer_float(self.ui.objetivo)
        velocidad = _leer_float(self.ui.vel_objetivo)
        acel = _leer_float(self.ui.aceleracion)
        decel = _leer_float(self.ui.deceleracion)
        if None in (posicion, velocidad, acel, decel):
            return
        self.motor.set_velocidad(velocidad)
        self.motor.set_aceleracion(acel)
        self.motor.set_deceleracion(decel)
        self.motor.mover_a(posicion)

    def home(self):
        self.homing_en_curso = True
        self.motor.habilitar()
        self.motor.home()
        self.secuencia.set_referencia_pendiente(True)   # hasta que confirme
        self.timer_home.start()

    def comprobar_home(self):
        try:
            terminado = self.motor.homing_terminado()
        except Exception as e:
            self.timer_home.stop()
            self.homing_en_curso = False
            print(f"[HOME] Abortado: {e}")
            return

        if terminado:
            self.timer_home.stop()
            self.motor.set_modo(MODO_POSICION)
            self.secuencia.set_referencia_pendiente(False)
            self.homing_en_curso = False
            print(f"[HOME] Referenciado. Posicion = {self.motor.leer_posicion():.2f} mm")

    def _jog(self, velocidad, aceleracion, deceleracion, sentido):
        self.motor.set_velocidad(velocidad)
        self.motor.set_aceleracion(aceleracion)
        self.motor.set_deceleracion(deceleracion)
        self.motor.mover_manual(velocidad, sentido)
        if sentido == SENTIDO_DERECHA:
            self.timer_jog.timeout.connect(self.comprobar_derecha)
        else:
            self.timer_jog.timeout.connect(self.comprobar_izquierda)
        self.timer_jog.start()

    def mov_derecha(self):
        self._jog(VELOCIDAD_JOG_LENTA, ACELERACION_JOG_LENTA, DECELERACION_JOG_LENTA,
                  SENTIDO_DERECHA)

    def mov_izquierda(self):
        self._jog(VELOCIDAD_JOG_LENTA, ACELERACION_JOG_LENTA, DECELERACION_JOG_LENTA,
                  SENTIDO_IZQUIERDA)

    def mov_derecha_rapido(self):
        self._jog(VELOCIDAD_JOG_RAPIDA, ACELERACION_JOG_RAPIDA, DECELERACION_JOG_RAPIDA,
                  SENTIDO_DERECHA)

    def mov_izquierda_rapido(self):
        self._jog(VELOCIDAD_JOG_RAPIDA, ACELERACION_JOG_RAPIDA, DECELERACION_JOG_RAPIDA,
                  SENTIDO_IZQUIERDA)

    def comprobar_derecha(self):
        if self.motor.leer_posicion() >= self.motor.limite_max:
            self.stop_motor()

    def comprobar_izquierda(self):
        if self.motor.leer_posicion() <= self.motor.limite_min:
            self.stop_motor()

    def stop_motor(self):
        self.motor.parar()
        self.timer_jog.stop()
        try:
            self.timer_jog.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass

    def mov_reposo(self):
        self.motor.set_velocidad(VELOCIDAD_REPOSO)
        self.motor.set_aceleracion(ACELERACION_REPOSO)
        self.motor.set_deceleracion(DECELERACION_REPOSO)
        self.motor.mover_a(config.POSICION_REPOSO_MM)

    # ===== persistencia de los campos de la interfaz =====
    def guardar_ajustes(self):
        """Vuelca los campos rellenables a disco."""
        ajustes = {"campos": {}, "modulos": {}, "distancias": {}}
        for nombre in CAMPOS_TEXTO:
            ajustes["campos"][nombre] = getattr(self.ui, nombre).text()
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            ajustes["modulos"][str(i)] = self._combo_modulo(i).currentIndex()
            ajustes["distancias"][str(i)] = self._campo_distancia(i).text()
        try:
            with open(config.RUTA_AJUSTES, "w", encoding="utf-8") as f:
                json.dump(ajustes, f, indent=2)
        except OSError as e:
            print(f"[AJUSTES] No se han podido guardar: {e}")

    def cargar_ajustes(self):
        """Restaura los campos rellenables desde disco."""
        if not os.path.exists(config.RUTA_AJUSTES):
            return
        try:
            with open(config.RUTA_AJUSTES, "r", encoding="utf-8") as f:
                ajustes = json.load(f)
        except (OSError, ValueError) as e:
            print(f"[AJUSTES] No se han podido cargar: {e}")
            return

        for nombre, valor in ajustes.get("campos", {}).items():
            widget = getattr(self.ui, nombre, None)
            if widget is not None:
                widget.setText(valor)
        for clave, indice in ajustes.get("modulos", {}).items():
            widget = getattr(self.ui, f"modulo{clave}", None)
            if widget is not None:
                widget.setCurrentIndex(indice)
        for clave, valor in ajustes.get("distancias", {}).items():
            widget = getattr(self.ui, f"M{clave}D", None)
            if widget is not None:
                widget.setText(valor)
