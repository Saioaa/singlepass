# -*- coding: utf-8 -*-
"""Punto de entrada de singlepass:  python main.py  (desde esta carpeta)

Crea los dispositivos, arranca la interfaz y cierra todo al salir.

Estructura (paquetes con __init__.py; imports absolutos desde esta carpeta):
    programa/        config, d1, mduino, registro, secuencia (comunes a todas las maquinas)
    programa/gis/    boards GIS (PMB y Epson/Atlas), pmb, vpi, temperatura del cabezal
    programa/aewa/   APRINT (cabezal Aewa en APMB4): arranque, protocolo remoto, propiedades
    programa/tinta/  sistema de tinta IMB (CoAP)
    interfaz/        ventana, paginas, mesa, .ui y ui_*.py generado
    recursos/        imagenes, template.vpi (datos que acompanan al programa)
    herramientas/    scripts sueltos para pruebas; la app no los usa
"""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from programa import config
from programa import registro
from programa.d1 import MotorAusente, MotorD1
from interfaz.interfaz import VentanaPrincipal
from programa.mduino import ClienteMDuino
from programa.gis.pmb import ClientePMB
from programa.aewa.aprint_comunicacion import Aprint

CODIGO_ERROR_MOTOR = 2
ARGUMENTOS_MOTOR = (config.IP_MOTOR, config.PUERTO_MOTOR,
                    config.LIMITE_MIN_MM, config.LIMITE_MAX_MM, config.FACTOR_SI)


def crear_motor():
    """MotorD1 conectado; si no responde y config.ARRANCAR_SIN_MOTOR, un
    MotorAusente (la app arranca con el eje deshabilitado)."""
    try:
        return MotorD1(*ARGUMENTOS_MOTOR)
    except OSError as e:
        if not config.ARRANCAR_SIN_MOTOR:
            raise
        print(f"[MOTOR] AVISO: sin variador D1 ({config.IP_MOTOR}: {e}). "
              "La app arranca con el eje deshabilitado")
        return MotorAusente(*ARGUMENTOS_MOTOR)


def crear_dispositivos():
    motor = crear_motor()
    mduino = ClienteMDuino(config.IP_MDUINO, config.PUERTO_MDUINO)
    mduino.iniciar()
    pmb = ClientePMB(config.IP_PMB, config.PUERTO_PMB)   # se conecta al entrar en su pagina
    aprint = Aprint()                                     # se conecta si hay un APMB4 en Programa
    return motor, mduino, pmb, aprint


def main():
    # lo primero: a partir de aqui todo print y traceback va tambien al .log del dia
    registro.iniciar(config.CARPETA_LOGS)
    app = QApplication(sys.argv)

    try:
        motor, mduino, pmb, aprint = crear_dispositivos()
    except OSError as e:
        QMessageBox.critical(None, "singlepass",
                             f"No se ha podido conectar con el variador D1 "
                             f"({config.IP_MOTOR}):\n{e}")
        sys.exit(CODIGO_ERROR_MOTOR)

    ventana = VentanaPrincipal(motor, mduino, pmb, aprint)
    app.aboutToQuit.connect(aprint.cerrar)
    app.aboutToQuit.connect(pmb.cerrar)
    app.aboutToQuit.connect(motor.close)
    app.aboutToQuit.connect(mduino.cerrar)
    app.aboutToQuit.connect(registro.cerrar)   # el ultimo: los cierres anteriores aun se registran
    ventana.ajustar_a_pantalla()
    ventana.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
