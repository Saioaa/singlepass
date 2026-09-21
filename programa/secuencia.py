# -*- coding: utf-8 -*-
"""Secuencia de impresion (maquina de estados guiada por un QTimer).

Los recorridos (fin de impresion, inicio y fin de curado) no se leen de la
interfaz: los calcula la pagina Programa a partir de los modulos montados y
llegan en ParametrosPrograma. La secuencia solo sabe de posiciones.

Uso:
    self.secuencia = SecuenciaImpresion(motor, mduino, self.pagina_pmb.esta_lista)
    self.secuencia.start(ParametrosPrograma(...))
"""

import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

# ===== TEMPORIZACION =====
PERIODO_SECUENCIA_MS = 50     # ms - intervalo del QTimer despachador
RETARDO_ARRANQUE_MOV = 0.15   # s - ventana ciega tras lanzar un movimiento
T_LAMPARAS_ON        = 4.0    # s que tardan en encender
T_LAMPARAS_OFF       = 2.0    # s que tardan en apagar

# ===== LAMPARAS =====
PWM_CURADO   = 50   # PWM de las lamparas durante el curado (%)
PWM_APAGADAS = 0

# ===== ETAPAS =====
ETAPA_ESPERA        = "espera"        # secuencia parada (antes "etapa1")
ETAPA_REPOSO        = "reposo"        # E0: ir a reposo antes de empezar
ETAPA_SIN_CURADO    = "sin_curado"    # E2: ida y vuelta a velocidad de impresion
ETAPA_IDA_IMPRESION = "ida_impresion" # E3: lamparas on + ida de impresion
ETAPA_CURADO        = "curado"        # E4: pasadas de curado
ETAPA_FIN           = "fin"           # E5: lamparas off + vuelta a reposo
ETAPA_PARADA        = "parada"        # E6: parada ordenada por el operario


@dataclass
class ParametrosPrograma:
    vel_impresion: float
    acel_impresion: float
    decel_impresion: float
    vel_curado: float
    acel_curado: float
    decel_curado: float
    pasadas_curado: int            # la ida de impresion cuenta como pasada 1
    fin_impresion: float           # mm: la mesa entera ha pasado el cabezal (y el curado, si lo hay)
    inicio_curado: float           # mm: mesa entera antes del primer modulo de curado
    fin_curado: float              # mm: mesa entera despues del ultimo modulo de curado
    hay_curado: bool = False       # hay modulo NIR/secador y pasadas > 0


class SecuenciaImpresion(QObject):

    terminada = Signal()    # la secuencia ha vuelto a ESPERA

    def __init__(self, motor, mduino, pmb_listo, posicion_reposo, parent=None):
        super().__init__(parent)
        self.motor = motor
        self.mduino = mduino
        self._pmb_listo = pmb_listo   # callable -> bool: el PMB esta armado (se arma en la pagina PMB)
        self.posicion_reposo = posicion_reposo

        self.timer = QTimer(self)
        self.timer.setInterval(PERIODO_SECUENCIA_MS)
        self.timer.timeout.connect(self.avanzar)

        self._etapas = {
            ETAPA_REPOSO:        self.etapa_reposo,
            ETAPA_SIN_CURADO:    self.etapa_sin_curado,
            ETAPA_IDA_IMPRESION: self.etapa_ida_impresion,
            ETAPA_CURADO:        self.etapa_curado,
            ETAPA_FIN:           self.etapa_fin,
            ETAPA_PARADA:        self.etapa_parada,
        }

        # --- estado ---
        self.parametros = None
        self.etapa = ETAPA_ESPERA
        self.subpaso = 0
        self.contpas = 0
        self.seta = False
        self.referencia_pendiente = False   # !!! CUIDADO: en el original estaba falseado a False
        self.destino_curado = 0
        self.t_ultimo_mov = 0.0
        self.t_espera = 0.0
        self.senal_lamparas = PWM_APAGADAS
        self.senal_impresion = False

    # ===== entradas externas =====
    def set_seta(self, pulsada):
        self.seta = pulsada
        if pulsada:
            self.referencia_pendiente = True

    def set_referencia_pendiente(self, pendiente):
        self.referencia_pendiente = pendiente

    def en_marcha(self):
        return self.timer.isActive()

    # ===== arranque / parada =====
    def start(self, parametros):
        if self.referencia_pendiente or self.seta or not self._pmb_listo():
            return False
        self.parametros = parametros
        self.contpas = parametros.pasadas_curado
        self.etapa = ETAPA_REPOSO
        self.subpaso = 0
        self.timer.start()
        return True

    def stop(self):
        self.senal_lamparas = PWM_APAGADAS   # TODO: apagar senal real
        self.motor.parar()
        self.etapa = ETAPA_PARADA
        self.subpaso = 0
        self.timer.start()

    def paro_seta(self):
        self.timer.stop()
        self.senal_lamparas = PWM_APAGADAS
        self.mduino.lamparas(PWM_APAGADAS)
        self.senal_impresion = False
        self._terminar()
        self.referencia_pendiente = True   # obliga a re-referenciar antes del proximo start

    def _terminar(self):
        self.etapa = ETAPA_ESPERA
        self.subpaso = 0
        self.timer.stop()
        self.terminada.emit()

    # ===== despachador (lo llama el timer cada PERIODO_SECUENCIA_MS) =====
    def avanzar(self):
        if self.seta:
            self.paro_seta()
            return
        if time.time() - self.t_ultimo_mov < RETARDO_ARRANQUE_MOV:
            return
        if not self.motor.movimiento_terminado():
            return
        accion = self._etapas.get(self.etapa)
        if accion is not None:
            accion()

    # ===== auxiliares =====
    def mover_secuencia(self, destino):
        """Lanza un movimiento y marca el instante de arranque."""
        self.motor.mover_a(destino, esperar=False)
        self.t_ultimo_mov = time.time()

    def params_impresion(self):
        self.motor.set_velocidad(self.parametros.vel_impresion)
        self.motor.set_aceleracion(self.parametros.acel_impresion)
        self.motor.set_deceleracion(self.parametros.decel_impresion)

    def params_curado(self):
        self.motor.set_velocidad(self.parametros.vel_curado)
        self.motor.set_aceleracion(self.parametros.acel_curado)
        self.motor.set_deceleracion(self.parametros.decel_curado)

    # ===== etapas =====
    def etapa_reposo(self):
        """E0: asegurar la posicion de reposo antes de empezar la pasada."""
        if self.subpaso == 0:
            self.params_impresion()
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 1
        elif self.subpaso == 1:
            curando = self.parametros.hay_curado and self.contpas > 0
            self.etapa = ETAPA_IDA_IMPRESION if curando else ETAPA_SIN_CURADO
            self.subpaso = 0

    def etapa_sin_curado(self):
        """E2: sin curado -> ida y vuelta a velocidad de impresion."""
        if self.subpaso == 0:
            self.params_impresion()
            self.senal_impresion = True
            self.mduino.pulso_impresion()
            self.mover_secuencia(self.parametros.fin_impresion)
            self.subpaso = 1
        elif self.subpaso == 1:
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 2
        elif self.subpaso == 2:
            self.senal_impresion = False
            self._terminar()

    def etapa_ida_impresion(self):
        """E3: encender lamparas, esperar, e ida de impresion (= pasada 1)."""
        if self.subpaso == 0:
            self.senal_lamparas = PWM_CURADO
            self.mduino.lamparas(PWM_CURADO)
            self.t_espera = time.time() + T_LAMPARAS_ON
            self.subpaso = 1
        elif self.subpaso == 1:
            if time.time() < self.t_espera:   # esperando encendido
                return
            self.params_impresion()
            self.senal_impresion = True
            self.mduino.pulso_impresion()
            self.mover_secuencia(self.parametros.fin_impresion)
            self.subpaso = 2
        elif self.subpaso == 2:
            self.senal_impresion = False
            self.destino_curado = self.parametros.fin_curado   # la ida ha acabado en el extremo lejano
            self.contpas -= 1   # la ida ya fue la pasada 1
            if self.contpas > 0:
                self.etapa = ETAPA_CURADO
                self.destino_curado = self.parametros.inicio_curado   # siguiente: volver curando
            else:
                self.etapa = ETAPA_FIN
            self.subpaso = 0

    def etapa_curado(self):
        """E4: pasadas de curado alternando entre inicio_curado y fin_curado."""
        if self.subpaso == 0:
            self.params_curado()
            self.mover_secuencia(self.destino_curado)
            self.subpaso = 1
        elif self.subpaso == 1:
            self.contpas -= 1
            if self.contpas > 0:
                if self.destino_curado == self.parametros.fin_curado:
                    self.destino_curado = self.parametros.inicio_curado
                else:
                    self.destino_curado = self.parametros.fin_curado
                self.subpaso = 0
            else:
                self.etapa = ETAPA_FIN
                self.subpaso = 0

    def etapa_fin(self):
        """E5: apagar lamparas y volver a reposo."""
        if self.subpaso == 0:
            self.senal_lamparas = PWM_APAGADAS
            self.mduino.lamparas(PWM_APAGADAS)
            if self.destino_curado == self.parametros.fin_curado:
                # acabamos al final: esperar apagado y luego volver
                self.t_espera = time.time() + T_LAMPARAS_OFF
                self.subpaso = 1
            else:
                # acabamos en inicio de curado: apagar y volver a la vez
                self.subpaso = 2
        elif self.subpaso == 1:
            if time.time() < self.t_espera:
                return
            self.subpaso = 2
        elif self.subpaso == 2:
            self.params_curado()
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 3
        elif self.subpaso == 3:
            self._terminar()

    def etapa_parada(self):
        """E6: parada -> apagar lamparas, reposo y apagar la secuencia."""
        if self.subpaso == 0:
            self.senal_lamparas = PWM_APAGADAS   # TODO: apagar senal real
            self.senal_impresion = False
            self.motor.reanudar()
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 1
        elif self.subpaso == 1:
            self._terminar()
