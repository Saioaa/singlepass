# -*- coding: utf-8 -*-
"""Comunicacion con el servidor de impresion PMB-8.

Portado a PySide6 desde pmb_comunication.py, listener.py y message_manager.py.

Diferencias respecto al codigo anterior:
  - Un unico socket y un unico lector. Antes get_system_mode_info() hacia un
    recv() directo mientras el hilo listener leia el mismo socket: carrera.
  - La conexion fallida se detecta al construir, no al primer recv().
  - El resultado sale por senales de Qt, no escribiendo directamente en un
    QTextEdit, para que la interfaz decida que hacer con cada aviso.

Uso:
    self.pmb = ClientePMB()
    self.pmb.mensaje.connect(self.ui.pg_impr_log.append)
    self.pmb.modos_recibidos.connect(self.cargar_modos)
    self.pmb.dpi_recibido.connect(self.guardar_dpi)
    self.pmb.conectar()
"""

import re
import socket

from PySide6.QtCore import QObject, QThread, Signal

# ===== CONEXION =====
HOST_PMB       = "localhost"   # cambiar si el PMB corre en otra maquina de la red
PUERTO_PMB     = 2000
TIMEOUT_SOCKET = 5             # s
TAM_BUFFER     = 4096          # bytes por lectura

# ===== COMANDOS DEL PROTOCOLO =====
CMD_PEDIR_MODOS     = "S,T,N"
CMD_INFO_MODO       = "S,T,I"
CMD_CARGAR_VPI      = "R,D"
CMD_RENDERIZAR      = "R,R"
CMD_CAMBIAR_PARAM_PC = "P,C,P"
CMD_IMPRIMIR        = "P,P"
CMD_ESCUCHAR_PC     = "P,L"     # registrar listener del Print Controller (mensajes I,...)
CMD_ABORTAR_IMPRESION = "P,A"   # se envia por un socket independiente (manual, 2.2)

PARAM_RENDER_POR_DEFECTO   = "0"
PARAM_COPIAS_POR_DEFECTO   = "1"
PARAM_PRIMERA_COPIA        = "1"
TERMINADOR                 = "\n"
TIMEOUT_ACUSE_ABORTO       = 3     # s de espera del acuse A,<id>,P,A en el socket de aborto

# ===== TIPOS DE MENSAJE DE RESPUESTA =====
TIPO_RED       = "N"   # notificacion de red
TIPO_ACUSE     = "A"   # acuse de recibo
TIPO_INFO      = "I"   # informacion durante la ejecucion
TIPO_COMPLETO  = "C"   # comando terminado

# ===== CODIGOS DE INFORMACION =====
INFO_ESTADO          = "S"
INFO_SEMAFORO        = "T"
INFO_PASADA          = "SP"
INFO_IMPRIMIENDO     = "P"
INFO_LISTO_IMPRIMIR  = "RTP"
INFO_FIN_IMPRESION   = "EP"
INFO_REGISTRO        = "G"

# ===== POSICIONES DENTRO DE LOS MENSAJES =====
POS_TIPO          = 0
POS_ID_COMANDO    = 1
POS_CODIGO        = 2
CAMPOS_MINIMOS_C  = 3
PREFIJO_LISTA_MODOS = "0;"   # marca la respuesta que contiene los modos
SIN_ERROR         = 0

CODIGOS_ERROR = {
    -1: "Comando desconocido",
    -2: "Fallo al cargar la configuracion del Print Server",
    -4: "Fallo al fijar el valor de un parametro",
    -5: "Parametros incorrectos en el mensaje",
    -6: "Fallo al leer el valor de un parametro",
    -7: "Fallo al aplicar el modo de impresion",
    -8: "Print Server suspendido",
    -100: "Fallo general del Render Engine",
    -101: "Render Engine ocupado",
    -102: "Fallo al cargar la configuracion del Render Engine",
    -121: "Fallo en el renderizado",
    -160: "Fallo esperando la inicializacion del Print Server",
    -165: "Fallo en la inicializacion de la operacion",
    -201: "Print Controller ocupado",
    -202: "Fallo general del Print Controller",
    -210: "Fallo en la impresion",
    -216: "Print Controller no inicializado",
    -217: "Fallo de seguridad del Print Controller",
    -230: "Fallo en el purgado",
    -240: "Fallo al arrancar el monitor de estado de los cabezales",
    -255: "Fallo al leer el estado de error",
    -260: "Fallo al encender los calentadores de los cabezales",
    -270: "Fallo al apagar los calentadores de los cabezales",
    -600: "Fallo general del Network Controller",
    -601: "Network Controller ocupado",
    -620: "Fallo en la difusion de red",
    -625: "Fallo al abortar la operacion",
    -1000: "Fallo general del Print Server Monitor",
    -1001: "Print Server Monitor ocupado",
    -1030: "Fallo al arrancar los Print Servers",
    -1031: "Fallo al detener los Print Servers",
    -1032: "Fallo al reiniciar los Print Servers",
}

ESTADOS_SEMAFORO = {0: "Listo", 1: "Preparando", 2: "Imprimiendo", 3: "Error"}
NIVELES_REGISTRO = {0: "INFO", 1: "AVISO", 2: "ERROR"}


class LectorPMB(QThread):
    """Hilo unico de lectura del socket. Emite cada linea recibida."""

    linea_recibida = Signal(str)
    desconectado = Signal(str)

    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.activo = True

    def run(self):
        pendiente = ""
        while self.activo:
            try:
                datos = self.sock.recv(TAM_BUFFER)
            except OSError as e:
                if self.activo:
                    self.desconectado.emit(str(e))
                return

            if not datos:
                if self.activo:
                    self.desconectado.emit("el PMB ha cerrado la conexion")
                return

            pendiente += datos.decode("utf-8", errors="replace")
            while TERMINADOR in pendiente:
                linea, pendiente = pendiente.split(TERMINADOR, 1)
                linea = linea.strip()
                if linea:
                    self.linea_recibida.emit(linea)

    def detener(self):
        self.activo = False


class ClientePMB(QObject):
    """Cliente del servidor de impresion PMB-8."""

    mensaje = Signal(str)            # linea para el registro de la interfaz
    modos_recibidos = Signal(list)   # lista de modos de sistema disponibles
    dpi_recibido = Signal(int, int)  # resolucion del modo seleccionado
    listo_para_imprimir = Signal()   # I,<id>,RTP: el PMB tiene datos y espera el print go
    impresion_terminada = Signal()
    conexion_perdida = Signal(str)
    comando_completado = Signal(str)  # id del comando que ha terminado bien
    comando_fallido = Signal(str, int)  # id del comando y codigo de error

    def __init__(self, host=HOST_PMB, puerto=PUERTO_PMB, parent=None):
        super().__init__(parent)
        self.host = host
        self.puerto = puerto
        self.sock = None
        self.lector = None
        self.esperando_info_modo = False

    # ----- conexion -----

    def conectar(self):
        """Abre la conexion y arranca el lector. Devuelve True si lo consigue."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(TIMEOUT_SOCKET)
            self.sock.connect((self.host, self.puerto))
            self.sock.settimeout(None)
        except OSError as e:
            self.sock = None
            self.mensaje.emit(f"[PMB] No se ha podido conectar: {e}")
            return False

        self.lector = LectorPMB(self.sock)
        self.lector.linea_recibida.connect(self._procesar_linea)
        self.lector.desconectado.connect(self._al_desconectar)
        self.lector.start()
        self.mensaje.emit(f"[PMB] Conectado a {self.host}:{self.puerto}")
        # sin esto el servidor solo envia A y C; los I (RTP, EP, estado) no llegan
        self._enviar(CMD_ESCUCHAR_PC)
        return True

    def conectado(self):
        return self.sock is not None

    def cerrar(self):
        if self.lector is not None:
            self.lector.detener()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        if self.lector is not None:
            self.lector.wait()
            self.lector = None

    def _al_desconectar(self, motivo):
        self.sock = None
        self.mensaje.emit(f"[PMB] Conexion perdida: {motivo}")
        self.conexion_perdida.emit(motivo)

    # ----- envio -----

    def _enviar(self, comando):
        if self.sock is None:
            self.mensaje.emit(f"[PMB] Sin conexion, descartado: {comando}")
            return False
        try:
            self.sock.sendall((comando + TERMINADOR).encode("utf-8"))
            return True
        except OSError as e:
            self.mensaje.emit(f"[PMB] Error enviando {comando}: {e}")
            return False

    def pedir_modos(self):
        """Solicita la lista de modos de sistema disponibles."""
        self._enviar(CMD_PEDIR_MODOS)

    def pedir_info_modo(self, modo):
        """Solicita la informacion de un modo; la resolucion llega por dpi_recibido."""
        self.esperando_info_modo = True
        self._enviar(f"{CMD_INFO_MODO},{modo}")

    def cargar_vpi(self, ruta_vpi):
        self._enviar(f"{CMD_CARGAR_VPI},{ruta_vpi}")

    def renderizar(self, ruta_salida):
        self._enviar(f"{CMD_RENDERIZAR},{ruta_salida},{PARAM_RENDER_POR_DEFECTO}")

    def cambiar_parametro_pc(self, nombre, valor):
        """Change Parameter Value en el Print Controller (nombre = Data Unique ID)."""
        self._enviar(f"{CMD_CAMBIAR_PARAM_PC},{nombre},{valor}")

    def imprimir(self, ruta_bmp):
        self._enviar(f"{CMD_IMPRIMIR},{PARAM_PRIMERA_COPIA},{ruta_bmp},"
                     f"{PARAM_COPIAS_POR_DEFECTO}")

    def abortar_impresion(self):
        """Aborta la impresion en curso. El manual exige enviar P,A por una
        conexion nueva, distinta de la de impresion. Devuelve True si se envio."""
        try:
            with socket.create_connection((self.host, self.puerto), timeout=TIMEOUT_SOCKET) as s:
                s.sendall((CMD_ABORTAR_IMPRESION + TERMINADOR).encode("utf-8"))
                # esperar el acuse antes de cerrar, para que el servidor no descarte el comando
                s.settimeout(TIMEOUT_ACUSE_ABORTO)
                recibido = ""
                while TIPO_ACUSE + "," + CMD_ABORTAR_IMPRESION not in recibido:
                    datos = s.recv(TAM_BUFFER)
                    if not datos:
                        break
                    recibido += datos.decode("utf-8", errors="replace")
        except socket.timeout:
            self.mensaje.emit("[PMB] Aborto enviado, sin acuse del servidor")
            return True
        except OSError as e:
            self.mensaje.emit(f"[PMB] No se ha podido enviar el aborto: {e}")
            return False
        for linea in recibido.split(TERMINADOR):
            if linea.strip():
                self.mensaje.emit(f"[PMB] (aborto) {linea.strip()}")
        return True

    # ----- recepcion -----

    def _procesar_linea(self, linea):
        partes = linea.split(",")
        tipo = partes[POS_TIPO]

        if tipo == TIPO_RED:
            self.mensaje.emit("[PMB] Notificacion de red")
        elif tipo == TIPO_ACUSE:
            pass   # el acuse no aporta nada a la interfaz
        elif tipo == TIPO_INFO:
            self._procesar_info(partes)
        elif tipo == TIPO_COMPLETO:
            self._procesar_completo(partes)
        else:
            self.mensaje.emit(f"[PMB] Mensaje no reconocido: {linea}")

    def _procesar_completo(self, partes):
        if len(partes) < CAMPOS_MINIMOS_C:
            self.mensaje.emit(f"[PMB] Mensaje C mal formado: {','.join(partes)}")
            return

        id_comando = partes[POS_ID_COMANDO]
        try:
            codigo = int(partes[POS_CODIGO])
        except ValueError:
            self.mensaje.emit(f"[PMB] Codigo de error ilegible: {','.join(partes)}")
            return

        info = ",".join(partes[POS_CODIGO + 1:])

        if codigo != SIN_ERROR:
            descripcion = CODIGOS_ERROR.get(codigo, "Error desconocido")
            self.mensaje.emit(f"[PMB] ERROR {codigo} en el comando {id_comando}: "
                              f"{descripcion}. {info}")
            self.esperando_info_modo = False
            self.comando_fallido.emit(id_comando, codigo)
            return

        self.mensaje.emit(f"[PMB] Comando {id_comando} completado. {info}")
        self.comando_completado.emit(id_comando)

        if info.startswith(PREFIJO_LISTA_MODOS):
            self.modos_recibidos.emit(info.split(";")[1:])
        elif self.esperando_info_modo:
            self.esperando_info_modo = False
            dpi = self._extraer_dpi(info)
            if dpi is None:
                self.mensaje.emit(f"[PMB] No se ha podido extraer la resolucion de: {info}")
            else:
                self.dpi_recibido.emit(dpi[0], dpi[1])

    def _procesar_info(self, partes):
        if len(partes) < CAMPOS_MINIMOS_C:
            return
        id_comando = partes[POS_ID_COMANDO]
        codigo = partes[POS_CODIGO]
        datos = partes[POS_CODIGO + 1:]

        if codigo == INFO_ESTADO and len(datos) >= 2:
            self.mensaje.emit(f"[PMB] Estado: {datos[0]} (codigo {datos[1]})")
        elif codigo == INFO_SEMAFORO and datos:
            self.mensaje.emit(f"[PMB] Semaforo: {self._texto_semaforo(datos[0])}")
        elif codigo == INFO_PASADA and datos:
            self.mensaje.emit(f"[PMB] Pasada procesada: {datos[0]}")
        elif codigo == INFO_IMPRIMIENDO:
            self.mensaje.emit("[PMB] Impresion iniciada")
        elif codigo == INFO_LISTO_IMPRIMIR and datos:
            self.mensaje.emit(f"[PMB] Listo para imprimir ({datos[0]} pasadas)")
            self.listo_para_imprimir.emit()
        elif codigo == INFO_FIN_IMPRESION:
            self.mensaje.emit("[PMB] Impresion completada")
            self.impresion_terminada.emit()
        elif codigo == INFO_REGISTRO and datos:
            nivel = self._texto_nivel(datos[0])
            self.mensaje.emit(f"[PMB] {nivel}: {', '.join(datos[1:])}")
        else:
            self.mensaje.emit(f"[PMB] Info {codigo} del comando {id_comando}: "
                              f"{', '.join(datos)}")

    # ----- utilidades -----

    @staticmethod
    def _extraer_dpi(texto):
        encontrados = re.findall(r"(\d+)\s*dpi", texto, re.IGNORECASE)
        if len(encontrados) >= 2:
            return int(encontrados[0]), int(encontrados[1])
        return None

    @staticmethod
    def _texto_semaforo(codigo):
        try:
            return ESTADOS_SEMAFORO.get(int(codigo), "Desconocido")
        except ValueError:
            return "Desconocido"

    @staticmethod
    def _texto_nivel(codigo):
        try:
            return NIVELES_REGISTRO.get(int(codigo), "DESCONOCIDO")
        except ValueError:
            return "DESCONOCIDO"
