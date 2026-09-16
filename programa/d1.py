# -*- coding: utf-8 -*-
"""Driver del variador D1 (CiA 402 sobre Modbus TCP, funcion 43 / MEI 13).

Extraido de programa_impresora.py sin cambiar la logica: solo se han
sustituido los literales por constantes con nombre. No depende de Qt.
"""

import socket
import struct
import threading
import time

# ===== OBJETOS CiA 402 (indice de cada objeto) =====
CONTROLWORD        = 0x6040   # ordenes al motor          (2 bytes)
STATUSWORD         = 0x6041   # estado del motor          (2 bytes)
MODO_OPERACION     = 0x6060   # modo de trabajo           (1 byte)
MODO_OPERACION_REAL = 0x6061  # modo activo (lectura)     (1 byte)
POSICION_ACTUAL    = 0x6064   # posicion real (lectura)   (4 bytes)
POSICION_OBJETIVO  = 0x607A   # posicion destino          (4 bytes)
VELOCIDAD_PERFIL   = 0x6081   # velocidad en modo posicion(4 bytes)
ACELERACION        = 0x6083   # aceleracion               (4 bytes)
DECELERACION       = 0x6084   # deceleracion              (4 bytes)
HOMING_METHOD      = 0x6098   # metodo de homing          (1 byte)
HOMING_VELOCIDADES = 0x6099   # sub1 busqueda / sub2 cero (4 bytes)
HOMING_ACELERACION = 0x609A   # aceleracion de homing     (4 bytes)
UNIDAD_SI_POSICION = 0x60A8   # factor de unidades (lectura) (4 bytes)
VELOCIDAD_OBJETIVO = 0x60FF   # velocidad en modo velocidad (4 bytes)

# ===== METODOS DE HOMING =====
METODO_LSN    = 17   # Limit Switch Negative: busca el final de carrera negativo
METODO_SCP    = 37   # Set Current Position: fija el cero en la posicion actual (NO mueve)
METODO_HOMING = METODO_LSN

# ===== SUBINDICES =====
SUB_POR_DEFECTO  = 0
SUB_VEL_BUSQUEDA = 1
SUB_VEL_CERO     = 2

# ===== TAMANIOS DE OBJETO (bytes) =====
TAM_1_BYTE  = 1
TAM_2_BYTES = 2
TAM_4_BYTES = 4

# ===== BITS DEL STATUSWORD =====
SW_FALLO              = 0x0008   # bit 3  - fault
SW_OBJETIVO_ALCANZADO = 0x0400   # bit 10 - target reached
SW_HOMING_ALCANZADO   = 0x1000   # bit 12 - homing attained
SW_HOMING_ERROR       = 0x2000   # bit 13 - homing error
SW_ACUSE_CONSIGNA     = 0x1000   # bit 12 - en modo posicion: set-point acknowledge

# ===== MODOS DE OPERACION =====
MODO_POSICION  = 1
MODO_VELOCIDAD = 3
MODO_HOMING    = 6

# ===== CONTROLWORDS (ordenes de la maquina de estados CiA 402) =====
CW_SHUTDOWN     = 0x06    # -> Ready to Switch On
CW_SWITCH_ON    = 0x07    # -> Switched On
CW_ENABLE_OP    = 0x0F    # -> Operation Enabled (operativo), halt = 0
CW_HALT         = 0x10F   # enable + halt = 1 -> decelera y para
CW_FAULT_RESET  = 0x80    # resetear fallo
CW_NEW_SETPOINT = 0x1F    # 0x0F + bit4: disparar movimiento
CW_START_HOMING = 0x1F    # en modo homing, bit4 arranca el homing

# ===== TELEGRAMA MODBUS (funcion 43 encapsulada, MEI tipo 13 = CANopen) =====
FUNCION_ENCAPSULADA   = 43
MEI_CANOPEN           = 13
OPERACION_LECTURA     = 0
OPERACION_ESCRITURA   = 1
LONGITUD_BASE_LECTURA = 13    # bytes del PDU sin datos
TAM_CABECERA_MBAP     = 6
OFFSET_DATOS_RESPUESTA = 19   # posicion del primer byte de datos en la respuesta

# ===== CONEXION =====
INTENTOS_CONEXION  = 3
TIMEOUT_SOCKET     = 5      # s
RETARDO_REINTENTO  = 2      # s

# ===== TEMPORIZACION =====
RETARDO_TRANSICION_ESTADO = 0.05   # s entre controlwords de la secuencia de encendido
RETARDO_RESET_FALLO       = 0.1    # s tras el fault reset
TIMEOUT_CAMBIO_MODO       = 2.0    # s
PERIODO_SONDEO_MODO       = 0.02   # s
TIMEOUT_HANDSHAKE         = 2.0    # s para el acuse de consigna del modo posicion
TIMEOUT_MOVIMIENTO        = 120    # s de duracion maxima de un posicionamiento
PERIODO_SONDEO            = 0.02   # s entre lecturas del statusword

# ===== HOMING =====
VELOCIDAD_HOMING_BUSQUEDA = 20     # mm/s - busqueda del final de carrera
VELOCIDAD_HOMING_CERO     = 2      # mm/s - busqueda fina del cero
ACELERACION_HOMING        = 100    # mm/s2
RETARDO_ARRANQUE_HOMING   = 0.5    # s - ventana ciega frente al bit 12 obsoleto
TIMEOUT_HOMING            = 90     # s


def _telegrama(operacion, longitud, indice, subindice, tamanio):
    alto = (indice >> 8) & 0xFF
    bajo = indice & 0xFF
    return bytearray([0, 0, 0, 0, 0, longitud,
                      0, FUNCION_ENCAPSULADA, MEI_CANOPEN, operacion, 0, 0,
                      alto, bajo, subindice, 0, 0, 0, tamanio])


def leer_objeto(indice, tamanio, subindice=SUB_POR_DEFECTO):
    """Construye el telegrama para LEER un objeto CiA de la D1."""
    return _telegrama(OPERACION_LECTURA, LONGITUD_BASE_LECTURA, indice, subindice, tamanio)


def escribir_objeto(indice, tamanio, valor, subindice=SUB_POR_DEFECTO):
    """Construye el telegrama para ESCRIBIR un valor en un objeto CiA."""
    valor_bytes = list(struct.pack("<i", valor))[:tamanio]
    return (_telegrama(OPERACION_ESCRITURA, LONGITUD_BASE_LECTURA + tamanio,
                       indice, subindice, tamanio)
            + bytearray(valor_bytes))


class MotorD1:
    """Eje controlado por un variador D1. Las posiciones se expresan en mm."""

    def __init__(self, ip, puerto, limite_min, limite_max, factor_si):
        self.ip = ip
        self.puerto = puerto
        self.limite_min = limite_min
        self.limite_max = limite_max
        self.factor_si = factor_si      # conversion mm -> unidades del motor
        self.lock = threading.Lock()    # serializa el acceso al socket
        self.socket = None
        self.t_inicio_homing = 0.0
        self._conectar()
        self.habilitar()                # dejar el motor operativo al arrancar

    # ===== CAPA 1: comunicacion =====
    def _conectar(self):
        for intento in range(INTENTOS_CONEXION):
            try:
                if self.socket is not None:
                    try:
                        self.socket.close()
                    except OSError:
                        pass
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(TIMEOUT_SOCKET)
                self.socket.connect((self.ip, self.puerto))
                print(f"[MOTOR] Conectado a {self.ip}:{self.puerto}")
                return
            except socket.error as e:
                print(f"[MOTOR] Intento {intento + 1} fallido: {e}")
                if intento < INTENTOS_CONEXION - 1:
                    time.sleep(RETARDO_REINTENTO)
                else:
                    raise

    def _enviar(self, telegrama):
        with self.lock:
            try:
                return self._transaccion(telegrama)
            except (ConnectionError, OSError, socket.timeout) as e:
                print(f"[MOTOR] Conexion perdida ({e}), reconectando...")
                self._conectar()
                return self._transaccion(telegrama)

    def _transaccion(self, telegrama):
        self.socket.send(telegrama)
        cabecera = self._recibir_exacto(TAM_CABECERA_MBAP)
        longitud = (cabecera[4] << 8) | cabecera[5]
        resto = self._recibir_exacto(longitud)
        return list(cabecera + resto)

    def _recibir_exacto(self, n):
        datos = bytearray()
        while len(datos) < n:
            trozo = self.socket.recv(n - len(datos))
            if not trozo:
                raise ConnectionError("conexion cerrada por el D1")
            datos += trozo
        return datos

    def _extraer_valor(self, respuesta, tamanio):
        valor = 0
        for i in range(tamanio):
            valor |= respuesta[OFFSET_DATOS_RESPUESTA + i] << (8 * i)
        return valor

    # ===== CAPA 2: leer / escribir objetos =====
    def _leer(self, indice, tamanio, subindice=SUB_POR_DEFECTO):
        respuesta = self._enviar(leer_objeto(indice, tamanio, subindice))
        return self._extraer_valor(respuesta, tamanio)

    def _escribir(self, indice, tamanio, valor, subindice=SUB_POR_DEFECTO):
        self._enviar(escribir_objeto(indice, tamanio, valor, subindice))

    def set_modo(self, modo, timeout=TIMEOUT_CAMBIO_MODO):
        """Cambia de modo y confirma leyendo 0x6061 (la D1 no lo aplica al instante)."""
        self._escribir(MODO_OPERACION, TAM_1_BYTE, modo)
        inicio = time.time()
        while time.time() - inicio < timeout:
            if self._leer(MODO_OPERACION_REAL, TAM_1_BYTE) == modo:
                return
            time.sleep(PERIODO_SONDEO_MODO)
        raise Exception(f"Timeout cambiando al modo {modo}")

    # ===== CAPA 3: estado y control =====
    def leer_estado(self):
        """Devuelve el Statusword (numero de 16 bits)."""
        return self._leer(STATUSWORD, TAM_2_BYTES)

    def hay_fallo(self):
        """True si el motor esta en fault (bit 3 del statusword)."""
        return (self.leer_estado() & SW_FALLO) != 0

    def resetear_fallo(self):
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_FAULT_RESET)
        time.sleep(RETARDO_RESET_FALLO)

    def leer_posicion(self):
        """Devuelve la posicion actual en mm."""
        bruto = self._leer(POSICION_ACTUAL, TAM_4_BYTES)
        con_signo = struct.unpack("<i", struct.pack("<I", bruto))[0]
        return con_signo / self.factor_si

    # ===== Secuencia de encendido CiA 402 =====
    def habilitar(self):
        """Lleva el motor de apagado a OPERATION ENABLED (listo para moverse)."""
        if self.hay_fallo():
            print("[MOTOR] Fallo detectado, reseteando...")
            self.resetear_fallo()
        for controlword in (CW_SHUTDOWN, CW_SWITCH_ON, CW_ENABLE_OP):
            self._escribir(CONTROLWORD, TAM_2_BYTES, controlword)
            time.sleep(RETARDO_TRANSICION_ESTADO)
        print("[MOTOR] Habilitado (Operation Enabled)")

    def deshabilitar(self):
        """Apaga el par del motor."""
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_SHUTDOWN)
        print("[MOTOR] Deshabilitado")

    # ===== Parametros de movimiento =====
    def set_velocidad(self, mm_s):
        self._escribir(VELOCIDAD_PERFIL, TAM_4_BYTES, int(mm_s * self.factor_si))

    def set_aceleracion(self, mm_s2):
        self._escribir(ACELERACION, TAM_4_BYTES, int(mm_s2 * self.factor_si))

    def set_deceleracion(self, mm_s2):
        self._escribir(DECELERACION, TAM_4_BYTES, int(mm_s2 * self.factor_si))

    def _validar(self, posicion_mm):
        """Recorta la posicion a los limites del eje."""
        return max(self.limite_min, min(self.limite_max, posicion_mm))

    # ===== Movimiento a posicion absoluta =====
    def _esperar_bit(self, mascara, activo, timeout, contexto):
        """Espera a que un bit del statusword tome el valor indicado."""
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self.leer_estado()
            if (estado & SW_FALLO) != 0:
                raise Exception(f"Fallo del motor durante {contexto}")
            if ((estado & mascara) != 0) == activo:
                return
            time.sleep(PERIODO_SONDEO)
        raise Exception(f"Timeout en {contexto} ({timeout} s)")

    def mover_a(self, posicion_mm, esperar=True, timeout=TIMEOUT_MOVIMIENTO):
        """Mueve a una posicion absoluta (mm) en modo posicion."""
        posicion_mm = self._validar(posicion_mm)
        self.set_modo(MODO_POSICION)
        self._escribir(POSICION_OBJETIVO, TAM_4_BYTES, int(posicion_mm * self.factor_si))
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)      # bit4 = 0
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_NEW_SETPOINT)   # bit4 = 1: dispara
        self._esperar_bit(SW_ACUSE_CONSIGNA, True, TIMEOUT_HANDSHAKE, "acuse de consigna")
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)      # bit4 = 0: cierra el acuse
        self._esperar_bit(SW_ACUSE_CONSIGNA, False, TIMEOUT_HANDSHAKE, "cierre del acuse")
        if esperar:
            self.esperar_fin_movimiento(timeout)

    def esperar_fin_movimiento(self, timeout=TIMEOUT_MOVIMIENTO):
        """Espera hasta que el motor alcanza el objetivo (bit 10: target reached)."""
        self._esperar_bit(SW_OBJETIVO_ALCANZADO, True, timeout, "movimiento")

    def movimiento_terminado(self):
        """True si el motor alcanzo el objetivo (bit 10)."""
        return (self.leer_estado() & SW_OBJETIVO_ALCANZADO) != 0

    # ===== Movimiento manual (modo velocidad) =====
    def mover_manual(self, mm_s, sentido):
        """Arranca movimiento continuo. sentido = +1 (derecha) o -1 (izquierda).
        Llamar a parar() para detenerlo."""
        velocidad = int(mm_s * self.factor_si) * sentido
        self.set_modo(MODO_VELOCIDAD)
        self._escribir(VELOCIDAD_OBJETIVO, TAM_4_BYTES, velocidad)
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)   # enable con halt=0 -> arranca
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)   # refuerza halt=0

    def parar(self):
        """Detiene el movimiento manual (halt=1)."""
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_HALT)
        self._escribir(VELOCIDAD_OBJETIVO, TAM_4_BYTES, 0)

    def reanudar(self):
        """Baja el bit de halt para poder volver a posicionar tras un parar()."""
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)

    # ===== Homing =====
    def home(self,
             velocidad_busqueda_mm_s=VELOCIDAD_HOMING_BUSQUEDA,
             velocidad_cero_mm_s=VELOCIDAD_HOMING_CERO,
             aceleracion_mm_s2=ACELERACION_HOMING):
        """Lanza el homing. NO bloquea: vigilar con homing_terminado()."""
        if self.hay_fallo():
            self.resetear_fallo()

        self.set_modo(MODO_HOMING)
        self._escribir(HOMING_METHOD, TAM_1_BYTE, METODO_HOMING)
        self._escribir(HOMING_VELOCIDADES, TAM_4_BYTES,
                       int(velocidad_busqueda_mm_s * self.factor_si), SUB_VEL_BUSQUEDA)
        self._escribir(HOMING_VELOCIDADES, TAM_4_BYTES,
                       int(velocidad_cero_mm_s * self.factor_si), SUB_VEL_CERO)
        self._escribir(HOMING_ACELERACION, TAM_4_BYTES,
                       int(aceleracion_mm_s2 * self.factor_si))

        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_ENABLE_OP)      # bit4 = 0
        self._escribir(CONTROLWORD, TAM_2_BYTES, CW_START_HOMING)   # flanco de bit4
        self.t_inicio_homing = time.time()
        print("[MOTOR] Homing lanzado")

    def homing_terminado(self):
        """True cuando el eje queda referenciado. Lanza excepcion si la D1 reporta error."""
        transcurrido = time.time() - self.t_inicio_homing
        if transcurrido < RETARDO_ARRANQUE_HOMING:
            return False  # el bit 12 aun puede ser el del homing anterior

        estado = self.leer_estado()
        if (estado & SW_FALLO) != 0:
            raise Exception("Fallo del motor durante el homing (bit 3)")
        if (estado & SW_HOMING_ERROR) != 0:
            raise Exception("Error de homing reportado por la D1 (bit 13)")
        if transcurrido > TIMEOUT_HOMING:
            raise Exception(f"Timeout de homing ({TIMEOUT_HOMING}s)")

        return (estado & SW_HOMING_ALCANZADO) != 0 and (estado & SW_OBJETIVO_ALCANZADO) != 0

    # ===== Cierre de conexion =====
    def close(self):
        try:
            self.socket.close()
        except (AttributeError, OSError):
            pass
