# -*- coding: utf-8 -*-
"""Parametros de la maquina y rutas del proyecto.

Unico sitio donde se tocan IPs, limites de carrera y geometria de la barra.
"""

import os
import sys

# ===== RUTAS DEL PROGRAMA =====
# Ejecutando desde el codigo: singlepass/ es la raiz (este fichero esta en programa/).
# Empaquetado con PyInstaller (sys.frozen): la raiz es sys._MEIPASS y recursos/
# se anade con --add-data "recursos;recursos".
if getattr(sys, "frozen", False):
    CARPETA_RAIZ = sys._MEIPASS
else:
    CARPETA_RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
CARPETA_RECURSOS  = os.path.join(CARPETA_RAIZ, "recursos")
CARPETA_IMAGENES  = os.path.join(CARPETA_RECURSOS, "imagenes")
RUTA_GUIA_EJE     = os.path.join(CARPETA_IMAGENES, "guia_eje_x_blanca.png")
RUTA_PLANTILLA_VPI = os.path.join(CARPETA_RECURSOS, "template.vpi")   # base de los VPI (gis/vpi.py)

# ===== RUTAS DE DATOS DEL USUARIO (fuera del programa: sobreviven a reinstalar) =====
CARPETA_DATOS = os.path.join(os.path.expanduser("~"), "MATERIALIGHT")   # tambien RIPOutput (vpi.py)
CARPETA_LOGS  = os.path.join(CARPETA_DATOS, "Logging")                  # un .log por dia
RUTA_AJUSTES  = os.path.join(CARPETA_DATOS, "ajustes.json")             # campos de la interfaz

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
POSICION_REPOSO_MM = 50     # arranque y fin de cada impresion (desde aqui se envia el PULSE)
BARRA_MM           = 2200   # longitud fisica de la barra
MODULO_MM          = 125    # ancho de cada modulo a lo largo de la barra
# La mesa ocupa [p, p + MESA_ANCHO_MM] sobre la barra cuando el eje esta en p;
# un modulo montado a distancia d ocupa [d, d + MODULO_MM]. Los recorridos de la
# secuencia se calculan con esto a partir de los modulos de la pagina Programa.

# ===== GIS PRINT SERVER (PMB-C8 / PMB-C2) =====
IP_PMB     = "localhost"   # Print Server de GIS, corre en este mismo PC
PUERTO_PMB = 2000
# PROVISIONAL: el pulso del rele R1_4 del M-Duino no llega a la entrada TTL del PMB
# (en la SM-200 si se ve en el Encoder Monitor de Atlas). Mientras se arregla, la
# secuencia envia el PULSE al M-Duino y ADEMAS el print go por software al Print
# Controller (P,SPG). Requiere PrintGoSource = Software en el nodo PMB de GIS.
# Con el cable arreglado: False y PrintGoSource = TTL.
PRINT_GO_TAMBIEN_POR_SOFTWARE = True

# ===== ATLAS (SM-200 / Epson) =====
IP_ATLAS      = "localhost"        # Atlas Server (API REST), corre en este mismo PC
PUERTO_ATLAS  = 5000
IP_HMB        = "192.168.79.134"   # Head Manager Board: API propia en el 8080 (host board, cabezales)
PUERTO_HMB    = 8080
IP_SM200      = "192.168.79.1"     # tarjeta encoder / print go: solo habla con el Atlas Server
PUERTO_SM200  = 8080

# ===== MESA DE IMPRESION (X = direccion del movimiento) =====
# La mesa se define en pixeles a una resolucion de referencia: el alto son los
# MESA_ALTO_PX del area de impresion y el ancho, los pixeles enteros mas cercanos
# a MESA_ANCHO_OBJETIVO_MM a esa misma resolucion.
MM_POR_PULGADA = 25.4
DPI_MESA       = 600      # resolucion de referencia en la que se cuentan los pixeles de la mesa
MESA_ALTO_PX   = 5072
MESA_ANCHO_OBJETIVO_MM = 297
MESA_ANCHO_PX  = round(MESA_ANCHO_OBJETIVO_MM * DPI_MESA / MM_POR_PULGADA)   # 7016 px
MESA_ANCHO_MM  = MESA_ANCHO_PX * MM_POR_PULGADA / DPI_MESA                    # 297.01 mm
MESA_ALTO_MM   = MESA_ALTO_PX * MM_POR_PULGADA / DPI_MESA                     # 214.71 mm
# Resolucion con la que se mide una imagen mientras no hay modo de impresion cargado.
# El tamano fisico de la imagen = pixeles / dpi del modo (los dpi del archivo se ignoran).
DPI_IMAGEN_POR_DEFECTO = 600

# ===== SISTEMA DE TINTA (IMB, CoAP puerto 5683): tinta.py =====
IP_TINTA    = "192.168.79.75"
CANAL_TINTA = 1
# Tiempo maximo para que el IMB confirme un cambio de estado (pasar a Dormant
# puede tardar bastante)
TINTA_CONFIRMACION_S = 180.0
# Limites que admite GUARDAR (PROVISIONAL: confirmar con el fabricante). Como en
# la app de 4 canales: idle y delta - negativas, delta + positiva. El IMB tiene
# ahora idle -300, delta + 1000 y delta - -1500.
PRESION_IDLE_MIN   = -1000
PRESION_IDLE_MAX   = 0
PRESION_INLET_MIN  = 0
PRESION_INLET_MAX  = 3000
PRESION_OUTLET_MIN = -3000
PRESION_OUTLET_MAX = 0

# ===== TEMPERATURA DEL CABEZAL (por el PMB): cabezal_pmb.py =====
# La real y la consigna llegan en los mensajes de estado de cabezales del Print
# Controller (I,<id>,H,...). La consigna se escribe en este parametro del Print
# Controller con P,C,P (como XOffset).
# Los parametros se nombran con su ruta en el arbol del Print Controller (como XOffset):
# "<RUTA_NODO_PMB>,<nombre del cabezal>,TargetControllerTemp". El nombre del cabezal
# (HIB-1...) sale del estado de cabezales que envia el propio Print Controller.
RUTA_NODO_PMB = "Print Manager,Print Line Manager,Master PMB"
PARAMETRO_CONSIGNA_CABEZAL = "TargetControllerTemp"
# Consigna que admite GUARDAR (PROVISIONAL: confirmar el maximo del cabezal)
TEMPERATURA_CABEZAL_MIN_C = 20.0
TEMPERATURA_CABEZAL_MAX_C = 60.0

# ===== OFFSET X DE IMPRESION (Print Controller) =====
# XOffset = DISTANCIA_CABEZAL (pagina Programa) - X_IMAGEN (mesa) - POSICION_PULSE_MM
POSICION_PULSE_MM   = POSICION_REPOSO_MM   # posicion del carro cuando se envia el PULSE
# Con print go por software (PROVISIONAL): si la mesa ya esta a menos de esto de reposo,
# la secuencia no la mueve (la board ya compenso la posicion real en el XOffset al armar).
TOLERANCIA_REPOSO_MM = 5.0
PARAMETRO_OFFSET_X  = f'"{RUTA_NODO_PMB},PhysicalPrePrintBufferLength"'
