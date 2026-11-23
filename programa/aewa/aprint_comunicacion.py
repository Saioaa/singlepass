# -*- coding: utf-8 -*-
"""Comunicacion con APRINT (aewa) por TCP: protocolo de APRINT-Remote.

Comando : codigo (2 letras ASCII) + parametros + "\\n" + 0
Respuesta: "rp" + codigo de error (4) + valor de retorno (variable) + 2 bytes
           (eco del comando desde APRINT 3.5.2; "\\n" + 0 en versiones anteriores)
Enteros en little endian. Textos (rutas, nombres) en Unicode (UTF-16LE)
terminados en 0. Si el codigo de error no es 0 no hay valor de retorno.

ClienteAprint es sincrono (bloquea mientras espera la respuesta): se usa desde
un hilo. Aprint (QObject) lo envuelve para la interfaz: conecta en segundo
plano y manda los mensajes al log por senal, como EjesDryve.

Para que APRINT acepte la conexion hay que activar el protocolo remoto en
Printer Settings -> Remote de APRINT.
"""

import socket
import struct
import threading
import time

from PySide6.QtCore import QObject, Signal

from programa import config
from programa.aewa import aprint_arranque

# ===== FORMATO =====
FIN_COMANDO = b"\n\x00"
CABECERA_RESPUESTA = b"rp"
TAM_CODIGO = 2
TAM_ERROR = 4
TAM_COLA = 2                    # eco del comando (o "\n" + 0 antes de 3.5.2)
CODIFICACION_TEXTO = "utf-16-le"
FIN_TEXTO = b"\x00\x00"
TAM_CARACTER = 2

# ===== TIPOS DE VALOR DE RETORNO =====
RETORNO_NINGUNO = 0
RETORNO_TEXTO = -1              # texto Unicode terminado en 0
TAM_ENTERO = 4

# ===== INDICES =====
IMPRESORA_0 = 0
TODAS_LAS_IMPRESORAS = 0xFFFF   # -1: todas / el job abierto en la vista de APRINT
PMB_0 = 0

# ===== CONEXION =====
TIMEOUT_CONEXION_S = 3.0
TIMEOUT_RESPUESTA_S = 10.0      # abrir el dialogo de impresion o insertar una imagen puede tardar
OPCION_RESERVADA = 0
REINTENTO_ARRANQUE_S = 1.0      # mientras APRINT arranca, un intento de conexion por segundo
PD_CERRAR_AL_SALIR = 0          # "pd" 0: cerrar el dialogo de impresion
CODIGO_DIALOGO = "pd"
PD_ABRIR_DIALOGO = 1

# ===== ERRORES CON SOLUCION PARA EL OPERARIO =====
# Salen cuando alguien ha abierto ventanas de APRINT a mano (visto el 22/10/2026):
# un dialogo Print abierto desde APRINT no se puede cerrar por el protocolo remoto.
ERROR_VENTANA_ABIERTA = 0xC00001E6    # "a window or message box is open on the remote host"
ERROR_DIALOGO_ABIERTO = 0xC00001EA    # "Command can't be processed when print dialog is open"
SOLUCIONES_ERROR = {
    ERROR_VENTANA_ABIERTA: "Hay una ventana abierta en APRINT (Printer Settings, un mensaje...): "
                           "ciérrela y vuelva a intentarlo",
    ERROR_DIALOGO_ABIERTO: "El diálogo Print de APRINT está abierto: ciérrelo en APRINT y vuelva "
                           "a intentarlo",
}


class ErrorAprint(Exception):
    """APRINT ha respondido con un codigo de error (o la respuesta no es valida)."""

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def u16(valor):
    return struct.pack("<H", valor & 0xFFFF)


def u8(valor):
    return struct.pack("<B", valor & 0xFF)


def i32(valor):
    return struct.pack("<i", valor)


def u32(valor):
    return struct.pack("<I", valor & 0xFFFFFFFF)


def texto(cadena):
    """Texto para APRINT: UTF-16LE terminado en 0."""
    return str(cadena).encode(CODIFICACION_TEXTO) + FIN_TEXTO


class ClienteAprint:

    def __init__(self, ip=config.IP_APRINT, puerto=config.PUERTO_APRINT):
        """ip: la de APRINT (config.IP_APRINT), la primera que se prueba; si no
        responde (o es None), se prueban las IPs de este ordenador. APRINT
        escucha solo en la IP de red que muestra en Printer Settings -> Remote,
        que cambia de un ordenador a otro (127.0.0.1 no le vale)."""
        self.ip_fija = ip
        self.ip = ip              # la que ha funcionado (None hasta conectar)
        self.puerto = puerto
        self.socket = None
        self.propiedades = {}     # ultima lectura de aprint_propiedades.leer_propiedades
        self._candado = threading.Lock()   # un comando cada vez, aunque llamen varios hilos
        # callable() tras abrir el dialogo de impresion ("pd" 1) con exito: la
        # ventana principal vuelve al frente (Aprint lo conecta a dialogo_abierto)
        self.al_abrir_dialogo = None

    # ===== conexion =====
    @property
    def conectado(self):
        return self.socket is not None

    def ips_candidatas(self):
        """En orden: la de config, la ultima que funciono y las IPv4 de los
        adaptadores de este ordenador (las que Windows asocia a su nombre)."""
        ips = []
        for ip in (self.ip_fija, self.ip):
            if ip and ip not in ips:
                ips.append(ip)
        try:
            for *_, direccion in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                if direccion[0] not in ips:
                    ips.append(direccion[0])
        except OSError:
            pass
        return ips

    def conectar(self):
        """Prueba las IPs candidatas; lanza OSError con la ultima si no responde ninguna."""
        self.cerrar()
        error = None
        for ip in self.ips_candidatas():
            try:
                s = socket.create_connection((ip, self.puerto), timeout=TIMEOUT_CONEXION_S)
            except OSError as e:
                error = OSError(f"{ip}:{self.puerto}: {e}")
                continue
            s.settimeout(TIMEOUT_RESPUESTA_S)
            self.socket = s
            self.ip = ip
            return
        raise error

    def cerrar(self):
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None

    # ===== protocolo =====
    def comando(self, codigo, parametros=b"", retorno=RETORNO_NINGUNO):
        """Envia un comando y devuelve el valor de retorno (bytes, o str si
        retorno es RETORNO_TEXTO). retorno: numero de bytes esperados.
        Lanza ErrorAprint si APRINT responde con error, OSError si se cae la
        conexion (se reconecta una vez antes de rendirse)."""
        trama = codigo.encode("ascii") + parametros + FIN_COMANDO
        with self._candado:
            for intento in (1, 2):
                try:
                    if self.socket is None:
                        self.conectar()
                    self.socket.sendall(trama)
                    respuesta = self._leer_respuesta(codigo, retorno)
                except OSError:
                    self.cerrar()
                    if intento == 2:
                        raise
                    continue
                if codigo == CODIGO_DIALOGO and parametros == u16(PD_ABRIR_DIALOGO) \
                        and self.al_abrir_dialogo is not None:
                    self.al_abrir_dialogo()
                return respuesta

    def _recibir(self, n):
        datos = b""
        while len(datos) < n:
            trozo = self.socket.recv(n - len(datos))
            if not trozo:
                raise ConnectionError("APRINT ha cerrado la conexion")
            datos += trozo
        return datos

    def enviar_sin_respuesta(self, codigo, parametros=b""):
        """Envia un comando sin esperar respuesta (QuitAPRINT: APRINT se cierra
        y puede no contestar). No hace nada si no hay conexion."""
        with self._candado:
            if self.socket is None:
                return
            try:
                self.socket.sendall(codigo.encode("ascii") + parametros + FIN_COMANDO)
            except OSError:
                pass

    def _leer_respuesta(self, codigo, retorno):
        cabecera = self._recibir(TAM_CODIGO + TAM_ERROR)
        if cabecera[:TAM_CODIGO] != CABECERA_RESPUESTA:
            self.cerrar()   # desincronizados: mejor empezar de cero
            raise ErrorAprint(f"{codigo}: respuesta no valida {cabecera!r}")
        error = struct.unpack("<I", cabecera[TAM_CODIGO:])[0]
        if error:
            self._recibir(TAM_COLA)
            raise ErrorAprint(f"{codigo}: error 0x{error:08X}", error)
        if retorno == RETORNO_TEXTO:
            valor = self._leer_texto()
        else:
            valor = self._recibir(retorno) if retorno else b""
        self._recibir(TAM_COLA)
        return valor

    def _leer_texto(self):
        datos = b""
        while True:
            caracter = self._recibir(TAM_CARACTER)
            if caracter == FIN_TEXTO:
                return datos.decode(CODIFICACION_TEXTO)
            datos += caracter

    # ===== comandos de uso general =====
    def leer_parametro(self, tipo, impresora=IMPRESORA_0):
        """Get Printer Parameter ("pg"): entero con signo."""
        valor = self.comando("pg", u16(impresora) + u16(tipo), TAM_ENTERO)
        return struct.unpack("<i", valor)[0]

    def escribir_parametro(self, tipo, valor, impresora=IMPRESORA_0):
        """Set Printer Parameter ("pp")."""
        self.comando("pp", u16(impresora) + u16(tipo) + i32(valor))

    def texto_error(self, codigo_error):
        """Get Error String ("ge"): descripcion de un codigo de error."""
        return self.comando("ge", u32(codigo_error), RETORNO_TEXTO)

    def describir(self, error):
        """Texto para el log de una excepcion: con la descripcion de APRINT si la hay."""
        if isinstance(error, ErrorAprint) and error.codigo:
            solucion = SOLUCIONES_ERROR.get(error.codigo)
            try:
                texto = f"{error} ({self.texto_error(error.codigo)})"
            except (OSError, ErrorAprint):
                texto = str(error)
            return f"{texto}. {solucion}" if solucion else texto
        return str(error)


class Aprint(QObject):
    """APRINT para la interfaz: conexion en segundo plano y mensajes al log.
    Las funciones de cada parte (propiedades, trabajo, impresion) estan en
    los modulos aprint_*.py y usan self.cliente."""

    mensaje = Signal(str)
    conexion_terminada = Signal(bool)
    # el dialogo de impresion se ha abierto: APRINT lo pone delante de todo, la
    # ventana principal vuelve al frente (se emite desde el hilo que lo abre)
    dialogo_abierto = Signal()
    _resultado = Signal(list, list, bool)   # interno: del hilo de conexion al hilo de Qt
    _mensaje_hilo = Signal(str)             # interno: mensajes desde el hilo de conexion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cliente = ClienteAprint()
        self.conectando = False          # hilo de conexion en marcha
        self._resultado.connect(self._tras_conectar)
        self._mensaje_hilo.connect(self._log)
        self.abierto_por_app = False     # la app ha lanzado APRINT: lo cierra al salir
        # abrir y cerrar el dialogo de impresion (preparar, imprimir, job de
        # lectura): una operacion cada vez (aprint_lectura.py)
        self.candado_dialogo = threading.Lock()
        # "ps" aceptado y sin "px": el dialogo no se toca (aprint_impresion lo
        # marca en su hilo, antes de soltar candado_dialogo)
        self.impresion_en_marcha = False
        self.cliente.al_abrir_dialogo = self.dialogo_abierto.emit

    def _log(self, texto_log):
        self.mensaje.emit(f"[APRINT] {texto_log}")

    @staticmethod
    def _log_archivo(texto_log):
        """Solo al fichero de log del dia."""
        print(f"[APRINT] {texto_log}")

    @property
    def conectado(self):
        return self.cliente.conectado

    def conectar(self, al_conectar=None):
        """Conecta en segundo plano. al_conectar(cliente) -> (lineas para la app,
        lineas solo para el fichero): lo que se haga justo despues, en el mismo
        hilo (leer las propiedades...)."""
        if self.conectando:
            return
        self.conectando = True
        self._log("Conectando con APRINT...")
        self._log_archivo(f"Direcciones: {', '.join(self.cliente.ips_candidatas())}, "
                          f"puerto {self.cliente.puerto}")

        def tarea():
            try:
                self.cliente.conectar()
            except OSError as e:
                error = self._abrir_y_conectar(e) if config.ABRIR_APRINT else e
                if error is not None:
                    self._resultado.emit(
                        [f"NO conectado ({error}). Compruebe que APRINT esta abierto y con el "
                         "protocolo remoto activado (Printer Settings -> Remote)"], [], False)
                    return
            app = [f"Conectado en {self.cliente.ip}:{self.cliente.puerto}"]
            archivo = []
            ip_config = self.cliente.ip_fija
            if ip_config and self.cliente.ip != ip_config:
                # normal en otro ordenador; en el de la maquina: revisar IP_APRINT
                archivo.append(f"AVISO: no responde en la IP de config.IP_APRINT "
                               f"({ip_config}): conectado en {self.cliente.ip}")
            if al_conectar is not None:
                try:
                    with self.candado_dialogo:
                        lineas_app, lineas_archivo = al_conectar(self.cliente)
                    app += list(lineas_app)
                    archivo += list(lineas_archivo)
                except (OSError, ErrorAprint) as e:
                    app.append(f"Error al leer de APRINT: {self.cliente.describir(e)}")
            self._resultado.emit(app, archivo, True)

        threading.Thread(target=tarea, daemon=True).start()

    def _abrir_y_conectar(self, error):
        """En el hilo de conexion: si APRINT no esta abierto lo abre y espera a
        que escuche. Devuelve None si conecta, o el ultimo error."""
        ruta = aprint_arranque.buscar_ejecutable()
        if ruta is None:
            self._mensaje_hilo.emit("No se encuentra APRINT para abrirlo: poner su ruta en "
                      "config.RUTA_APRINT")
            return error
        if aprint_arranque.en_ejecucion(ruta) is not False:
            # abierto (o no se sabe): no responde porque falta el protocolo remoto
            # o porque esta en otro equipo; abrir otro no lo arregla
            self._log_archivo(f"{ruta.name} ya esta abierto y no responde")
            return error
        self._mensaje_hilo.emit("Abriendo APRINT...")
        self._log_archivo(f"Ejecutable: {ruta} ({config.MODO_ARRANQUE_APRINT})")
        try:
            aprint_arranque.abrir(ruta)
        except OSError as e:
            self._mensaje_hilo.emit(f"No se ha podido abrir APRINT: {e}")
            return e
        self.abierto_por_app = True
        limite = time.monotonic() + config.ESPERA_ARRANQUE_APRINT_S
        while time.monotonic() < limite:
            time.sleep(REINTENTO_ARRANQUE_S)
            try:
                self.cliente.conectar()
                return None
            except OSError as e:
                error = e
        self._mensaje_hilo.emit(f"APRINT no responde tras {config.ESPERA_ARRANQUE_APRINT_S:g} s")
        return error

    def _tras_conectar(self, app, archivo, conectado):
        self.conectando = False
        # en el fichero queda en orden: conectado, detalle y avisos
        if app:
            self._log(app[0])
        for linea in archivo:
            self._log_archivo(linea)
        for linea in app[1:]:
            self._log(linea)
        self.conexion_terminada.emit(conectado)

    def cerrar(self):
        """Al salir de la app. Si la app abrio APRINT, lo cierra (QuitAPRINT)."""
        if self.abierto_por_app and config.CERRAR_APRINT_AL_SALIR and self.cliente.conectado:
            self._log_archivo("Cerrando APRINT")
            self.cliente.enviar_sin_respuesta("gq")
        self.cliente.cerrar()
