# -*- coding: utf-8 -*-
"""Parametros de la maquina y rutas del proyecto.

Unico sitio donde se tocan IPs, limites de carrera y geometria de la barra.
"""

import os
import sys
from pathlib import Path

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
CARPETA_FUENTES   = os.path.join(CARPETA_RECURSOS, "fuentes")   # Nunito (.ttf): la carga interfaz.py
RUTA_GUIA_EJE     = os.path.join(CARPETA_IMAGENES, "guia_eje_x_blanca.png")
RUTA_PLANTILLA_VPI = os.path.join(CARPETA_RECURSOS, "template.vpi")   # base de los VPI (gis/vpi.py)

# ===== RUTAS DE DATOS DEL USUARIO (fuera del programa: sobreviven a reinstalar) =====
CARPETA_DATOS = os.path.join(os.path.expanduser("~"), "MATERIALIGHT")   # tambien RIPOutput (vpi.py)
CARPETA_LOGS  = os.path.join(CARPETA_DATOS, "Logging")                  # un .log por dia
RUTA_AJUSTES  = os.path.join(CARPETA_DATOS, "ajustes.json")             # campos de la interfaz

# ===== VARIADOR D1 (eje X) =====
IP_MOTOR      = "192.168.79.73"
PUERTO_MOTOR  = 502
# Si el D1 no responde al arrancar, la app arranca igual con el eje ausente
# (movimientos y secuencia rechazados con aviso en el log): para probar la app
# en un PC sin la maquina (APRINT, print server...). False: la app no arranca.
ARRANCAR_SIN_MOTOR = True
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

# ===== AEWA / APRINT (cabezal Ricoh en APMB4): programa/aewa, print_server_aewa.py =====
# Protocolo remoto TCP de APRINT (Printer Settings -> Remote). APRINT escucha en
# la IP de red del ordenador donde corre (la que muestra esa pestana). Se prueba
# IP_APRINT; si no responde, las IPs de los adaptadores de este ordenador, y en
# el fichero de log queda un AVISO con la que ha funcionado.
IP_APRINT = "192.168.1.162"
PUERTO_APRINT = 1025
# Arranque de APRINT desde la app: si no responde al conectar y no esta abierto,
# la app lo abre (minimizado u "oculto": opcion -hidden) y espera a que escuche.
# RUTA_APRINT: "Destino" del acceso directo de APRINT; None: se busca APRINT*.exe
# en CARPETAS_BUSQUEDA_APRINT. Si la app lo ha abierto, lo cierra al salir.
ABRIR_APRINT = True
RUTA_APRINT = Path(r"C:\Program Files\AEWA\APRINT\bin\APRINT.exe")
CARPETAS_BUSQUEDA_APRINT = (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)"),
                            Path(r"C:\aewa"), Path(r"C:\APRINT"))
MODO_ARRANQUE_APRINT = "minimizado"
ESPERA_ARRANQUE_APRINT_S = 60.0
CERRAR_APRINT_AL_SALIR = True
# Cabezal Ricoh MH5xxx: 4 filas de boquillas escalonadas que juntas dan la
# resolucion nativa a lo largo del cabezal (aviso si APRINT tiene filas desactivadas)
CABEZAL_FILAS = 4
RESOLUCION_NATIVA_CABEZAL_DPI = 600
# Job de APRINT ("ji"): posiciones en pixeles a esta resolucion
APRINT_DPI_POSICION = 600
# Ejes del job en la impresora "Singlepass BW": X = a lo largo del cabezal (ancho
# util ANCHO_CABEZAL_AEWA_MM, la "mesa" que muestra APRINT), Y = sentido de avance
# de la mesa (el blanco por delante = offset hasta el cabezal va en Y). La pagina
# de APRINT (Printer Settings -> General) debe ser mas larga que el mayor offset
# + imagen posible (distancia del cabezal en la barra).
ANCHO_CABEZAL_AEWA_MM = 54.1867
# Y de la mesa (mm) en la que empieza el cabezal (su primera boquilla): la X de la
# imagen en el job es su Y en la mesa menos esta. PROVISIONAL: medir al montar la board.
Y_CABEZAL_AEWA_MM = 0.0
# Orientacion de la imagen en el job respecto a la mesa (X de la mesa = avance, Y =
# a lo largo del cabezal): giro horario que se suma al de la pagina y espejos que
# se aplican ademas de los de la pagina. Con 270 el borde x + ancho (el que pasa
# primero bajo el cabezal) queda arriba (Y = offset) y la Y de la mesa va hacia +X.
# PROVISIONAL: comprobar con el PDF del codigo de barras; corregir aqui si sale
# girado o espejado.
GIRO_JOB_AEWA = 270
ESPEJO_JOB_X_AEWA = True
ESPEJO_JOB_Y_AEWA = False

# ===== TEST DE CABEZAL (boton test_cabezal de Print Server AEWA) =====
# PNG de 1 bit hecho pixel a pixel (1280 filas = una por boquilla, a 600 dpi), de
# la app MBD-F-500; va con la app en recursos/test_cabezal. Se imprime a 600 x 600
# dpi para que cada pixel sea una gota, en esta posicion de la mesa.
RUTA_TEST_CABEZAL = os.path.join(CARPETA_RECURSOS, "test_cabezal", "test_cabezal.png")
TEST_CABEZAL_X_MM = 0.0
TEST_CABEZAL_Y_MM = 0.0
TEST_CABEZAL_RES_HORIZONTAL_DPI = 600
TEST_CABEZAL_RES_VERTICAL_DPI = 600

# ===== INSERTAR TEXTO (boton texto_variable de Print Server AEWA) =====
# Texto en un PDF vectorial propio, segundo objeto del job (programa/aewa/texto_trabajo.py)
TEXTO_FUENTE = "Nunito"           # familia de las fuentes de CARPETA_FUENTES
TEXTO_COLOR = "#000000"
TEXTO_PUNTOS_INICIAL = 16.0       # al insertarlo; despues se cambia con las esquinas
TEXTO_PUNTOS_MIN = 4.0
TEXTO_PUNTOS_MAX = 500.0
TEXTO_SEPARACION_MM = 5.0         # al insertarlo, debajo de la imagen
NOMBRE_PDF_TEXTO = "texto.pdf"    # en la carpeta del trabajo
# Impresora de APRINT "Singlepass BW" (Ricoh MH5xxx, un cabezal): en Printer
# Settings -> General la resolucion HORIZONTAL (a lo largo del cabezal, paso de
# boquilla) es fija y la VERTICAL (sentido del movimiento de la mesa, por el
# encoder) se elige. En la interfaz se ofrecen las mismas opciones que APRINT.
RESOLUCIONES_HORIZONTALES_AEWA_DPI = (600,)
RESOLUCIONES_VERTICALES_AEWA_DPI = (150, 300, 450, 600, 900, 1200, 2400, 3000)
RESOLUCION_VERTICAL_AEWA_POR_DEFECTO = 600
# Un solo cabezal en una pasada: sin multipass (pasos = 1 siempre)
PASOS_AEWA = 1

# ===== SISTEMA DE TINTA (IMB, CoAP puerto 5683): tinta.py =====
IP_TINTA    = "192.168.79.75"
CANAL_TINTA = 1
# Tiempo maximo para que el IMB confirme un cambio de estado. Medido: Dormant 1 s,
# Idle < 1 s, Flow 4 s, una purga completa unos 10 s.
TINTA_CONFIRMACION_S = 30.0
# Orden CoAP del boton RESET (/cmd/<orden>?uc=<canal>): "stop" lleva el IMB a Dormant
# al instante, como la seta de la app de GIS (a proposito: es la parada rapida).
ORDEN_RESET_IMB = "stop"
# Limites que admite GUARDAR (PROVISIONAL: confirmar con el fabricante). Como en
# la app de 4 canales: idle y delta - negativas, delta + positiva.
PRESION_IDLE_MIN   = -5000
PRESION_IDLE_MAX   = 0
PRESION_INLET_MIN  = 0
PRESION_INLET_MAX  = 5000
PRESION_OUTLET_MIN = -5000
PRESION_OUTLET_MAX = 0
# Duracion de la purga (parametro PUTO del IMB, en segundos; de fabrica 6).
# Medido: la purga dura PUTO s y luego ~4-6 s de retorno a Flow.
TIEMPO_PURGA_MIN_S = 1
TIEMPO_PURGA_MAX_S = 60
# Tras GUARDAR, pedir al IMB que persista los ajustes en su memoria no volatil
# (/nv/save); si no, PUTO vuelve al valor anterior al reiniciar el IMB.
GUARDAR_AJUSTES_EN_IMB = True

# ===== TEMPERATURA DEL CABEZAL (por el PMB): cabezal_pmb.py =====
# La real y la consigna llegan en los mensajes de estado de cabezales del Print
# Controller (I,<id>,H,...). La consigna se escribe en este parametro del Print
# Controller con P,C,P (como XOffset).
# Los parametros se nombran con su ruta en el arbol del Print Controller (como XOffset):
# "<RUTA_NODO_PMB>,<cabezal>,<SUBRUTA_CALENTADOR>,TargetControllerTemp". El nombre del
# cabezal (HIB-1...) sale del estado de cabezales que envia el propio Print Controller.
RUTA_NODO_PMB = "Print Manager,Print Line Manager,Master PMB"
SUBRUTA_CALENTADOR = "Heater Controllers,Head 1 Heater Controller"
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
