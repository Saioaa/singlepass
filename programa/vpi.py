# -*- coding: utf-8 -*-
"""Generacion de trabajos VPI para el print server GIS.

Adaptado de vpi_generate.py. Diferencias:
  - Usa xml.etree de la biblioteca estandar en lugar de lxml: una dependencia
    menos que instalar.
  - El alto de pagina sale de una constante con nombre, no de un literal.
  - Sin valores de la maquina anterior codificados a fuego.

El modelo es el mismo que el del programa anterior:
  - El ANCHO de pagina es el ancho de la imagen (direccion del movimiento).
  - El ALTO de pagina es lo que cubre el cabezal (perpendicular al movimiento).
  - La posicion a lo largo del recorrido se resuelve con XOffset al imprimir,
    no dentro del VPI.
"""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

# ===== AREA DE IMPRESION =====
# PROVISIONAL: valor tomado de template.vpi. Sustituir por el ancho real que
# cubre el cabezal de la maquina, perpendicular al movimiento de la barra.
ANCHO_CABEZAL_MM = 215.8575

# ===== RUTAS =====
CARPETA_BASE    = os.path.join(os.path.expanduser("~"), "MATERIALIGHT")
CARPETA_SALIDA  = os.path.join(CARPETA_BASE, "RIPOutput")
NOMBRE_PLANTILLA = "template.vpi"
NOMBRE_POSICION  = "position_x.json"
NOMBRE_RENDER    = "img.bmp"

# ===== FORMATO =====
DECIMALES_MM     = 6
DECIMALES_GIRO   = 1
FORMATO_MARCA    = "%y%m%d_%H%M%S"
GRADOS_VUELTA    = 360
GIRO_PERPENDICULAR = 90


def _ruta_plantilla():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), NOMBRE_PLANTILLA)


def generar_vpi(ruta_imagen, ancho_mm, alto_mm, pos_x_mm, pos_y_mm,
                rotacion=0, espejo_x=False, espejo_y=False,
                ancho_cabezal_mm=ANCHO_CABEZAL_MM):
    """Crea la carpeta del trabajo y devuelve la ruta del .vpi generado.

    ruta_imagen : imagen a imprimir
    ancho_mm    : ancho real de la imagen en mm
    alto_mm     : alto real de la imagen en mm
    pos_x_mm    : posicion a lo largo del recorrido (se guarda para el XOffset)
    pos_y_mm    : posicion perpendicular, dentro del ancho del cabezal
    """
    plantilla = _ruta_plantilla()
    if not os.path.exists(plantilla):
        raise FileNotFoundError(f"No se encuentra la plantilla: {plantilla}")

    # --- carpeta del trabajo ---
    marca = datetime.now().strftime(FORMATO_MARCA)
    nombre_base = os.path.splitext(os.path.basename(ruta_imagen))[0]
    carpeta_trabajo = os.path.join(CARPETA_SALIDA, f"{marca}_{nombre_base}")
    os.makedirs(carpeta_trabajo, exist_ok=True)

    # --- posicion X, para el XOffset del momento de imprimir ---
    with open(os.path.join(carpeta_trabajo, NOMBRE_POSICION), "w", encoding="utf-8") as f:
        json.dump({"pos_x_mm": pos_x_mm}, f)

    # --- copia de la imagen junto al trabajo ---
    nueva_imagen = os.path.join(carpeta_trabajo, os.path.basename(ruta_imagen))
    shutil.copy(ruta_imagen, nueva_imagen)

    # --- dimensiones segun la rotacion ---
    if rotacion % (GRADOS_VUELTA // 2) == GIRO_PERPENDICULAR:
        ancho_pagina, alto_visible = alto_mm, ancho_mm
    else:
        ancho_pagina, alto_visible = ancho_mm, alto_mm

    # --- rellenar la plantilla ---
    arbol = ET.parse(plantilla)
    raiz = arbol.getroot()

    documento = raiz.find("Document")
    if documento is not None:
        documento.set("Filename", os.path.join(carpeta_trabajo, NOMBRE_PLANTILLA))
        documento.set("PhysicalPageWidth", f"{ancho_pagina:.{DECIMALES_MM}f}")
        documento.set("PhysicalPageHeight", f"{ancho_cabezal_mm:.{DECIMALES_MM}f}")
        documento.set("VisibleWidth", f"{ancho_pagina:.{DECIMALES_MM}f}")
        documento.set("VisibleHeight", f"{alto_visible:.{DECIMALES_MM}f}")
        documento.set("PrintRotation", str(rotacion))

    mapa = raiz.find(".//DIBitmapUser")
    if mapa is not None:
        mapa.set("Filename", nueva_imagen)
        mapa.set("Rotation", f"{rotacion:.{DECIMALES_GIRO}f}")
        mapa.set("MirrorInX", str(espejo_x).lower())
        mapa.set("MirrorInY", str(espejo_y).lower())
        mapa.set("OrigWidth", f"{ancho_mm:.{DECIMALES_MM}f}")
        mapa.set("OrigHeight", f"{alto_mm:.{DECIMALES_MM}f}")

        posicion = mapa.find("DPPosition")
        if posicion is not None:
            posicion.set("X", f"{0:.{DECIMALES_MM}f}")
            posicion.set("Y", f"{pos_y_mm:.{DECIMALES_MM}f}")

        limites = mapa.find("DPBoundary")
        if limites is not None:
            limites.set("Right", f"{ancho_pagina:.{DECIMALES_MM}f}")
            limites.set("Bottom", f"{alto_visible:.{DECIMALES_MM}f}")

    ruta_vpi = os.path.join(carpeta_trabajo, f"{nombre_base}.vpi")
    arbol.write(ruta_vpi, encoding="UTF-8", xml_declaration=False)
    return ruta_vpi


def ruta_render(ruta_vpi):
    """Ruta del bitmap rasterizado que corresponde a un trabajo."""
    return os.path.join(os.path.dirname(ruta_vpi), NOMBRE_RENDER)
