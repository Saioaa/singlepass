# -*- coding: utf-8 -*-
"""Parametros de la maquina y rutas del proyecto.

Unico sitio donde se tocan IPs, limites de carrera y geometria de la barra.
"""

import os

# ===== RUTAS =====
CARPETA_PROGRAMA = os.path.dirname(os.path.realpath(__file__))
CARPETA_IMAGENES = os.path.normpath(os.path.join(CARPETA_PROGRAMA, "..", "imagenes"))
RUTA_AJUSTES     = os.path.join(CARPETA_PROGRAMA, "ajustes.json")
RUTA_GUIA_EJE    = os.path.join(CARPETA_IMAGENES, "guia_eje_x_blanca.png")

# ===== VARIADOR D1 (eje X) =====
IP_MOTOR      = "192.168.79.73"
PUERTO_MOTOR  = 502
LIMITE_MIN_MM = 0
LIMITE_MAX_MM = 1200
FACTOR_SI     = 100   # la D1 trabaja en centesimas de milimetro (0x60A8 = 0xFB010000)

# ===== M-DUINO =====
IP_MDUINO     = "192.168.79.180"
PUERTO_MDUINO = 5000

# ===== GEOMETRIA DEL RECORRIDO =====
POSICION_REPOSO_MM = 50
FINAL_RECORRIDO_MM = 1200   # borde trasero al final del recorrido 1900
BARRA_MM           = 2200   # longitud fisica de la barra
MODULO_MM          = 125    # ancho de cada modulo
