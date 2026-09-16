# -*- coding: utf-8 -*-
"""Comunicacion con el M-Duino (cliente TCP, protocolo de lineas de texto).

Extraido de programa_impresora.py (bucle_tcp / procesar_linea / enviar_mduino)
y convertido a QObject con senales, igual que pmb.py.

Mensajes que envia el programa:   "PULSE", "LAMP:<pwm>"
Mensajes que recibe del M-Duino:  "SETA:1", "SETA:0"
    (la emision de seta_cambiada esta comentada en _procesar_linea hasta
     que el M-Duino este conectado fisicamente)

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

# ===== CONEXION =====
TAM_BUFFER         = 64    # bytes por lectura
RETARDO_RECONEXION = 2     # s


class ClienteMDuino(QObject):
    """Cliente TCP del M-Duino. Reconecta solo si se cae la conexion."""

    conexion_cambiada = Signal(bool)   # True al conectar, False al perder la conexion
    seta_cambiada     = Signal(bool)   # True = seta pulsada
    linea_recibida    = Signal(str)    # cualquier linea, para el registro de la interfaz

    def __init__(self, ip, puerto, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.puerto = puerto
        self.sock = None
        self._hilo = None

    # ----- conexion -----

    def iniciar(self):
        """Arranca el hilo de lectura. No bloquea."""
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def esta_conectado(self):
        return self.sock is not None

    def _bucle(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip, self.puerto))
                self.sock = sock
                print("[MDUINO] Conectado")
                self.conexion_cambiada.emit(True)
                self._leer(sock)
            except OSError as e:
                print(f"[MDUINO] TCP desconectado, reintentando: {e}")
            if self.sock is not None:
                self.sock = None
                self.conexion_cambiada.emit(False)
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
        self.linea_recibida.emit(linea)
        # SETA DESACTIVADA: el M-Duino aun no esta conectado fisicamente.
        # Descomentar cuando se pueda probar con la seta real.
        # if linea == MSG_SETA_PULSADA:
        #     self.seta_cambiada.emit(True)
        # elif linea == MSG_SETA_LIBRE:
        #     self.seta_cambiada.emit(False)

    # ----- envio -----

    def enviar(self, mensaje):
        if self.sock is None:
            print(f"[MDUINO] Sin conexion, descartado: {mensaje}")
            return False
        try:
            self.sock.sendall((mensaje + TERMINADOR).encode("utf-8"))
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
