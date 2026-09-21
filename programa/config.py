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
# Print go: False = pulso electrico del M-Duino (PrintGoSource = TTL/External en el
# nodo PMB de GIS). True = P,SPG por software (PrintGoSource = Software); solo
# para pruebas sin M-Duino.
PRINT_GO_POR_SOFTWARE = False

# ===== GEOMETRIA DEL RECORRIDO =====
POSICION_REPOSO_MM = 50     # arranque y fin de cada impresion (desde aqui se envia el PULSE)
BARRA_MM           = 2200   # longitud fisica de la barra
MODULO_MM          = 125    # ancho de cada modulo a lo largo de la barra
# La mesa ocupa [p, p + MESA_ANCHO_MM] sobre la barra cuando el eje esta en p;
# un modulo montado a distancia d ocupa [d, d + MODULO_MM]. Los recorridos de la
# secuencia se calculan con esto a partir de los modulos de la pagina Programa.

# ===== MESA DE IMPRESION (A4 apaisado: X = direccion del movimiento) =====
MESA_ANCHO_MM = 297
MESA_ALTO_MM  = 210

# ===== OFFSET X DE IMPRESION (Print Controller) =====
# XOffset = DISTANCIA_CABEZAL (pagina Programa) - X_IMAGEN (mesa) - POSICION_PULSE_MM
POSICION_PULSE_MM   = POSICION_REPOSO_MM   # posicion del carro cuando se envia el PULSE
PARAMETRO_OFFSET_X  = '"Print Manager,Print Line Manager,Master PMB,PhysicalPrePrintBufferLength"'
