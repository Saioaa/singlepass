# -*- coding: utf-8 -*-
"""Ventana principal: navegacion, pagina de movimientos, tinta, ajustes y escalado.

Los dispositivos (MotorD1, ClienteMDuino, ClientePMB) los crea main.py y
llegan por el constructor. La pagina Print Server vive en print_server.py y la pagina
Programa (secuencia, plan y grafico) en pagina_programa.py.

ui_pantalla_programa.py debe generarse con:
    pyside6-uic interfaz/pantalla_programa.ui -o interfaz/ui_pantalla_programa.py
"""

import ctypes
import json
import os
import re
import sys

from PySide6.QtCore import QLocale, QSize, Qt, QTimer
from PySide6.QtGui import QDoubleValidator, QFont, QFontDatabase, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QDialog, QLabel, QMainWindow, QMessageBox,
                               QVBoxLayout, QWidget)

from programa import config
from programa.d1 import MODO_POSICION
from programa.gis.board_pmb import BoardPMB
from programa.gis.board_epson import BoardEpson
from programa.gis.cabezal_pmb import TemperaturaCabezal
from interfaz.pagina_tinta import PaginaTinta
from interfaz.print_server import MOTIVO_CABEZALES, PrintServer
from programa.tinta.tinta import Tinta
from interfaz.pagina_programa import TIPO_AEWA, PaginaPrograma
from programa.secuencia import SecuenciaImpresion
from interfaz.ui_pantalla_programa import Ui_MainWindow

# ===== IDENTIDAD DE LA APLICACION =====
TITULO_VENTANA = "MATERIALIGHT"
ICONO_APP      = "M_02.ico"           # en config.CARPETA_IMAGENES: barra de titulo y barra de tareas
# Windows agrupa las ventanas en la barra de tareas por este identificador; sin el,
# una app lanzada con python.exe hereda el icono de Python en lugar del suyo.
ID_APP_WINDOWS = "Materialight.Singlepass"
# Fuente de la interfaz: el .ui la pide por hoja de estilo (font-family: nunito).
# Se cargan los .ttf de config.CARPETA_FUENTES para no depender de que este
# instalada en el PC.
EXTENSIONES_FUENTE = (".ttf", ".otf")

# ===== CIERRE CON IMPRESION EN CURSO =====
AVISO_CERRAR_TITULO = "CERRAR LA APLICACIÓN"
AVISO_CERRAR_IMPRIMIENDO = ("Hay una impresión en curso: si cierra la aplicación se detendrá.\n\n"
                            "¿Cerrar la aplicación de todos modos?")

# ===== ACCESO A LAS PAGINAS PRINT SERVER =====
# Cada pagina solo se abre si en Programa hay algun cabezal activo de su familia:
# GIS (PMB-C8, PMB-C2, SM-200: lo dicen las boards) o AEWA (APMB4). Si no, su
# boton queda deshabilitado con este aspecto (se anade a la hoja del .ui).
ESTILO_BOTON_DESHABILITADO = """
QPushButton:disabled { background-color: #2E3837; color: #6F7F7D; border-color: #2E3837; }"""

# ===== MODULOS DE LA BARRA (para la persistencia de ajustes) =====
PRIMER_MODULO = 1
ULTIMO_MODULO = 8

# ===== SECUENCIA =====
SIN_TOLERANCIA_REPOSO = 0.0   # con PD por hardware la mesa va siempre a reposo antes del PULSE

# ===== CAMPOS DE TEXTO QUE SE GUARDAN ENTRE SESIONES =====
CLAVE_AJUSTES_TINTA = "tinta"   # estado y ajustes de la tinta (pagina_tinta.estado())
CAMPOS_TEXTO = [
    "objetivo", "vel_objetivo", "aceleracion", "deceleracion",
    "pg_prog_vel_impresion", "pg_prog_acel_impresion", "pg_prog_decel_impresion",
    "pg_prog_vel_curado", "pg_prog_acel_curado", "pg_prog_decel_curado",
    "pg_prog_cant_pasadas_curado", "pg_prog_potencia_NIR", "pg_prog_potencia_secador",
]

# ===== VENTANA DE PARADA DE EMERGENCIA =====
EMERGENCIA_TITULO    = "PARADA DE EMERGENCIA"
EMERGENCIA_SUBTITULO = "Rearme para continuar"
EMERGENCIA_IMAGEN    = "emergency_2.png"
EMERGENCIA_LADO_PX   = 260
EMERGENCIA_MARGEN_PX = 40
EMERGENCIA_ESPACIADO_PX = 20
EMERGENCIA_ESTILO = """
QDialog { background-color: #B71C1C; border: 6px solid #FFD600; border-radius: 16px; }
QDialog QLabel { background-color: transparent; border: none; }
QLabel#titulo { color: #FFFFFF; font-size: 34px; font-weight: bold; }
QLabel#subtitulo { color: #FFF59D; font-size: 18px; }
"""
# la ventana hereda la hoja de estilo de la principal (fondos azules de los QLabel):
# la regla "QDialog QLabel" los anula dentro del dialogo

# ===== ESCALADO A LA VENTANA =====
# El .ui esta disenado con geometrias absolutas; el tamano de diseno es el de la
# ventana en el .ui (MainWindow -> geometry), asi que si se cambia en el Designer
# no hay que tocar nada aqui. La interfaz se reescala a la ventana cada vez que
# cambia de tamano (maximizar, restaurar, arrastrar el borde).
TOLERANCIA_ESCALA = 0.01
PATRON_PIXELES = re.compile(r"(\d+)px")
RETARDO_REESCALADO_MS = 150    # tras el ultimo cambio de tamano de la ventana
ESCALA_MINIMA = 0.4            # tamano minimo de la ventana respecto al diseno


class DisenoWidget:
    """Valores de diseno de un widget (antes de escalar) y la ultima hoja aplicada."""

    def __init__(self, geometria, hoja, puntos, icono):
        self.geometria = geometria
        self.hoja = hoja
        self.hoja_aplicada = hoja
        self.puntos = puntos
        self.icono = icono

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


class VentanaEmergencia(QDialog):
    """Bloquea toda la aplicacion mientras la seta esta pulsada. Sin borde, siempre
    encima, y sin forma de cerrarla desde teclado o raton: solo la cierra ocultar()
    cuando el M-Duino informa de que la seta se ha liberado."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet(EMERGENCIA_ESTILO)

        imagen = QLabel()
        imagen.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(os.path.join(config.CARPETA_IMAGENES, EMERGENCIA_IMAGEN))
        if not pixmap.isNull():
            imagen.setPixmap(pixmap.scaled(EMERGENCIA_LADO_PX, EMERGENCIA_LADO_PX,
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation))
        titulo = QLabel(EMERGENCIA_TITULO)
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        subtitulo = QLabel(EMERGENCIA_SUBTITULO)
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignCenter)

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(EMERGENCIA_MARGEN_PX, EMERGENCIA_MARGEN_PX,
                                       EMERGENCIA_MARGEN_PX, EMERGENCIA_MARGEN_PX)
        disposicion.setSpacing(EMERGENCIA_ESPACIADO_PX)
        disposicion.addWidget(imagen)
        disposicion.addWidget(titulo)
        disposicion.addWidget(subtitulo)

    def reject(self):
        pass   # Esc

    def closeEvent(self, evento):
        evento.ignore()   # Alt+F4 / gestor de ventanas

    def keyPressEvent(self, evento):
        evento.ignore()

    def mostrar(self):
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()
        pantalla = self.screen().availableGeometry()
        self.move(pantalla.center() - self.rect().center())

    def ocultar(self):
        self.hide()


class VentanaPrincipal(QMainWindow):

    def __init__(self, motor, mduino, pmb):
        super().__init__()
        self._cargar_fuentes()   # antes de setupUi: las hojas de estilo del .ui la usan
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._tamano_diseno = self.size()   # el de MainWindow en el .ui
        self._diseno = {}
        self._poner_identidad()

        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))

        # ===== dispositivos (creados en main.py) =====
        self.motor = motor
        self.mduino = mduino
        self.pmb = pmb

        # ===== paginas y secuencias =====
        # boards de impresion: una por familia de cabezal (board.tipos_modulo)
        self.boards = [BoardPMB(self.pmb, parent=self), BoardEpson(parent=self)]
        self.print_server = PrintServer(self.ui, self.boards,
                                        cabezales_activos=lambda: self.pagina_programa.cabezales_activos(),
                                        posicion_eje=lambda: self.posicion_mm,
                                        iniciar_programa=lambda: self.pagina_programa.start(),
                                        parar_programa=lambda: self.pagina_programa.stop(),
                                        programa_en_marcha=lambda: self.secuencia.en_marcha(),
                                        parent=self)
        print_go_extra = self.print_server.print_go_software if config.PRINT_GO_TAMBIEN_POR_SOFTWARE else None
        tolerancia_reposo = (config.TOLERANCIA_REPOSO_MM if config.PRINT_GO_TAMBIEN_POR_SOFTWARE
                             else SIN_TOLERANCIA_REPOSO)
        self.secuencia = SecuenciaImpresion(self.motor, self.mduino,
                                            self.print_server.esta_lista,
                                            config.POSICION_REPOSO_MM,
                                            print_go_extra=print_go_extra,
                                            tolerancia_reposo=tolerancia_reposo, parent=self)
        if config.PRINT_GO_TAMBIEN_POR_SOFTWARE:
            print("[CONFIG] PROVISIONAL: print go tambien por software (P,SPG)")
        self.secuencia.terminada.connect(self.print_server.programa_terminado)
        self.mduino.seta_cambiada.connect(self.secuencia.set_seta)
        self.mduino.seta_cambiada.connect(self.seta_cambiada)
        self.seta_pulsada = False
        self.ventana_emergencia = VentanaEmergencia(self)

        self.homing_en_curso = False   # impide leer la posicion durante el homing
        self.posicion_mm = None        # ultima posicion leida del D1

        # ===== tinta (IMB por CoAP) y temperatura del cabezal (PMB) =====
        self.tinta = Tinta(parent=self)
        self.temperatura = TemperaturaCabezal(self.pmb, parent=self)
        self.pagina_tinta = PaginaTinta(self.ui, self.tinta, self.temperatura,
                                        registrar=self.print_server.registrar,
                                        guardar_ajustes=self.guardar_ajustes)

        self.pagina_programa = PaginaPrograma(
            self.ui, self.secuencia, self.mduino,
            boards_listas=self.print_server.esta_lista,
            abortar_boards=self.print_server.abortar_boards,
            geometria_imagen=self.print_server.geometria_imagen,
            posicion_real=lambda: self.posicion_mm,
            registrar=self.print_server.registrar,
            parent=self)
        self.pagina_programa.cabezales_cambiados.connect(
            lambda: self.print_server.invalidar_render(MOTIVO_CABEZALES))

        # ===== navegacion =====
        self.ui.bt_pg_movimientos1.clicked.connect(self.ir_pg_movimientos)
        self.ui.bt_pg_movimientos2.clicked.connect(self.ir_pg_movimientos)
        self.ui.bt_pg_menu.clicked.connect(self.ir_pg_menu)
        self.ui.bt_pg_programa.clicked.connect(self.ir_pg_programa)
        self.ui.bt_pg_programa_2.clicked.connect(self.ir_pg_programa)
        self.ui.bt_pg_printserver_gis.clicked.connect(self.print_server.entrar)
        self.ui.bt_pg_printserver_aewa.clicked.connect(self.ir_pg_printserver_aewa)
        for boton in (self.ui.bt_pg_printserver_gis, self.ui.bt_pg_printserver_aewa):
            boton.setStyleSheet(boton.styleSheet() + ESTILO_BOTON_DESHABILITADO)
        self.pagina_programa.cabezales_cambiados.connect(self._actualizar_accesos_print_server)

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
        self._vigilante_jog = None   # funcion conectada al timeout durante un jog

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
        self._actualizar_accesos_print_server()   # con o sin ajustes guardados
        self.tinta.conectar()

    # ===== fuente =====
    @staticmethod
    def _cargar_fuentes():
        carpeta = config.CARPETA_FUENTES
        if not os.path.isdir(carpeta):
            print(f"[UI] Sin carpeta de fuentes {carpeta}: se usa la del sistema")
            return
        familias = []
        for nombre in sorted(os.listdir(carpeta)):
            if not nombre.lower().endswith(EXTENSIONES_FUENTE):
                continue
            indice = QFontDatabase.addApplicationFont(os.path.join(carpeta, nombre))
            if indice < 0:
                print(f"[UI] No se ha podido cargar la fuente {nombre}")
                continue
            familias.extend(QFontDatabase.applicationFontFamilies(indice))
        if familias:
            # tambien para lo que no lleva hoja de estilo (dialogos, mensajes)
            QGuiApplication.setFont(QFont(familias[0]))
            print(f"[UI] Fuente cargada: {', '.join(dict.fromkeys(familias))}")

    # ===== identidad =====
    def _poner_identidad(self):
        """Titulo e icono de la ventana (barra de titulo y barra de tareas)."""
        self.setWindowTitle(TITULO_VENTANA)
        ruta = os.path.join(config.CARPETA_IMAGENES, ICONO_APP)
        if not os.path.exists(ruta):
            print(f"[UI] Falta el icono {ruta}")
            return
        if sys.platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP_WINDOWS)
        icono = QIcon(ruta)
        self.setWindowIcon(icono)
        QGuiApplication.setWindowIcon(icono)   # tambien dialogos y ventanas secundarias

    # ===== escalado =====
    def ajustar_a_pantalla(self):
        """Captura el diseno y escala la interfaz a la pantalla. Despues,
        _reescalar se aplica solo cada vez que la ventana cambia de tamano."""
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self._capturar_diseno()
        self.setMinimumSize(round(self._tamano_diseno.width() * ESCALA_MINIMA),
                            round(self._tamano_diseno.height() * ESCALA_MINIMA))
        self.resize(pantalla.size())
        self._reescalar()
        print(f"[UI] Pantalla {pantalla.width()}x{pantalla.height()}, diseno "
              f"{self._tamano_diseno.width()}x{self._tamano_diseno.height()}")

    def _capturar_diseno(self):
        """Guarda, una sola vez, geometria, hoja, fuente e icono de diseno de cada
        widget (los del .ui y los creados por las paginas)."""
        self._diseno = {}
        for widget in self.findChildren(QWidget):
            if widget is self.centralWidget():
                continue   # lo coloca QMainWindow
            fuente = widget.font()
            icono = widget.iconSize() if isinstance(widget, QAbstractButton) \
                and not widget.icon().isNull() else None
            self._diseno[widget] = DisenoWidget(widget.geometry(), widget.styleSheet(),
                                                fuente.pointSizeF(), icono)
        self._factores = (1.0, 1.0)
        self._timer_escala = QTimer(self)
        self._timer_escala.setSingleShot(True)
        self._timer_escala.setInterval(RETARDO_REESCALADO_MS)
        self._timer_escala.timeout.connect(self._reescalar)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        timer = getattr(self, "_timer_escala", None)
        if timer is not None:
            timer.start()   # durante el arrastre del borde solo se escala al final

    def _reescalar(self):
        """Geometrias: cada eje con su factor (ventana / diseno), para llenar la
        ventana aunque su proporcion no sea la del diseno. Textos, bordes e
        iconos: con el menor, para que no se deformen. Siempre desde los valores
        de diseno, asi no se acumula redondeo. Las hojas que las paginas cambian
        en marcha (Print parpadeando, botones de tinta...) se conservan: si
        empiezan por la ultima escalada se reescala solo esa parte; si la han
        sustituido entera, se reescalan sus px en proporcion al cambio."""
        if not self._diseno:
            return
        ancho_diseno, alto_diseno = self._tamano_diseno.width(), self._tamano_diseno.height()
        area = self.size()   # sin barra de menus ni de estado: todo es el widget central
        factor_x = area.width() / ancho_diseno
        factor_y = area.height() / alto_diseno
        anterior = min(self._factores)
        if abs(factor_x - self._factores[0]) < TOLERANCIA_ESCALA \
                and abs(factor_y - self._factores[1]) < TOLERANCIA_ESCALA:
            return
        factor = min(factor_x, factor_y)
        self._factores = (factor_x, factor_y)

        def px(valor, f=factor):
            # un 0 se queda en 0 y lo demas no baja de 1 (un borde no desaparece)
            return 0 if valor == 0 else max(1, round(valor * f))

        def escalar_hoja(hoja, f):
            return PATRON_PIXELES.sub(lambda m: f"{px(int(m.group(1)), f)}px", hoja)

        for widget, diseno in list(self._diseno.items()):
            try:
                g = diseno.geometria
                widget.setGeometry(px(g.x(), factor_x), px(g.y(), factor_y),
                                   px(g.width(), factor_x), px(g.height(), factor_y))
            except RuntimeError:   # widget ya destruido
                del self._diseno[widget]
                continue
            actual = widget.styleSheet()
            if actual.startswith(diseno.hoja_aplicada):
                base = escalar_hoja(diseno.hoja, factor)
                nueva = base + actual[len(diseno.hoja_aplicada):]
                diseno.hoja_aplicada = base
            else:
                nueva = escalar_hoja(actual, factor / anterior)
            if nueva != actual:
                widget.setStyleSheet(nueva)
            if diseno.puntos > 0:
                fuente = widget.font()
                fuente.setPointSizeF(diseno.puntos * factor)
                widget.setFont(fuente)
            if diseno.icono is not None:
                widget.setIconSize(QSize(px(diseno.icono.width()), px(diseno.icono.height())))
        print(f"[UI] Interfaz escalada x{factor_x:.3f} / y{factor_y:.3f} "
              f"({area.width()}x{area.height()})")

    # ===== cierre =====
    def closeEvent(self, evento):
        if self.secuencia.en_marcha():
            respuesta = QMessageBox.question(self, AVISO_CERRAR_TITULO, AVISO_CERRAR_IMPRIMIENDO,
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if respuesta != QMessageBox.Yes:
                evento.ignore()
                return
            self.print_server.abortar()   # para la secuencia y desarma las boards
        self.guardar_ajustes()
        self.temperatura.cerrar()
        self.tinta.cerrar()
        for board in self.boards:
            if hasattr(board, "cerrar"):
                board.cerrar()   # Epson: apaga cabezales y host board del HMB
        super().closeEvent(evento)

    # ===== accesos a widgets repetidos =====
    def _combo_modulo(self, i):
        return self.pagina_programa.combo_modulo(i)

    def _campo_distancia(self, i):
        return self.pagina_programa.campo_distancia(i)

    # ===== navegacion =====
    def ir_pg_printserver_aewa(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.print_server_aewa)

    def _actualizar_accesos_print_server(self):
        """Habilita cada boton Print Server segun los cabezales activos en Programa."""
        tipos = {tipo for tipo, _x in self.pagina_programa.cabezales_activos()}
        tipos_gis = {tipo for board in self.boards for tipo in board.tipos_modulo}
        self.ui.bt_pg_printserver_gis.setEnabled(bool(tipos & tipos_gis))
        self.ui.bt_pg_printserver_aewa.setEnabled(TIPO_AEWA in tipos)

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

    # ===== seta de emergencia =====
    def seta_cambiada(self, pulsada):
        """La secuencia se para sola (paro_seta); aqui se paran los movimientos
        manuales, se abortan las boards armadas y se bloquea la app hasta
        liberar la seta y volver a referenciar."""
        if pulsada == self.seta_pulsada:
            return   # el M-Duino repite el estado cada segundo
        self.seta_pulsada = pulsada
        if pulsada:
            self.stop_motor()
            self.timer_home.stop()
            self.homing_en_curso = False
            print("[SEGURIDAD] Parada de emergencia: movimientos bloqueados")   # en pantalla ya esta la ventana
            if self.print_server.esta_lista():
                self.print_server.abortar()   # la impresion no se reanuda: se empieza de nuevo
            self.ventana_emergencia.mostrar()
        else:
            self.ventana_emergencia.ocultar()
            self.print_server.registrar("[SEGURIDAD] Home para continuar")

    def _orden_motor(self, descripcion, orden):
        """Ejecuta una orden manual al D1 y, si falla (fallo del variador, sin acuse
        tras una seta...), lo deja en el registro en vez de en un traceback."""
        try:
            orden()
            return True
        except Exception as e:
            self.print_server.registrar(f"[MOTOR] No se ha podido {descripcion}: {e}. "
                                        "Haz Home y vuelve a intentarlo")
            return False

    def _movimiento_permitido(self):
        if self.seta_pulsada:
            print("[SEGURIDAD] Movimiento ignorado: parada de emergencia activa")
            return False
        return True

    # ===== pagina movimientos =====
    def ir_objetivo(self):
        if not self._movimiento_permitido():
            return
        posicion = _leer_float(self.ui.objetivo)
        velocidad = _leer_float(self.ui.vel_objetivo)
        acel = _leer_float(self.ui.aceleracion)
        decel = _leer_float(self.ui.deceleracion)
        if None in (posicion, velocidad, acel, decel):
            return
        def mover():
            self.motor.set_velocidad(velocidad)
            self.motor.set_aceleracion(acel)
            self.motor.set_deceleracion(decel)
            self.motor.mover_a(posicion)
        self._orden_motor("ir al objetivo", mover)

    def home(self):
        if not self._movimiento_permitido():
            return
        self.homing_en_curso = True
        self.secuencia.set_referencia_pendiente(True)   # hasta que confirme

        def lanzar():
            self.motor.habilitar()
            self.motor.home()
        if self._orden_motor("lanzar el home", lanzar):
            self.timer_home.start()
        else:
            self.homing_en_curso = False

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
        if not self._movimiento_permitido():
            return
        def mover():
            self.motor.set_velocidad(velocidad)
            self.motor.set_aceleracion(aceleracion)
            self.motor.set_deceleracion(deceleracion)
            self.motor.mover_manual(velocidad, sentido)
        if not self._orden_motor("mover manualmente", mover):
            return
        self._vigilante_jog = self.comprobar_derecha if sentido == SENTIDO_DERECHA else self.comprobar_izquierda
        self.timer_jog.timeout.connect(self._vigilante_jog)
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
        self._orden_motor("parar", self.motor.parar)
        self.timer_jog.stop()
        if self._vigilante_jog is not None:
            self.timer_jog.timeout.disconnect(self._vigilante_jog)
            self._vigilante_jog = None

    def mov_reposo(self):
        if not self._movimiento_permitido():
            return
        def mover():
            self.motor.set_velocidad(VELOCIDAD_REPOSO)
            self.motor.set_aceleracion(ACELERACION_REPOSO)
            self.motor.set_deceleracion(DECELERACION_REPOSO)
            self.motor.mover_a(config.POSICION_REPOSO_MM)
        self._orden_motor("ir a reposo", mover)

    # ===== persistencia de los campos de la interfaz =====
    def guardar_ajustes(self):
        """Vuelca los campos rellenables a disco."""
        ajustes = {"campos": {}, "modulos": {}, "distancias": {}, "activos": {},
                   CLAVE_AJUSTES_TINTA: self.pagina_tinta.estado()}
        for nombre in CAMPOS_TEXTO:
            ajustes["campos"][nombre] = getattr(self.ui, nombre).text()
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            ajustes["modulos"][str(i)] = self._combo_modulo(i).currentIndex()
            ajustes["distancias"][str(i)] = self._campo_distancia(i).text()
            check = self.pagina_programa.check_modulo(i)
            if check is not None:
                ajustes["activos"][str(i)] = check.isChecked()
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
        for clave, activo in ajustes.get("activos", {}).items():
            widget = getattr(self.ui, f"M{clave}Check", None)
            if widget is not None:
                widget.setChecked(bool(activo))
        self.pagina_tinta.restaurar(ajustes.get(CLAVE_AJUSTES_TINTA))
