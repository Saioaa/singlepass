# -*- coding: utf-8 -*-
"""Secuencia de impresion (maquina de estados guiada por un QTimer).

Los recorridos (fin de impresion, inicio y fin de curado) no se leen de la
interfaz: los calcula la pagina Programa a partir de los modulos montados y
llegan en ParametrosPrograma. La secuencia solo sabe de posiciones.

Uso:
    self.secuencia = SecuenciaImpresion(motor, mduino, self.print_server.esta_lista, reposo)
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
PWM_APAGADAS = 0    # la potencia de curado llega en ParametrosPrograma.potencia_nir (%)

# ===== ETAPAS =====
# Transiciones: start -> reposo -> (sin_curado | ida_impresion | solo_curado) ...
#   sin_curado -> espera; ida_impresion -> curado | fin; solo_curado -> curado;
#   curado -> curado | fin; fin -> espera; stop -> parada -> espera
ETAPA_ESPERA        = "espera"        # secuencia parada
ETAPA_REPOSO        = "reposo"        # ir a reposo antes de empezar
ETAPA_SIN_CURADO    = "sin_curado"    # ida de impresion y vuelta, sin lamparas
ETAPA_IDA_IMPRESION = "ida_impresion" # lamparas on + ida de impresion (cuenta como pasada 1 de curado)
ETAPA_SOLO_CURADO   = "solo_curado"   # sin cabezal: lamparas on y primera pasada de curado
ETAPA_CURADO        = "curado"        # pasadas de curado entre inicio_curado y fin_curado
ETAPA_FIN           = "fin"           # lamparas off + vuelta a reposo
ETAPA_PARADA        = "parada"        # parada ordenada por el operario


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
    hay_impresion: bool = True     # hay cabezal activo: la secuencia envia PULSE e imprime
    requiere_armado: bool = True   # hay cabezal con board: exige todas las boards armadas
    potencia_nir: int = 0          # % de las lamparas NIR durante el curado (LAMP:<n> al M-Duino)
    potencia_secador: int = 0      # % del secador; sin salida en el M-Duino todavia, solo se guarda


class SecuenciaImpresion(QObject):

    terminada = Signal()    # la secuencia ha vuelto a ESPERA

    def __init__(self, motor, mduino, boards_listas, posicion_reposo, print_go_extra=None,
                 parent=None):
        super().__init__(parent)
        self.motor = motor
        self.mduino = mduino
        self._print_go_extra = print_go_extra   # callable opcional que se lanza junto al PULSE
        self._boards_listas = boards_listas   # callable -> bool: todas las boards activas armadas
        self.posicion_reposo = posicion_reposo

        self.timer = QTimer(self)
        self.timer.setInterval(PERIODO_SECUENCIA_MS)
        self.timer.timeout.connect(self.avanzar)

        self._etapas = {
            ETAPA_REPOSO:        self.etapa_reposo,
            ETAPA_SIN_CURADO:    self.etapa_sin_curado,
            ETAPA_IDA_IMPRESION: self.etapa_ida_impresion,
            ETAPA_SOLO_CURADO:   self.etapa_solo_curado,
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
        if self.referencia_pendiente or self.seta:
            return False
        if parametros.hay_impresion and parametros.requiere_armado and not self._boards_listas():
            return False
        self.parametros = parametros
        self.contpas = parametros.pasadas_curado
        self.etapa = ETAPA_REPOSO
        self.subpaso = 0
        self.timer.start()
        return True

    def stop(self):
        self.senal_lamparas = PWM_APAGADAS
        self.mduino.lamparas(PWM_APAGADAS)
        self.motor.parar()
        self.etapa = ETAPA_PARADA
        self.subpaso = 0
        self.timer.start()

    def paro_seta(self):
        self.timer.stop()
        self.senal_lamparas = PWM_APAGADAS
        self.mduino.lamparas(PWM_APAGADAS)
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
    def print_go(self):
        """Dispara la impresion: pulso del M-Duino y, si esta configurado, tambien por software."""
        self.mduino.pulso_impresion()
        if self._print_go_extra is not None:
            self._print_go_extra()

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
        """asegurar la posicion de reposo antes de empezar la pasada."""
        if self.subpaso == 0:
            self.params_impresion()
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 1
        elif self.subpaso == 1:
            curando = self.parametros.hay_curado and self.contpas > 0
            if not self.parametros.hay_impresion:
                self.etapa = ETAPA_SOLO_CURADO
            else:
                self.etapa = ETAPA_IDA_IMPRESION if curando else ETAPA_SIN_CURADO
            self.subpaso = 0

    def etapa_solo_curado(self):
        """sin cabezal -> encender lamparas, esperar y lanzar las pasadas de curado."""
        if self.subpaso == 0:
            self.senal_lamparas = self.parametros.potencia_nir
            self.mduino.lamparas(self.parametros.potencia_nir)
            self.t_espera = time.time() + T_LAMPARAS_ON
            self.subpaso = 1
        elif self.subpaso == 1:
            if time.time() < self.t_espera:
                return
            self.destino_curado = self.parametros.fin_curado   # primera pasada: reposo -> fin
            self.etapa = ETAPA_CURADO
            self.subpaso = 0

    def etapa_sin_curado(self):
        """sin curado -> ida y vuelta a velocidad de impresion."""
        if self.subpaso == 0:
            self.params_impresion()
            self.print_go()
            self.mover_secuencia(self.parametros.fin_impresion)
            self.subpaso = 1
        elif self.subpaso == 1:
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 2
        elif self.subpaso == 2:
            self._terminar()

    def etapa_ida_impresion(self):
        """encender lamparas, esperar, e ida de impresion (= pasada 1)."""
        if self.subpaso == 0:
            self.senal_lamparas = self.parametros.potencia_nir
            self.mduino.lamparas(self.parametros.potencia_nir)
            self.t_espera = time.time() + T_LAMPARAS_ON
            self.subpaso = 1
        elif self.subpaso == 1:
            if time.time() < self.t_espera:   # esperando encendido
                return
            self.params_impresion()
            self.print_go()
            self.mover_secuencia(self.parametros.fin_impresion)
            self.subpaso = 2
        elif self.subpaso == 2:
            self.destino_curado = self.parametros.fin_curado   # la ida ha acabado en el extremo lejano
            self.contpas -= 1   # la ida ya fue la pasada 1
            if self.contpas > 0:
                self.etapa = ETAPA_CURADO
                self.destino_curado = self.parametros.inicio_curado   # siguiente: volver curando
            else:
                self.etapa = ETAPA_FIN
            self.subpaso = 0

    def etapa_curado(self):
        """pasadas de curado alternando entre inicio_curado y fin_curado."""
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
        """apagar lamparas y volver a reposo."""
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
        """parada -> apagar lamparas, reposo y apagar la secuencia."""
        if self.subpaso == 0:
            self.senal_lamparas = PWM_APAGADAS
            self.mduino.lamparas(PWM_APAGADAS)
            self.motor.reanudar()
            self.mover_secuencia(self.posicion_reposo)
            self.subpaso = 1
        elif self.subpaso == 1:
            self._terminar()
