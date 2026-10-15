# -*- coding: utf-8 -*-
"""Sistema de tinta (IMB) por CoAP, un solo canal (config.CANAL_TINTA).

Mismo modulo que en MBD-F-500. La conexion la abre CoAPIMB_external.setupClient
(la libreria del fabricante, sin modificar). Sus funciones no ponen timeout a las
peticiones (si el IMB no contesta se quedarian esperando para siempre), asi que
aqui se usan las mismas rutas CoAP con su cliente y un timeout.

Todo lo que habla con el IMB va en un unico hilo (el cliente CoAP no admite
peticiones simultaneas):
  - conecta y reconecta cada REINTENTO_CONEXION_S
  - al conectar lee los ajustes (presiones)
  - cada PERIODO_LECTURA_S lee el estado del canal
  - entre lecturas atiende las ordenes de la interfaz (cambio de estado, ajustes)

Estados: idle, flow, purge, reset (la orden "stop" del IMB). Textos exactos del
IMB (con mayusculas): Idle, Flow, Dormant (reset) y HighPressureTimePurge. Se
lee el subestado del canal (/state/sub) y, si no es uno de esos, el estado
superior (/state/top); cada texto nuevo va al fichero de log.

La temperatura no es del IMB (el sensor del tanque no se usa): es la del
cabezal, por el PMB (cabezal_pmb.py).

Ordenes: se envian una vez. Si el IMB no contesta en TIMEOUT_ORDEN_S puede que
la haya recibido igual, asi que no se da por fallida: la interfaz sigue
esperando a ver el estado pedido (config.TINTA_CONFIRMACION_S).

Requiere:  python -m pip install coapthon3==1.0.2   y CoAPIMB_external.py en programa/tinta/.
"""

import queue
import threading
import time

from PySide6.QtCore import QObject, Signal

from programa import config

# ===== ESTADOS =====
IDLE = "idle"
FLOW = "flow"
PURGE = "purge"
RESET = "reset"
ESTADOS = (IDLE, FLOW, PURGE, RESET)
NOMBRES = {IDLE: "IDLE", FLOW: "FLOW", PURGE: "PURGA", RESET: "RESET"}
ORDEN_IMB = {IDLE: "idle", FLOW: "flow", PURGE: "purge", RESET: "stop"}
# texto exacto del IMB -> estado
ESTADOS_IMB = {"Idle": IDLE, "Flow": FLOW, "Dormant": RESET, "HighPressureTimePurge": PURGE}

# ===== AJUSTES =====
PRESION_IDLE = "idle"
PRESION_INLET = "inlet"       # ITPD: presion delta de entrada (+)
PRESION_OUTLET = "outlet"     # OTPD: presion delta de salida (-)
AJUSTES = (PRESION_IDLE, PRESION_INLET, PRESION_OUTLET)

# ===== COAP =====
PUERTO_COAP = 5683
TIMEOUT_S = 3.0               # lecturas
TIMEOUT_ORDEN_S = 10.0        # ordenes y ajustes
CARGA_VACIA = "NULL"
RESPUESTA_VALIDA = "0"

# ===== TEMPORIZACION =====
REINTENTO_CONEXION_S = 10.0
PERIODO_LECTURA_S = 1.0
FALLOS_PARA_DESCONECTAR = 3   # lecturas seguidas sin respuesta


class ErrorTinta(Exception):
    """El IMB no ha contestado o ha rechazado la orden."""


class SinRespuesta(ErrorTinta):
    """El IMB no ha contestado a tiempo (la peticion puede haber llegado)."""


class Tinta(QObject):

    mensaje = Signal(str)
    conexion_cambiada = Signal(bool)
    estado_leido = Signal(object)        # estado (ESTADOS) o None si no se reconoce
    ajustes_leidos = Signal(dict)        # {PRESION_IDLE, ...}: valores del IMB
    orden_terminada = Signal(str, bool)  # (descripcion, correcta)
    orden_sin_respuesta = Signal(str)    # enviada pero sin respuesta: puede haber llegado

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ip = config.IP_TINTA
        self.canal = str(config.CANAL_TINTA)
        self._ordenes = queue.Queue()
        self._activo = False
        self._conectado = False
        self._cliente = None
        self._fallos = 0
        self._textos_vistos = set()

    @property
    def conectado(self):
        return self._conectado

    # ===== interfaz publica (hilo de Qt) =====
    def conectar(self):
        if self._activo:
            return
        self._activo = True
        self.mensaje.emit("[TINTA] Conectando con el sistema de tinta...")
        threading.Thread(target=self._bucle, daemon=True).start()

    def cerrar(self):
        self._activo = False
        self._ordenes.put(None)   # despierta al hilo

    def pedir_estado(self, estado):
        self._ordenes.put(("estado", estado))

    def enviar_ajustes(self, ajustes):
        """ajustes: {PRESION_IDLE, PRESION_INLET, PRESION_OUTLET}."""
        self._ordenes.put(("ajustes", dict(ajustes)))

    # ===== hilo =====
    def _bucle(self):
        avisado = False
        while self._activo:
            if not self._conectado:
                if self._abrir():
                    avisado = False
                    self._cambiar_conexion(True)
                    self._leer_ajustes()
                else:
                    if not avisado:
                        self.mensaje.emit(f"[TINTA] NO conectado ({self.ip}), se reintenta")
                        avisado = True
                    self._descartar_ordenes()
                    self._esperar(REINTENTO_CONEXION_S)
                    continue
            self._leer_estado()
            self._atender_ordenes(PERIODO_LECTURA_S)
        self._cerrar_cliente()

    def _abrir(self):
        try:
            from programa.tinta import CoAPIMB_external as imb
            if imb.setupClient(self.ip, False):
                self._cliente = imb.client
                return True
            imb.client.stop()
        except Exception as e:   # libreria externa: cualquier fallo es "no conectado"
            print(f"[TINTA] Error al conectar: {e}")
        return False

    def _cerrar_cliente(self):
        if self._cliente is not None:
            try:
                self._cliente.stop()
            except Exception:
                pass
            self._cliente = None

    def _cambiar_conexion(self, conectado):
        self._conectado = conectado
        self._fallos = 0
        self.conexion_cambiada.emit(conectado)
        if conectado:
            self.mensaje.emit(f"[TINTA] Conectado en {self.ip}")
        else:
            self.mensaje.emit("[TINTA] Conexion perdida con el sistema de tinta")
            self._cerrar_cliente()

    def _esperar(self, segundos):
        """Espera, pero sale antes si llega cerrar()."""
        try:
            orden = self._ordenes.get(timeout=segundos)
        except queue.Empty:
            return
        if orden is not None:
            self._ordenes.put(orden)

    def _descartar_ordenes(self):
        while True:
            try:
                orden = self._ordenes.get_nowait()
            except queue.Empty:
                return
            if orden is None:
                self._ordenes.put(None)
                return
            self.orden_terminada.emit(self._descripcion(orden), False)
            self.mensaje.emit(f"[TINTA] Sin conexion: '{self._descripcion(orden)}' no enviada")

    # ===== CoAP con timeout =====
    def _get(self, ruta, timeout=TIMEOUT_S):
        respuesta = self._cliente.get(ruta, timeout=timeout)
        if respuesta is None or respuesta.payload is None:
            raise SinRespuesta(f"sin respuesta a {ruta}")
        return respuesta.payload

    def _put(self, ruta, carga=CARGA_VACIA, timeout=TIMEOUT_ORDEN_S):
        respuesta = self._cliente.put(ruta, carga, timeout=timeout)
        if respuesta is None:
            raise SinRespuesta(f"sin respuesta a {ruta}")
        return respuesta.payload

    def _get_numero(self, ruta, escala=1):
        return int(self._get(ruta)) / escala

    # ===== lecturas =====
    def _leer_estado(self):
        try:
            sub = self._get(f"/state/sub?uc={self.canal}")
            estado = self._interpretar(sub)
            if estado is None:
                estado = self._interpretar(self._get(f"/state/top?uc={self.canal}"))
        except (ErrorTinta, ValueError) as e:
            self._fallos += 1
            print(f"[TINTA] Lectura fallida ({self._fallos}): {e}")
            if self._fallos >= FALLOS_PARA_DESCONECTAR:
                self._cambiar_conexion(False)
            return
        self._fallos = 0
        self.estado_leido.emit(estado)

    def _interpretar(self, texto):
        texto = (texto or "").strip()
        if texto not in self._textos_vistos:
            self._textos_vistos.add(texto)
            print(f"[TINTA] Estado del IMB: '{texto}'")
        return ESTADOS_IMB.get(texto)

    def _leer_ajustes(self):
        c = self.canal
        try:
            ajustes = {
                PRESION_IDLE: self._get_numero(f"/fc/{c}/cset/vac/IP/store"),
                PRESION_INLET: self._get_numero(f"/fc/{c}/cset/vac/ITPD/store"),
                PRESION_OUTLET: self._get_numero(f"/fc/{c}/cset/vac/OTPD/store"),
            }
        except (ErrorTinta, ValueError) as e:
            self.mensaje.emit("[TINTA] No se han podido leer los ajustes del sistema de tinta")
            print(f"[TINTA] Ajustes: {e}")
            return
        print(f"[TINTA] Ajustes del IMB: {ajustes}")
        self.ajustes_leidos.emit(ajustes)

    # ===== ordenes =====
    @staticmethod
    def _descripcion(orden):
        tipo, valor = orden
        return f"estado {NOMBRES[valor]}" if tipo == "estado" else "ajustes"

    def _atender_ordenes(self, espera_s):
        limite = time.monotonic() + espera_s
        while self._activo and self._conectado:
            restante = limite - time.monotonic()
            if restante <= 0:
                return
            try:
                orden = self._ordenes.get(timeout=restante)
            except queue.Empty:
                return
            if orden is None:
                return
            descripcion = self._descripcion(orden)
            try:
                if orden[0] == "estado":
                    self._put(f"/cmd/{ORDEN_IMB[orden[1]]}?uc={self.canal}")
                else:
                    self._escribir_ajustes(orden[1])
            except SinRespuesta as e:
                if orden[0] == "estado":   # puede haber llegado: se sigue esperando el estado
                    print(f"[TINTA] {descripcion}: {e}")
                    self.orden_sin_respuesta.emit(descripcion)
                    continue
                self.mensaje.emit(f"[TINTA] AVISO: {descripcion} sin respuesta del IMB")
                self.orden_terminada.emit(descripcion, False)
                continue
            except ErrorTinta as e:
                self.mensaje.emit(f"[TINTA] AVISO: {descripcion} no aceptada: {e}")
                self.orden_terminada.emit(descripcion, False)
                continue
            print(f"[TINTA] {descripcion}: enviada")
            self.orden_terminada.emit(descripcion, True)

    def _escribir_ajustes(self, ajustes):
        """Presiones con la transaccion de validacion del IMB (la de
        CoAPIMB_external.setChannelPressures)."""
        c = self.canal
        presiones = (("IP", ajustes[PRESION_IDLE]), ("ITPD", ajustes[PRESION_INLET]),
                     ("OTPD", ajustes[PRESION_OUTLET]))
        transaccion = self._get(f"/fc/{c}/validate/starttxact")
        for nombre, valor in presiones:
            self._put(f"/fc/{c}/vset/vac/{nombre}/store?tid={transaccion}", str(int(valor)))
        rechazadas = [nombre for nombre, _ in presiones
                      if self._get(f"/fc/{c}/vset/vac/{nombre}/validate?tid={transaccion}")
                      != RESPUESTA_VALIDA]
        fin = self._put(f"/fc/{c}/validate/endtxact?tid={transaccion}")
        if rechazadas:
            raise ErrorTinta(f"el IMB rechaza {', '.join(rechazadas)}")
        if fin != RESPUESTA_VALIDA:
            raise ErrorTinta("el IMB no ha cerrado la validacion")
        for nombre, valor in presiones:
            self._put(f"/fc/{c}/cset/vac/{nombre}/store", str(int(valor)))
        self._put(f"/cmd/applysettings?uc={c}")
