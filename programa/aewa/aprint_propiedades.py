# -*- coding: utf-8 -*-
"""Propiedades de impresion de APRINT: leer y (paso 2) escribir dpi y pasos.

Ademas de los comandos de la guia, la libreria de aewa (apRemote.cpp) tiene
dos comandos hechos para esta maquina: "pm" (avance Y de multipass numero i;
se leen hasta que devuelve 0, como SECUENCIAS_PX de Node-RED) y "pS" (total de
franjas del job). Sirven para comprobar que nuestro plan coincide con APRINT.

Parametros de Get/Set Printer Parameter ("pg"/"pp") de la guia APRINT-Remote.
Los dpi van multiplicados por 1000. Pasos: modo multipass (100) "ninguno" para
1 paso, "multiples pasadas" + numero de pasadas (111, de 2 a 8) para el resto.
"""

import struct

from programa import config
from programa.aewa.aprint_comunicacion import TAM_ENTERO, ErrorAprint, u16

ESCALA_MILES = 1000

# ===== TIPOS DE PARAMETRO =====
PARAM_VERSION = 0
PARAM_DIALOGO_ABIERTO = 3
PARAM_IMPRIMIENDO = 4
PARAM_RETARDO_IMPRESION_UM = 12     # distancia entre la senal de inicio y la impresion
PARAM_DPI_HORIZONTAL = 15
PARAM_DPI_VERTICAL = 16
PARAM_ESPEJO_HORIZONTAL = 17
PARAM_ESPEJO_VERTICAL = 18
PARAM_MODO_IMPRESION = 40
PARAM_FUENTE_ENCODER = 41
PARAM_RESOLUCION_ENCODER = 43
PARAM_VELOCIDAD_ENCODER_VIRTUAL = 44   # cm/s x 1000
PARAM_BITS_POR_PIXEL = 46
PARAM_TRAMADO = 51
PARAM_BOTON_PRINT = 52
PARAM_FILAS_DESACTIVADAS = 53          # bit i = 1: fila i+1 del cabezal desactivada
PARAM_MODO_MULTIPASS = 100
PARAM_TIPO_MULTIPASS = 110
PARAM_NUMERO_PASADAS = 111

# ===== VALORES =====
MODO_MULTIPASS_NINGUNO = 0
MODO_MULTIPASS_COSIDO = 1
MODO_MULTIPASS_PASADAS = 2
ENCODER_REAL = 0
# Parametro 40 (pestana Motion, "Printing mode"): como se dispara cada franja.
# No tiene que ver con el multipass (parametro 100, pestana Multipass): la guia
# lo llama "single pass" porque cada disparo imprime una franja.
MODO_IMPRESION_EXTERNO = 0      # Single pass - External trigger (el pulso del M-Duino)
NOMBRES_MODO_IMPRESION = {MODO_IMPRESION_EXTERNO: "externo por franja", 1: "interno por franja",
                          2: "continuo"}
NOMBRES_MODO_MULTIPASS = {MODO_MULTIPASS_NINGUNO: "ninguno", MODO_MULTIPASS_COSIDO: "cosido",
                          MODO_MULTIPASS_PASADAS: "multiples pasadas"}
NOMBRES_TIPO_MULTIPASS = {0: "estatico", 1: "aleatorio"}
NOMBRES_TRAMADO = {0: "error diffusion", 1: "random error diffusion", 2: "stochastic",
                   3: "stochastic HQ", 4: "stochastic compatibility", 5: "custom screening",
                   6: "surface dither"}
DESCONOCIDO = "?"
BIT_FILA = 1
MICRAS_POR_MM = 1000
BITS_BYTE = 8
MASCARA_BYTE = 0xFF


def _version(valor):
    """0x00020103 -> 2.1.3"""
    return ".".join(str((valor >> desplazamiento) & MASCARA_BYTE)
                    for desplazamiento in (2 * BITS_BYTE, BITS_BYTE, 0))


def leer_propiedades(cliente):
    """Lee lo que interesa de APRINT. Devuelve un dict; un parametro que APRINT
    no conoce (version antigua) queda como None."""
    def leer(tipo):
        try:
            return cliente.leer_parametro(tipo)
        except ErrorAprint:
            return None

    p = {
        "version": leer(PARAM_VERSION),
        "dpi_horizontal": leer(PARAM_DPI_HORIZONTAL),
        "dpi_vertical": leer(PARAM_DPI_VERTICAL),
        "modo_multipass": leer(PARAM_MODO_MULTIPASS),
        "tipo_multipass": leer(PARAM_TIPO_MULTIPASS),
        "numero_pasadas": leer(PARAM_NUMERO_PASADAS),
        "modo_impresion": leer(PARAM_MODO_IMPRESION),
        "fuente_encoder": leer(PARAM_FUENTE_ENCODER),
        "resolucion_encoder": leer(PARAM_RESOLUCION_ENCODER),
        "velocidad_encoder_virtual": leer(PARAM_VELOCIDAD_ENCODER_VIRTUAL),
        "retardo_impresion_um": leer(PARAM_RETARDO_IMPRESION_UM),
        "espejo_horizontal": leer(PARAM_ESPEJO_HORIZONTAL),
        "espejo_vertical": leer(PARAM_ESPEJO_VERTICAL),
        "bits_por_pixel": leer(PARAM_BITS_POR_PIXEL),
        "tramado": leer(PARAM_TRAMADO),
        "filas_desactivadas": leer(PARAM_FILAS_DESACTIVADAS),
    }
    p["filas_activas"] = filas_activas(p["filas_desactivadas"])
    for clave in ("dpi_horizontal", "dpi_vertical", "resolucion_encoder"):
        if p[clave] is not None:
            p[clave] = p[clave] / ESCALA_MILES
    return p


def filas_activas(mascara, total=config.CABEZAL_FILAS):
    """Filas del cabezal que imprimen segun la mascara del parametro 53, o None."""
    if mascara is None:
        return None
    return sum(1 for fila in range(total) if not (mascara >> fila) & BIT_FILA)


def resolucion_nativa(filas):
    """dpi del cabezal en vertical (direccion de las boquillas) con esas filas."""
    if not filas:
        return None
    return config.RESOLUCION_NATIVA_CABEZAL_DPI * filas // config.CABEZAL_FILAS


def aviso_filas(propiedades):
    """Texto de aviso si no imprimen todas las filas del cabezal, o None."""
    filas = propiedades.get("filas_activas")
    if filas is None or filas >= config.CABEZAL_FILAS:
        return None
    return (f"Cabezal modificado, {filas}/{config.CABEZAL_FILAS} filas -> "
            f"{resolucion_nativa(filas)}dpi vertical")


def pasos_de(propiedades):
    """Pasos efectivos (1 si el multipass esta en 'ninguno'), o None."""
    modo = propiedades.get("modo_multipass")
    if modo is None:
        return None
    if modo == MODO_MULTIPASS_NINGUNO:
        return 1
    return propiedades.get("numero_pasadas")


def _o_desconocido(valor, formato="{}"):
    return DESCONOCIDO if valor is None else formato.format(valor)


def _si_no(valor):
    if valor is None:
        return DESCONOCIDO
    return "si" if valor else "no"


def describir_propiedades(p):
    """Lineas para el log."""
    lineas = [
        f"Version {DESCONOCIDO if p['version'] is None else _version(p['version'])} | "
        f"{_o_desconocido(p['dpi_horizontal'], '{:g}')} x "
        f"{_o_desconocido(p['dpi_vertical'], '{:g}')} dpi (H x V) | "
        f"pasos {_o_desconocido(pasos_de(p))} (multipass "
        f"{NOMBRES_MODO_MULTIPASS.get(p['modo_multipass'], DESCONOCIDO)}, "
        f"{NOMBRES_TIPO_MULTIPASS.get(p['tipo_multipass'], DESCONOCIDO)})",
    ]
    fuente = p["fuente_encoder"]
    if fuente is None:
        encoder = DESCONOCIDO
    elif fuente == ENCODER_REAL:
        encoder = f"real, {_o_desconocido(p['resolucion_encoder'], '{:g}')} dpi"
    else:
        velocidad = p["velocidad_encoder_virtual"]
        encoder = ("virtual, " + _o_desconocido(
            None if velocidad is None else velocidad / ESCALA_MILES, "{:g} cm/s"))
    retardo = p["retardo_impresion_um"]
    lineas.append(
        f"Disparo: {NOMBRES_MODO_IMPRESION.get(p['modo_impresion'], DESCONOCIDO)} | encoder "
        f"{encoder} | retardo de impresion "
        f"{_o_desconocido(None if retardo is None else retardo / MICRAS_POR_MM, '{:g} mm')}")
    lineas.append(
        f"Espejo H {_si_no(p['espejo_horizontal'])} / V {_si_no(p['espejo_vertical'])}"
        f" | {_o_desconocido(p['bits_por_pixel'])} bits por pixel | tramado "
        f"{NOMBRES_TRAMADO.get(p['tramado'], DESCONOCIDO)}")
    return lineas


MAXIMO_AVANCES_Y = 16      # tope de seguridad al leer "pm" (el ciclo mas largo, 2400 dpi, son 4)


def leer_avances_y(cliente):
    """Avances Y de un ciclo de multipass segun APRINT ("pm"), hasta el primer 0."""
    avances = []
    for indice in range(MAXIMO_AVANCES_Y):
        valor = struct.unpack("<i", cliente.comando("pm", u16(indice), TAM_ENTERO))[0]
        if valor == 0:
            break
        avances.append(valor)
    return avances


def leer_total_franjas(cliente):
    """Total de franjas (pasadas) del job segun APRINT ("pS")."""
    return struct.unpack("<i", cliente.comando("pS", b"", TAM_ENTERO))[0]


def leer_y_describir(cliente):
    """Para Aprint.conectar(al_conectar=...): (lineas para la app, lineas solo
    para el fichero de log). Deja las propiedades en cliente.propiedades para el
    resto de la app."""
    propiedades = leer_propiedades(cliente)
    cliente.propiedades = propiedades
    archivo = describir_propiedades(propiedades)
    filas = propiedades["filas_activas"]
    archivo.append(f"Cabezal: {DESCONOCIDO if filas is None else filas} de "
                   f"{config.CABEZAL_FILAS} filas activas")
    app = []
    aviso = aviso_filas(propiedades)
    if aviso:
        app.append(f"AVISO: {aviso}")
    # el job activo de APRINT no se consulta: cada render prepara el suyo
    # los avances de Y ("pm") y las franjas ("pS") no se leen al arrancar: APRINT
    # solo los da con el dialogo de impresion abierto o imprimiendo, y la app ya
    # los calcula (secuencia.planificar). Quedan las funciones para comprobarlos.
    return app, archivo
