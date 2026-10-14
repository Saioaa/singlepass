# -*- coding: utf-8 -*-
"""Tinta (sistema IMB por CoAP, tinta.py) en la pagina Movimientos: botones de
estado, temperatura del cabezal y bloque de ajustes TINTA.

Botones IDLE / FLOW / PURGA / RESET (con sus imagenes):
  - verde (RESET en rojo): estado activo segun el IMB
  - naranja parpadeando: estado pedido, a la espera de que el IMB lo confirme
    (si no lo confirma en config.TINTA_CONFIRMACION_S se avisa y se vuelve al
    estado real)
  - sin fondo (el de la app): inactivo
Al arrancar se muestra el ultimo estado conocido (guardado en los ajustes), o
RESET si no hay ninguno, hasta que el IMB diga el real.

Temperatura: la del cabezal por el PMB (cabezal_pmb.py): la real se ve en
tinta_real_temp y la consigna en tinta_temperatura (GUARDAR la envia).

Ajustes (GUARDAR): consigna de temperatura del cabezal (al PMB) y presiones
idle, delta + (inlet) y delta - (outlet) (al IMB). Al conectar se rellenan con lo
que tienen el PMB y el IMB. La presion y la duracion de la purga quedan
deshabilitadas (PENDIENTE: no hay orden conocida para la presion; la duracion
podria ser PUTO, sin confirmar unidades).

Widgets del .ui (pagina movimientos): tinta_idle, tinta_flow, tinta_purge,
tinta_reset, label_botella, tinta_real_temp, tinta_temperatura,
tinta_idlepressure, tinta_inletpressure, tinta_outletpressure,
tinta_purgapressure, tinta_purgatiempo, btn_save_tinta.
"""

import os
import time

from PySide6.QtCore import QLocale, QSize, QTimer
from PySide6.QtGui import QDoubleValidator, QIcon, QPixmap

import config
from tinta import (AJUSTES, ESTADOS, FLOW, IDLE, NOMBRES, PRESION_IDLE, PRESION_INLET,
                   PRESION_OUTLET, PURGE, RESET)

# ===== IMAGENES (en config.CARPETA_IMAGENES) =====
IMAGEN_BOTELLA = "botella.png"
IMAGENES = {IDLE: "IGU-layout_Idle.png", FLOW: "IGU-layout_Flow.png",
            PURGE: "IGU-layout_Purge.png", RESET: "IGU-layout_Off.png"}
BORDE_BOTON_PX = 2                 # la imagen ocupa todo el boton salvo el borde

# ===== COLORES (los de la app) =====
COLOR_INACTIVO = "transparent"     # sin fondo: se ve el de la app
COLOR_HOVER = "rgb(170, 255, 255)"
COLOR_ACTIVO = "#008000"           # verde: estado activo
COLOR_RESET_ACTIVO = "#E30000"     # rojo: RESET activo (mismo rojo que Abort)
COLOR_PEDIDO = "#FF8C00"           # naranja parpadeando: pedido sin confirmar
ESTILO_BOTON = """
QPushButton {{
    background-color: {fondo};
    border: {borde}px solid #333333;
    border-radius: 5px;
    padding: 0px;
}}
QPushButton:hover {{ background-color: {hover}; }}
"""

# ===== TIEMPOS =====
PERIODO_PARPADEO_MS = 500
PERIODO_VIGILANCIA_MS = 1000

# ===== TEMPERATURA Y PRESIONES =====
TEMPERATURA = "temperatura"        # consigna del cabezal (PMB), junto a las presiones
SUFIJO_TEMPERATURA = "ºC"
DECIMALES_TEMPERATURA = 1
TEXTO_SIN_DATO = "--"
DECIMALES_PRESION = 0
TEXTO_PENDIENTE = "Pendiente"

# ===== PERSISTENCIA (clave "tinta" de ajustes.json) =====
CLAVE_ESTADO = "estado"
CLAVE_AJUSTES = "ajustes"


def validador_decimal(minimo, maximo, decimales, padre):
    validador = QDoubleValidator(minimo, maximo, decimales, padre)
    validador.setNotation(QDoubleValidator.StandardNotation)
    validador.setLocale(QLocale(QLocale.English))   # punto decimal
    return validador


def leer_en_rango(campo, minimo, maximo):
    """float del campo si esta dentro de [minimo, maximo]; None si no."""
    try:
        valor = float(campo.text().replace(",", "."))
    except ValueError:
        return None
    return valor if minimo <= valor <= maximo else None


class PaginaTinta:

    def __init__(self, ui, tinta, temperatura, registrar, guardar_ajustes):
        """tinta: Tinta (IMB). temperatura: TemperaturaCabezal (PMB).
        registrar: callable(texto) del registro de la interfaz.
        guardar_ajustes: callable que persiste todo a disco."""
        self.ui = ui
        self.tinta = tinta
        self.temperatura = temperatura
        self._log = registrar
        self._guardar_ajustes = guardar_ajustes
        self._botones = {IDLE: ui.tinta_idle, FLOW: ui.tinta_flow,
                         PURGE: ui.tinta_purge, RESET: ui.tinta_reset}
        self._campos = {TEMPERATURA: ui.tinta_temperatura, PRESION_IDLE: ui.tinta_idlepressure,
                        PRESION_INLET: ui.tinta_inletpressure,
                        PRESION_OUTLET: ui.tinta_outletpressure}
        self._limites = {
            TEMPERATURA: (config.TEMPERATURA_CABEZAL_MIN_C, config.TEMPERATURA_CABEZAL_MAX_C,
                          DECIMALES_TEMPERATURA),
            PRESION_IDLE: (config.PRESION_IDLE_MIN, config.PRESION_IDLE_MAX, DECIMALES_PRESION),
            PRESION_INLET: (config.PRESION_INLET_MIN, config.PRESION_INLET_MAX,
                            DECIMALES_PRESION),
            PRESION_OUTLET: (config.PRESION_OUTLET_MIN, config.PRESION_OUTLET_MAX,
                             DECIMALES_PRESION),
        }
        self._estado = RESET           # ultimo estado conocido (o guardado)
        self._pedido = None            # estado pedido sin confirmar
        self._t_pedido = 0.0
        self._encendido = False        # fase del parpadeo
        self._ajustes = {}             # ultimos ajustes guardados / leidos
        self._consigna_mostrada = None

        self._preparar_botones()
        self._preparar_ajustes()

        self._timer_parpadeo = QTimer(ui.movimientos)
        self._timer_parpadeo.setInterval(PERIODO_PARPADEO_MS)
        self._timer_parpadeo.timeout.connect(self._parpadear)
        self._timer_vigilancia = QTimer(ui.movimientos)
        self._timer_vigilancia.setInterval(PERIODO_VIGILANCIA_MS)
        self._timer_vigilancia.timeout.connect(self._vigilar_pedido)
        self._timer_vigilancia.start()

        tinta.estado_leido.connect(self._estado_leido)
        tinta.ajustes_leidos.connect(self._ajustes_leidos)
        tinta.orden_terminada.connect(self._orden_terminada)
        tinta.orden_sin_respuesta.connect(self._orden_sin_respuesta)
        tinta.conexion_cambiada.connect(self._conexion_cambiada)
        tinta.mensaje.connect(registrar)
        temperatura.lectura.connect(self._lectura_temperatura)
        temperatura.mensaje.connect(registrar)

        self.mostrar_temperatura(None)
        self._pintar()

    # ===== preparacion =====
    def _preparar_botones(self):
        # las rutas del .ui son relativas al Designer: las imagenes se cargan desde codigo
        ruta_botella = os.path.join(config.CARPETA_IMAGENES, IMAGEN_BOTELLA)
        botella = QPixmap(ruta_botella)
        if botella.isNull():
            print(f"[UI] Falta la imagen {ruta_botella}")
        self.ui.label_botella.setPixmap(botella)
        for estado, boton in self._botones.items():
            ruta = os.path.join(config.CARPETA_IMAGENES, IMAGENES[estado])
            if not os.path.exists(ruta):
                print(f"[UI] Falta la imagen {ruta}")
            # como icono la imagen se escala al boton; el escalado de pantalla
            # tambien ajusta el tamano de los iconos
            boton.setIcon(QIcon(ruta))
            lado = min(boton.width(), boton.height()) - 2 * BORDE_BOTON_PX
            boton.setIconSize(QSize(lado, lado))
            boton.setToolTip(NOMBRES[estado])
            boton.clicked.connect(lambda _=False, e=estado: self.pedir(e))

    def _preparar_ajustes(self):
        for clave, campo in self._campos.items():
            minimo, maximo, decimales = self._limites[clave]
            campo.setValidator(validador_decimal(minimo, maximo, decimales, self.ui.movimientos))
        self.ui.tinta_temperatura.setPlaceholderText(SUFIJO_TEMPERATURA)
        for campo in (self.ui.tinta_purgapressure, self.ui.tinta_purgatiempo):
            campo.setEnabled(False)
            campo.setPlaceholderText(TEXTO_PENDIENTE)
        self.ui.btn_save_tinta.clicked.connect(self.guardar)

    # ===== botones de estado =====
    def pedir(self, estado):
        if not self.tinta.conectado:
            self._log("[TINTA] Sistema de tinta no conectado")
            return
        if estado == self._estado and estado != PURGE and self._pedido is None:
            return   # ya esta en ese estado (la purga se puede repetir)
        self._pedido = estado
        self._t_pedido = time.monotonic()
        self._log(f"[TINTA] {NOMBRES[estado]} pedido")
        self.tinta.pedir_estado(estado)
        self._pintar()

    def _estado_leido(self, estado):
        if estado is None:
            return   # texto del IMB no reconocido: queda en el fichero de log
        anterior, self._estado = self._estado, estado
        if self._pedido is not None and estado == self._pedido:
            self._pedido = None
            self._log(f"[TINTA] {NOMBRES[estado]} activo")
        elif estado != anterior and self._pedido is None:
            self._log(f"[TINTA] Estado: {NOMBRES[estado]}")
        if estado != anterior:
            self._guardar_ajustes()
        self._pintar()

    def _orden_terminada(self, descripcion, correcta):
        if not correcta and self._pedido is not None and NOMBRES[self._pedido] in descripcion:
            self._pedido = None
            self._pintar()
        elif descripcion == "ajustes":
            if correcta:
                self._log("[TINTA] Presiones guardadas en el sistema de tinta")

    def _orden_sin_respuesta(self, descripcion):
        if self._pedido is not None:
            self._log(f"[TINTA] Sin respuesta del IMB a {NOMBRES[self._pedido]}: "
                      "se sigue esperando el cambio de estado")

    def _vigilar_pedido(self):
        limite = config.TINTA_CONFIRMACION_S
        if self._pedido is not None and time.monotonic() - self._t_pedido > limite:
            self._log(f"[TINTA] AVISO: el sistema de tinta no ha confirmado "
                      f"{NOMBRES[self._pedido]} en {limite:g} s")
            self._pedido = None
            self._pintar()

    def _conexion_cambiada(self, conectado):
        if not conectado:
            self._pedido = None
            self._pintar()

    # ===== aspecto de los botones =====
    def _pintar(self):
        if self._pedido is not None:
            if not self._timer_parpadeo.isActive():
                self._encendido = True
                self._timer_parpadeo.start()
        else:
            self._timer_parpadeo.stop()
        for estado, boton in self._botones.items():
            if estado == self._pedido:
                fondo = COLOR_PEDIDO if self._encendido else COLOR_INACTIVO
            elif estado == self._estado and self._pedido is None:
                fondo = COLOR_RESET_ACTIVO if estado == RESET else COLOR_ACTIVO
            else:
                fondo = COLOR_INACTIVO
            hoja = ESTILO_BOTON.format(fondo=fondo, hover=COLOR_HOVER, borde=BORDE_BOTON_PX)
            if boton.styleSheet() != hoja:
                boton.setStyleSheet(hoja)

    def _parpadear(self):
        self._encendido = not self._encendido
        self._pintar()

    # ===== temperatura =====
    def _lectura_temperatura(self, real, consigna):
        self.mostrar_temperatura(real)
        # la consigna solo se rellena cuando cambia (no pisa lo que se este editando)
        campo = self.ui.tinta_temperatura
        if consigna is not None and consigna != self._consigna_mostrada and not campo.hasFocus():
            self._consigna_mostrada = consigna
            self._ajustes[TEMPERATURA] = consigna
            campo.setText(f"{consigna:g}")

    def mostrar_temperatura(self, temperatura):
        texto = TEXTO_SIN_DATO if temperatura is None \
            else f"{temperatura:.{DECIMALES_TEMPERATURA}f}"
        self.ui.tinta_real_temp.setText(f"{texto} {SUFIJO_TEMPERATURA}")

    # ===== ajustes =====
    def _ajustes_leidos(self, ajustes):
        self._ajustes.update(ajustes)
        self._mostrar_ajustes(ajustes)
        self._guardar_ajustes()

    def _mostrar_ajustes(self, ajustes):
        for clave, campo in self._campos.items():
            if clave in ajustes and not campo.hasFocus():
                campo.setText(f"{ajustes[clave]:g}")

    def guardar(self):
        valores, erroneos = {}, []
        for clave, campo in self._campos.items():
            minimo, maximo, _ = self._limites[clave]
            valor = leer_en_rango(campo, minimo, maximo)
            if valor is None:
                erroneos.append(f"{clave} ({minimo:g} a {maximo:g})")
            else:
                valores[clave] = valor
        if erroneos:
            self._log(f"[TINTA] Ajustes NO enviados. Revisa: {', '.join(erroneos)}")
            return
        self._ajustes = valores
        self._guardar_ajustes()
        # consigna del cabezal al PMB (avisa ella misma si no esta conectado)
        self._consigna_mostrada = valores[TEMPERATURA]
        self.temperatura.fijar_consigna(valores[TEMPERATURA])
        if not self.tinta.conectado:
            self._log("[TINTA] Sistema de tinta no conectado: presiones no enviadas")
            return
        self._log("[TINTA] Enviando presiones al sistema de tinta...")
        self.tinta.enviar_ajustes({clave: valores[clave] for clave in AJUSTES})

    # ===== persistencia (la gestiona la ventana principal) =====
    def estado(self):
        return {CLAVE_ESTADO: self._estado, CLAVE_AJUSTES: dict(self._ajustes)}

    def restaurar(self, estado):
        estado = estado or {}
        if estado.get(CLAVE_ESTADO) in ESTADOS:
            self._estado = estado[CLAVE_ESTADO]
        ajustes = estado.get(CLAVE_AJUSTES) or {}
        try:
            self._ajustes = {clave: float(ajustes[clave])
                             for clave in (TEMPERATURA,) + AJUSTES if clave in ajustes}
        except (TypeError, ValueError):
            self._ajustes = {}
        self._mostrar_ajustes(self._ajustes)
        self._pintar()
