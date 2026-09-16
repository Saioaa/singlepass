# -*- coding: utf-8 -*-
"""Punto de entrada de singlepass:  python main.py

Crea los dispositivos, arranca la interfaz y cierra todo al salir.
"""

import os
import sys

CARPETA_RAIZ     = os.path.dirname(os.path.realpath(__file__))
CARPETA_PROGRAMA = os.path.join(CARPETA_RAIZ, "programa")
sys.path.insert(0, CARPETA_PROGRAMA)   # para importar los modulos de programa/

from PySide6.QtWidgets import QApplication, QMessageBox   # noqa: E402

import config                                   # noqa: E402
from d1 import MotorD1                          # noqa: E402
from interfaz import VentanaPrincipal           # noqa: E402
from mduino import ClienteMDuino                # noqa: E402
from pmb import ClientePMB                      # noqa: E402

CODIGO_ERROR_MOTOR = 2


def crear_dispositivos():
    motor = MotorD1(config.IP_MOTOR, config.PUERTO_MOTOR,
                    config.LIMITE_MIN_MM, config.LIMITE_MAX_MM, config.FACTOR_SI)
    mduino = ClienteMDuino(config.IP_MDUINO, config.PUERTO_MDUINO)
    mduino.iniciar()
    pmb = ClientePMB()   # se conecta al entrar en su pagina
    return motor, mduino, pmb


def main():
    # los iconos del .ui usan rutas relativas (../imagenes/...): fijar el
    # directorio de trabajo para que se resuelvan igual desde cualquier sitio
    os.chdir(config.CARPETA_PROGRAMA)
    app = QApplication(sys.argv)

    try:
        motor, mduino, pmb = crear_dispositivos()
    except OSError as e:
        QMessageBox.critical(None, "singlepass",
                             f"No se ha podido conectar con el variador D1 "
                             f"({config.IP_MOTOR}):\n{e}")
        sys.exit(CODIGO_ERROR_MOTOR)

    ventana = VentanaPrincipal(motor, mduino, pmb)
    app.aboutToQuit.connect(pmb.cerrar)
    app.aboutToQuit.connect(motor.close)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
