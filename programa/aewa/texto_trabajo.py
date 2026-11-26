# -*- coding: utf-8 -*-
"""Texto del trabajo (boton "Insertar Texto" de Print Server AEWA). De la app
MBD-F-500 (programa/texto_trabajo.py).

APRINT no tiene orden remota para insertar texto, asi que el texto se convierte
en un PDF vectorial (contornos rellenos, sin fuentes incrustadas) del tamano
exacto de su recuadro, se guarda en la carpeta del trabajo
(config.NOMBRE_PDF_TEXTO) y se inserta con "ji" como segundo objeto del job
(programa/aewa/board_aewa.py), con la misma orientacion que la imagen.

Lineas: el texto libre y, debajo, una linea por cada parametro marcado
(resolucion, velocidad, curado) con los valores del trabajo.
Tamano: en puntos tipograficos (1 pt = 1/72"): es la altura de la letra (em).
El recuadro es el de las lineas a ese tamano: al estirarlo por las esquinas en
la mesa cambian juntos el recuadro y los puntos, sin deformar el texto.

TextoTrabajo guarda archivo, posicion y tamano en la mesa (mm), puntos, texto
libre, parametros marcados y las lineas impresas.
"""

from dataclasses import dataclass, field

from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import (QColor, QFont, QFontInfo, QFontMetricsF, QPageLayout, QPageSize, QPainter,
                           QPainterPath, QPdfWriter, QTransform)
from PySide6.QtPdf import QPdfDocument

from programa import config

# ===== PARAMETROS QUE SE PUEDEN INSERTAR =====
PARAM_RESOLUCION = "resolucion"
PARAM_VELOCIDAD = "velocidad"
PARAM_CURADO = "curado"
PARAMETROS = (PARAM_RESOLUCION, PARAM_VELOCIDAD, PARAM_CURADO)
NOMBRES_PARAMETROS = {PARAM_RESOLUCION: "Resolución", PARAM_VELOCIDAD: "Velocidad",
                      PARAM_CURADO: "Curado"}

# ===== GEOMETRIA =====
PUNTOS_POR_PULGADA = 72.0
MM_POR_PUNTO = config.MM_POR_PULGADA / PUNTOS_POR_PULGADA
TAMANO_REFERENCIA_PX = 1000       # la fuente se traza a este tamano y se escala a mm
RESOLUCION_PDF_DPI = 1200         # de la pagina del PDF (el trazado es vectorial)
DECIMALES_PUNTOS = 1
DECIMALES_JSON = 3
TITULO_PDF = "Texto del trabajo"
# sin sustituciones contextuales: algunas fuentes cambian la "x" entre cifras por "×"
RASGOS_DESACTIVADOS = ("calt",)
RASGO_DESACTIVADO = 0


def texto_parametro(clave, valores):
    """valores: {"res_horizontal", "res_vertical", "velocidad" (mm/s o None),
    "pasadas_curado", "potencia_nir", "potencia_secador"} (los de la pagina Programa)."""
    if clave == PARAM_RESOLUCION:
        return f"{valores['res_horizontal']}x{valores['res_vertical']}dpi"
    if clave == PARAM_VELOCIDAD:
        velocidad = valores["velocidad"]
        return "Velocidad sin definir" if velocidad is None else f"{velocidad:g}mm/s"
    if clave == PARAM_CURADO:
        pasadas = valores["pasadas_curado"] or 0
        if pasadas <= 0:
            return "Sin curado"
        partes = []
        if valores["potencia_nir"]:
            partes.append(f"NIR {valores['potencia_nir']:g}%")
        if valores["potencia_secador"]:
            partes.append(f"secador {valores['potencia_secador']:g}%")
        detalle = ", ".join(partes) if partes else "sin potencia"
        return f"Curado {pasadas} pasada{'' if pasadas == 1 else 's'} ({detalle})"
    raise ValueError(f"parametro {clave} no valido")


def componer_lineas(contenido, parametros, valores):
    """Lineas del texto libre (sin las vacias del final) y de los parametros."""
    lineas = contenido.rstrip().splitlines() if contenido.strip() else []
    lineas += [texto_parametro(clave, valores) for clave in PARAMETROS if clave in parametros]
    return lineas


def _fuente():
    fuente = QFont(config.TEXTO_FUENTE)
    fuente.setPixelSize(TAMANO_REFERENCIA_PX)
    if hasattr(fuente, "setFeature"):   # Qt 6.7 o posterior
        for rasgo in RASGOS_DESACTIVADOS:
            fuente.setFeature(QFont.Tag(rasgo), RASGO_DESACTIVADO)
    return fuente


def fuente_disponible():
    """False si Qt no tiene config.TEXTO_FUENTE y usaria otra."""
    return QFontInfo(_fuente()).family().lower() == config.TEXTO_FUENTE.lower()


def trazado_mm(lineas, puntos):
    """(QPainterPath en mm con el origen en la esquina superior izquierda del
    recuadro, ancho_mm, alto_mm). Recuadro: interlineado de la fuente y, si la
    tinta sobresale (acentos, rasgos), ampliado hasta ella."""
    fuente = _fuente()
    metricas = QFontMetricsF(fuente)
    trazado = QPainterPath()
    for indice, linea in enumerate(lineas):
        trazado.addText(0.0, metricas.ascent() + indice * metricas.lineSpacing(), fuente, linea)
    ancho = max((metricas.horizontalAdvance(linea) for linea in lineas), default=0.0)
    alto = metricas.height() + max(len(lineas) - 1, 0) * metricas.lineSpacing()
    recuadro = QRectF(0.0, 0.0, ancho, alto).united(trazado.boundingRect())
    mm_por_unidad = puntos * MM_POR_PUNTO / TAMANO_REFERENCIA_PX
    transformacion = QTransform().scale(mm_por_unidad, mm_por_unidad) \
        .translate(-recuadro.left(), -recuadro.top())
    return (transformacion.map(trazado), recuadro.width() * mm_por_unidad,
            recuadro.height() * mm_por_unidad)


def generar_pdf(ruta, lineas, puntos):
    """Escribe el PDF del texto. Devuelve (ancho_mm, alto_mm) de su pagina tal
    como la lee APRINT (el PDF guarda el tamano en puntos: puede diferir unas
    centesimas del recuadro). Lanza OSError si no se puede escribir."""
    trazado, ancho_mm, alto_mm = trazado_mm(lineas, puntos)
    escritor = QPdfWriter(str(ruta))
    escritor.setTitle(TITULO_PDF)
    escritor.setResolution(RESOLUCION_PDF_DPI)
    escritor.setPageLayout(QPageLayout(QPageSize(QSizeF(ancho_mm, alto_mm), QPageSize.Millimeter),
                                       QPageLayout.Portrait, QMarginsF(0, 0, 0, 0),
                                       QPageLayout.Millimeter))
    pintor = QPainter()
    if not pintor.begin(escritor):
        raise OSError(f"no se puede escribir {ruta}")
    px_por_mm = RESOLUCION_PDF_DPI / config.MM_POR_PULGADA
    pintor.scale(px_por_mm, px_por_mm)
    pintor.setRenderHint(QPainter.Antialiasing)
    pintor.fillPath(trazado, QColor(config.TEXTO_COLOR))
    pintor.end()
    del escritor   # cierra el fichero

    documento = QPdfDocument()
    if documento.load(str(ruta)) != QPdfDocument.Error.None_:
        raise OSError(f"el PDF del texto no se puede leer: {ruta}")
    tamano_pt = documento.pagePointSize(0)
    documento.close()
    return tamano_pt.width() * MM_POR_PUNTO, tamano_pt.height() * MM_POR_PUNTO


@dataclass
class TextoTrabajo:
    contenido: str = ""                             # texto libre tal como se escribio
    parametros: list = field(default_factory=list)  # claves de PARAMETROS marcadas
    lineas: list = field(default_factory=list)      # lo que se imprime
    puntos: float = config.TEXTO_PUNTOS_INICIAL
    x_mm: float = 0.0                               # esquina superior izquierda en la mesa
    y_mm: float = 0.0
    ancho_mm: float = 0.0
    alto_mm: float = 0.0
    archivo: str = config.NOMBRE_PDF_TEXTO

    def a_dict(self):
        return {
            "archivo": self.archivo,
            "x_mm": round(self.x_mm, DECIMALES_JSON),
            "y_mm": round(self.y_mm, DECIMALES_JSON),
            "ancho_mm": round(self.ancho_mm, DECIMALES_JSON),
            "alto_mm": round(self.alto_mm, DECIMALES_JSON),
            "puntos": round(self.puntos, DECIMALES_PUNTOS),
            "contenido": self.contenido,
            "parametros": list(self.parametros),
            "lineas": list(self.lineas),
        }

    @classmethod
    def desde_dict(cls, d):
        """Lanza KeyError/ValueError si falta algo."""
        parametros = [p for p in d.get("parametros", []) if p in PARAMETROS]
        return cls(contenido=str(d.get("contenido", "")), parametros=parametros,
                   lineas=[str(linea) for linea in d["lineas"]], puntos=float(d["puntos"]),
                   x_mm=float(d["x_mm"]), y_mm=float(d["y_mm"]),
                   ancho_mm=float(d["ancho_mm"]), alto_mm=float(d["alto_mm"]),
                   archivo=str(d.get("archivo", config.NOMBRE_PDF_TEXTO)))
