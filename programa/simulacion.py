# -*- coding: utf-8 -*-
"""Dispositivos simulados para probar la secuencia sin maquina.

MotorSimulado  : misma interfaz que MotorD1 (d1.py) con un perfil trapezoidal
                 de velocidad calculado en tiempo real.
MDuinoSimulado : misma interfaz que ClienteMDuino (mduino.py); en vez de enviar
                 por TCP emite senales para que la interfaz lo muestre.
"""

import math
import time

from PySide6.QtCore import QObject, Signal

# ===== VALORES POR DEFECTO DEL MOTOR (mm/s, mm/s2) =====
VELOCIDAD_POR_DEFECTO    = 100.0
ACELERACION_POR_DEFECTO  = 100.0
DECELERACION_POR_DEFECTO = 100.0
STATUSWORD_OPERATIVO     = 0x0637   # Operation Enabled + target reached, sin fallo


class _Perfil:
    """Movimiento trapezoidal x0 -> xf iniciado en t0 (tiempos en s, mm)."""

    def __init__(self, x0, xf, v, a, d):
        self.t0 = time.monotonic()
        self.x0 = x0
        self.xf = xf
        self.sentido = 1.0 if xf >= x0 else -1.0
        distancia = abs(xf - x0)

        v_pico = min(v, math.sqrt(2.0 * distancia * a * d / (a + d)))
        self.t_acel = v_pico / a
        self.t_decel = v_pico / d
        d_acel = 0.5 * a * self.t_acel ** 2
        d_decel = 0.5 * d * self.t_decel ** 2
        self.t_crucero = max(0.0, (distancia - d_acel - d_decel) / v_pico) if v_pico > 0 else 0.0
        self.v_pico, self.a, self.d = v_pico, a, d
        self.d_acel, self.d_decel = d_acel, d_decel
        self.duracion = self.t_acel + self.t_crucero + self.t_decel

    def posicion(self, ahora):
        t = ahora - self.t0
        if t >= self.duracion:
            return self.xf, True
        if t < self.t_acel:
            s = 0.5 * self.a * t ** 2
        elif t < self.t_acel + self.t_crucero:
            s = self.d_acel + self.v_pico * (t - self.t_acel)
        else:
            tr = t - self.t_acel - self.t_crucero
            s = self.d_acel + self.v_pico * self.t_crucero + self.v_pico * tr - 0.5 * self.d * tr ** 2
        return self.x0 + self.sentido * s, False


class MotorSimulado:
    """Eje simulado. Las posiciones se expresan en mm, como en MotorD1."""

    def __init__(self, limite_min, limite_max, posicion_inicial=0.0):
        self.limite_min = limite_min
        self.limite_max = limite_max
        self._posicion = posicion_inicial
        self._perfil = None
        self._velocidad = VELOCIDAD_POR_DEFECTO
        self._aceleracion = ACELERACION_POR_DEFECTO
        self._deceleracion = DECELERACION_POR_DEFECTO

    # ----- parametros -----
    def set_velocidad(self, mm_s):
        self._velocidad = max(float(mm_s), 1e-6)

    def set_aceleracion(self, mm_s2):
        self._aceleracion = max(float(mm_s2), 1e-6)

    def set_deceleracion(self, mm_s2):
        self._deceleracion = max(float(mm_s2), 1e-6)

    def _validar(self, posicion_mm):
        return max(self.limite_min, min(self.limite_max, posicion_mm))

    # ----- estado -----
    def leer_posicion(self):
        if self._perfil is not None:
            self._posicion, terminado = self._perfil.posicion(time.monotonic())
            if terminado:
                self._perfil = None
        return self._posicion

    def movimiento_terminado(self):
        self.leer_posicion()
        return self._perfil is None

    def leer_estado(self):
        return STATUSWORD_OPERATIVO

    def hay_fallo(self):
        return False

    def resetear_fallo(self):
        pass

    # ----- movimiento -----
    def mover_a(self, posicion_mm, esperar=False, timeout=None):
        destino = self._validar(posicion_mm)
        self._perfil = _Perfil(self.leer_posicion(), destino,
                               self._velocidad, self._aceleracion, self._deceleracion)
        if esperar:
            time.sleep(self._perfil.duracion)
            self.leer_posicion()

    def esperar_fin_movimiento(self, timeout=None):
        while not self.movimiento_terminado():
            time.sleep(0.01)

    def mover_manual(self, mm_s, sentido):
        destino = self.limite_max if sentido > 0 else self.limite_min
        self._perfil = _Perfil(self.leer_posicion(), destino,
                               float(mm_s), self._aceleracion, self._deceleracion)

    def parar(self):
        self._posicion = self.leer_posicion()
        self._perfil = None

    def reanudar(self):
        pass

    # ----- encendido / homing / cierre: sin efecto -----
    def set_modo(self, modo, timeout=None):
        pass

    def habilitar(self):
        pass

    def deshabilitar(self):
        pass

    def home(self, *argumentos, **opciones):
        self._perfil = None
        self._posicion = self.limite_min

    def homing_terminado(self):
        return True

    def close(self):
        pass


class MDuinoSimulado(QObject):
    """M-Duino simulado: registra lo que se le ordena y lo emite por senales."""

    pulso_enviado     = Signal()
    lamparas_cambiadas = Signal(int)
    seta_cambiada     = Signal(bool)      # mantiene la interfaz de ClienteMDuino

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pwm_lamparas = 0

    def iniciar(self):
        pass

    def esta_conectado(self):
        return True

    def enviar(self, mensaje):
        return True

    def pulso_impresion(self):
        self.pulso_enviado.emit()
        return True

    def lamparas(self, pwm):
        self.pwm_lamparas = int(pwm)
        self.lamparas_cambiadas.emit(self.pwm_lamparas)
        return True
