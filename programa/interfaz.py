# -*- coding: utf-8 -*-
"""Ventana principal: navegacion, pagina de movimientos, ajustes y escalado.

Los dispositivos (MotorD1, ClienteMDuino, ClientePMB) los crea main.py y
llegan por el constructor. La pagina PMB-8 vive en pagina_pmb.py y la pagina
Programa (secuencia, plan y grafico) en pagina_programa.py.

ui_pantalla_programa.py debe generarse con:
    pyside6-uic pantalla_programa.ui -o ui_pantalla_programa.py
"""

import json
import os
import re

from PySide6.QtCore import QLocale, QSize, QTimer
from PySide6.QtGui import QDoubleValidator, QGuiApplication, QIcon
from PySide6.QtWidgets import QAbstractButton, QMainWindow, QWidget

import config
from d1 import MODO_POSICION
from pagina_pmb import PaginaPMB
from pagina_programa import PaginaPrograma
from secuencia import SecuenciaImpresion
from ui_pantalla_programa import Ui_MainWindow

# ===== MODULOS DE LA BARRA (para la persistencia de ajustes) =====
PRIMER_MODULO = 1
ULTIMO_MODULO = 8

# ===== CAMPOS DE TEXTO QUE SE GUARDAN ENTRE SESIONES =====
CAMPOS_TEXTO = [
    "objetivo", "vel_objetivo", "aceleracion", "deceleracion",
    "pg_prog_vel_impresion", "pg_prog_acel_impresion", "pg_prog_decel_impresion",
    "pg_prog_vel_curado", "pg_prog_acel_curado", "pg_prog_decel_curado",
    "pg_prog_cant_pasadas_curado",
]

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
# iconos de los botones de jog: se cargan desde codigo porque Designer reescribe
# las rutas relativas del .ui segun desde donde se abra
ICONOS_JOG = {
    "bt_mov_izquierda_rapido": "doble_flecha_izquierda.png",
    "bt_mov_izquierda":        "play_redondeado_izquierda.png",
    "bt_mov_derecha":          "play_redondeado_derecha.png",
    "bt_mov_derecha_rapido":   "doble_flecha_derecha.png",
}

# ===== TEMPORIZADORES (ms) =====
PERIODO_VIGILANCIA_JOG    = 50    # comprobacion de limites durante el jog
PERIODO_SONDEO_HOMING     = 100   # vigilancia del homing
PERIODO_REFRESCO_POSICION = 100   # refresco de la posicion (campo y mesa del grafico)
PERIODO_LATIDO            = 500   # lectura ligera para que el D1 no cierre la sesion

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

        # ===== paginas y secuencias =====
        self.pagina_pmb = PaginaPMB(self.ui, self.pmb, self.posicion_cabezal,
                                    posicion_eje=lambda: self.posicion_mm, parent=self)
        print_go_extra = self.pmb.print_go_software if config.PRINT_GO_TAMBIEN_POR_SOFTWARE else None
        self.secuencia = SecuenciaImpresion(self.motor, self.mduino,
                                            self.pagina_pmb.esta_lista,
                                            config.POSICION_REPOSO_MM,
                                            print_go_extra=print_go_extra, parent=self)
        if config.PRINT_GO_TAMBIEN_POR_SOFTWARE:
            print("[CONFIG] PROVISIONAL: print go tambien por software (P,SPG)")
        self.mduino.seta_cambiada.connect(self.secuencia.set_seta)

        self.homing_en_curso = False   # impide leer la posicion durante el homing
        self.posicion_mm = None        # ultima posicion leida del D1

        self.pagina_programa = PaginaPrograma(
            self.ui, self.secuencia, self.mduino,
            pmb_lista=self.pagina_pmb.esta_lista,
            abortar_pmb=self.pagina_pmb.abortar,
            geometria_imagen=self.pagina_pmb.geometria_imagen,
            posicion_real=lambda: self.posicion_mm,
            registrar=self.pagina_pmb.registrar,
            parent=self)

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

        for nombre_boton, archivo in ICONOS_JOG.items():
            ruta = os.path.join(config.CARPETA_IMAGENES, archivo)
            if os.path.exists(ruta):
                getattr(self.ui, nombre_boton).setIcon(QIcon(ruta))
            else:
                print(f"[UI] Falta el icono {ruta}")

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
            if isinstance(widget, QAbstractButton) and not widget.icon().isNull():
                icono = widget.iconSize()
                widget.setIconSize(QSize(px(icono.width()), px(icono.height())))

        self.resize(px(ANCHO_DISENO_PX), px(ALTO_DISENO_PX))
        print(f"[UI] Interfaz escalada x{factor:.2f} para {pantalla.width()}x{pantalla.height()}")

    # ===== cierre =====
    def closeEvent(self, evento):
        self.guardar_ajustes()
        super().closeEvent(evento)

    # ===== accesos a widgets repetidos =====
    def _combo_modulo(self, i):
        return self.pagina_programa.combo_modulo(i)

    def _campo_distancia(self, i):
        return self.pagina_programa.campo_distancia(i)

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
        if self.homing_en_curso:
            return   # durante el homing la posicion no es valida
        try:
            self.posicion_mm = self.motor.leer_posicion()
            self.ui.posicion.setText(f"{self.posicion_mm:.2f}")
        except Exception as e:
            self.ui.posicion.setText("---")
            print(f"[POSICION] Lectura fallida: {e}")
            self.timer_posicion.stop()

    def posicion_cabezal(self):
        return self.pagina_programa.posicion_cabezal()

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
