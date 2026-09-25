# -*- coding: utf-8 -*-
"""Comunicacion con el M-Duino (cliente TCP, protocolo de lineas de texto).

Extraido de programa_impresora.py (bucle_tcp / procesar_linea / enviar_mduino)
y convertido a QObject con senales, igual que pmb.py.

Mensajes que envia el programa:   "PULSE", "LAMP:<pwm>"
Mensajes que recibe del M-Duino:  "SETA:1", "SETA:0"
    seta_cambiada(True/False) se emite al cambiar y con cada latido

Uso:
    self.mduino = ClienteMDuino()
    self.mduino.seta_cambiada.connect(self.secuencia.set_seta)
    self.mduino.iniciar()
"""

import socket
import threading
import time

from PySide6.QtCore import QObject, Signal

# ===== PROTOCOLO =====
TERMINADOR       = "\n"
CMD_PULSO        = "PULSE"
CMD_LAMPARAS     = "LAMP"
MSG_SETA_PULSADA = "SETA:1"
MSG_SETA_LIBRE   = "SETA:0"
PWM_APAGADAS     = 0
# El sketch del M-Duino solo adopta al cliente cuando este envia algo (server.available()).
# Al conectar se manda una orden inofensiva para que nos adopte y empiece a enviar SETA/REF.
MENSAJE_PRESENTACION = f"{CMD_LAMPARAS}:{PWM_APAGADAS}"

# ===== CONEXION =====
TAM_BUFFER         = 64    # bytes por lectura
RETARDO_RECONEXION = 2     # s entre intentos
TIMEOUT_CONEXION   = 5     # s por intento (Windows tarda ~21 s si no se acota)
PERIODO_TRAZA_S    = 5     # s entre trazas en consola de un mismo mensaje repetido (latido)


class ClienteMDuino(QObject):
    """Cliente TCP del M-Duino. Reconecta solo si se cae la conexion."""

    conexion_cambiada = Signal(bool)   # True al conectar, False al perder la conexion
    seta_cambiada     = Signal(bool)   # True = seta pulsada
    linea_recibida    = Signal(str)    # cualquier linea, para el registro de la interfaz
    mensaje_enviado   = Signal(str)    # cada comando que sale hacia el M-Duino

    def __init__(self, ip, puerto, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.puerto = puerto
        self.sock = None
        self._hilo = None
        self._activo = False
        self._intentos = 0
        self._traza = {}   # clave (SETA, REF...) -> (ultimo valor, instante de la ultima traza)

    # ----- conexion -----

    def iniciar(self):
        """Arranca el hilo de lectura. No bloquea."""
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def cerrar(self):
        """Cierra la conexion de forma ordenada (FIN al M-Duino) al salir de la app.
        Si se sale sin esto, un Arduino con un unico cliente puede quedarse
        creyendo que seguimos conectados y rechazar la siguiente conexion."""
        self._activo = False
        sock, self.sock = self.sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def esta_conectado(self):
        return self.sock is not None

    def _bucle(self):
        while self._activo:
            sock = None
            try:
                self._intentos += 1
                sock = socket.create_connection((self.ip, self.puerto), timeout=TIMEOUT_CONEXION)
                sock.settimeout(None)
                self.sock = sock
                print(f"[MDUINO] Conectado a {self.ip}:{self.puerto} (intento {self._intentos})")
                self.conexion_cambiada.emit(True)
                self.enviar(MENSAJE_PRESENTACION)
                self._leer(sock)
                print("[MDUINO] El M-Duino ha cerrado la conexion")
            except OSError as e:
                if self._activo:
                    print(f"[MDUINO] Sin conexion (intento {self._intentos}): {e}")
            finally:
                if sock is not None:
                    sock.close()
            if self.sock is not None:
                self.sock = None
                self._traza.clear()
                self.conexion_cambiada.emit(False)
            if self._activo:
                time.sleep(RETARDO_RECONEXION)

    def _leer(self, sock):
        pendiente = ""
        while True:
            datos = sock.recv(TAM_BUFFER)
            if not datos:
                return
            pendiente += datos.decode("utf-8", errors="replace")
            while TERMINADOR in pendiente:
                linea, pendiente = pendiente.split(TERMINADOR, 1)
                self._procesar_linea(linea.strip())

    # ----- recepcion -----

    def _procesar_linea(self, linea):
        if not linea:
            return
        # el M-Duino repite SETA/REF cada segundo: se traza si cambia o cada PERIODO_TRAZA_S
        clave = linea.split(":", 1)[0]
        valor_anterior, instante = self._traza.get(clave, (None, 0.0))
        ahora = time.monotonic()
        if linea != valor_anterior or ahora - instante >= PERIODO_TRAZA_S:
            self._traza[clave] = (linea, ahora)
            print(f"[MDUINO] <- {linea}")
        self.linea_recibida.emit(linea)
        if linea == MSG_SETA_PULSADA:
            self.seta_cambiada.emit(True)
        elif linea == MSG_SETA_LIBRE:
            self.seta_cambiada.emit(False)

    # ----- envio -----

    def enviar(self, mensaje):
        if self.sock is None:
            print(f"[MDUINO] Sin conexion, descartado: {mensaje}")
            return False
        try:
            self.sock.sendall((mensaje + TERMINADOR).encode("utf-8"))
            print(f"[MDUINO] -> {mensaje}")
            self.mensaje_enviado.emit(mensaje)
            return True
        except OSError as e:
            print(f"[MDUINO] Error enviando {mensaje}: {e}")
            return False

    def pulso_impresion(self):
        """Pide el pulso de print start."""
        return self.enviar(CMD_PULSO)

    def lamparas(self, pwm):
        """Fija el PWM de las lamparas (0 = apagadas)."""
        return self.enviar(f"{CMD_LAMPARAS}:{pwm}")
