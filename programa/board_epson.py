# -*- coding: utf-8 -*-
"""Board SM-200 / HMB (cabezales Epson) a traves de la API REST de Atlas Server.

Atlas Server es el servicio del PC (localhost:5000) que gobierna el HMB (datos
del cabezal) y el SM-200 (encoder y print go). Rutas y campos tomados de su
Swagger (AtlasServices 1.0.10):

    GET  /api/Version                         servidor vivo
    GET  /api/HeadManagerBoards               estado del HMB (Disconnected / Running)
    GET  /api/PrintQueues                     los modos de impresion (colas), con su paso de pixel
    POST /api/Jobs?JobStoreId=Vpi1&JobMode=…  multipart con campo jobData = VPI
    GET  /api/Jobs/{id}                       estado del trabajo (sondeo)
    POST /api/PrintQueues/{id}/stop | /start  cola parada = no imprime; en marcha = espera print go
    POST /api/Jobs/{id}/Cancel, DELETE /api/Jobs/{id}
    GET  /api/Jobs/{id}/Preview.tif           previsualizacion del render

A diferencia del PMB no hay parametro de XOffset: la posicion a lo largo del
recorrido va dentro del VPI. La pagina empieza en el print go, mide
offset + ancho de imagen, y la imagen se coloca en X = offset.

Flujo:  preparar()  genera el VPI y crea el trabajo con la cola PARADA
        armar()     arranca la cola -> el trabajo queda esperando el print go
        abortar()   cancela el trabajo y para la cola
Los nombres de estado de un trabajo no estan en el Swagger: ESTADOS_* se
ajustan con lo que devuelva la primera prueba (todo cambio se registra).
"""

import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

import config
import vpi
from board import (ESTADO_ARMANDO, ESTADO_LISTO, ESTADO_RENDER_LISTO, ESTADO_SIN_TRABAJO,
                   Board, calcular_offset_x)

# ===== SERVIDOR (direcciones en config.py) =====
HOST_ATLAS  = config.IP_ATLAS
PUERTO_API  = config.PUERTO_ATLAS
TIMEOUT_S   = 10
JOB_STORE   = "Vpi1"                  # job store que acepta application/x.gis.vpi
MIME_VPI    = "application/x.gis.vpi"
MIME_JSON   = "application/json"
CAMPO_PROPIEDADES = "jobProperties"   # JSON con las propiedades del trabajo (el servidor lo exige)
FRAME_INICIAL = 0
FRAMES_POR_TRABAJO = 1
FRONTERA    = "------singlepass------trabajo"
CODIGOS_OK  = (200, 201, 202)
PERIODO_SONDEO_S = 0.5
MM_POR_PULGADA = 25.4
DECIMALES_MM = 2

# ===== ESTADOS (nombres observados en el Atlas Server real con probar_epson.py) =====
# Ciclo visto: WaitingForProcessing -> Processing (Vpi1) -> Processing (ImagePrint) -> QueuedForPrint
ESTADO_HMB_OK        = "Running"
ESTADOS_PROCESANDO   = ("WaitingForProcessing", "Processing")             # render en curso
ESTADOS_ARMADA       = ("QueuedForPrint", "ReadyToPrint", "Printing")     # raster hecho, en cola esperando print go
ESTADOS_IMPRESO      = ("Completed", "Printed", "Finished")               # terminado (a confirmar con HMB)
ESTADOS_ERROR        = ("FinishedWithError",)   # terminal con isError; visto sin HMB: "1 of 1 print operations failed"
NOMBRE_TRABAJO       = "singlepass"
NOMBRE_VPI_EPSON     = "epson.vpi"
NOMBRE_PREVIEW_ATLAS = "preview_atlas.tif"   # Preview.tif tal cual lo devuelve Atlas (miniatura cuadrada)
NOMBRE_PREVIEW       = "preview_epson.png"   # tramo de la pagina con la imagen, mismo formato que un plano del PMB
CLAVE_DATOS_EPSON    = "epson"          # bloque propio dentro del json del trabajo


class ClienteAtlas:
    """HTTP minimo sobre urllib: devuelve (codigo, json | texto)."""

    def __init__(self, host=HOST_ATLAS, puerto=PUERTO_API):
        self.base = f"http://{host}:{puerto}"

    def peticion(self, metodo, ruta, cuerpo=None, tipo=None, timeout=TIMEOUT_S):
        cabeceras = {"Accept": "application/json"}
        if tipo:
            cabeceras["Content-Type"] = tipo
            if tipo.startswith("multipart/"):
                cabeceras["Accept"] = "multipart/form-data"   # como Atlas Professional
        req = urllib.request.Request(self.base + ruta, data=cuerpo, method=metodo, headers=cabeceras)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                datos = r.read()
                codigo = r.status
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as e:
            return None, str(e)
        texto = datos.decode("utf-8", errors="replace")
        try:
            return codigo, json.loads(texto) if texto.strip() else ""
        except ValueError:
            return codigo, datos   # binario (Preview.tif)

    def crear_trabajo(self, ruta_vpi, modo, nombre, ancho_mm, alto_mm):
        """POST /api/Jobs con el multipart tal como lo envia Atlas Professional (capturado con
        espia_atlas.py): datos en una parte llamada como el job store, con filename = nombre;
        despues jobProperties (JSON) con filename=- . Sin filename, Atlas ignora la parte."""
        propiedades = {"Name": nombre, "JobStoreId": JOB_STORE, "FrameStart": FRAME_INICIAL,
                       "FrameCount": FRAMES_POR_TRABAJO, "JobMode": modo, "RecognitionId": None,
                       "WidthInMillimetres": round(ancho_mm, DECIMALES_MM),
                       "HeightInMillimetres": round(alto_mm, DECIMALES_MM), "Arguments": None}
        with open(ruta_vpi, "rb") as f:
            datos = f.read()
        parte_datos = ((f"--{FRONTERA}\r\n"
                        f"Content-Type: {MIME_VPI}\r\n"
                        f'Content-Disposition: form-data; name={JOB_STORE}; filename="{nombre}"\r\n\r\n').encode()
                       + datos + b"\r\n")
        parte_props = ((f"--{FRONTERA}\r\n"
                        f"Content-Type: {MIME_JSON}; charset=utf-8\r\n"
                        f"Content-Disposition: form-data; name={CAMPO_PROPIEDADES}; filename=-\r\n\r\n").encode()
                       + json.dumps(propiedades).encode("utf-8") + b"\r\n")
        cuerpo = parte_datos + parte_props + f"--{FRONTERA}--\r\n".encode()
        return self.peticion("POST", "/api/Jobs", cuerpo, f'multipart/form-data; boundary="{FRONTERA}"')


class SondeoTrabajo(QThread):
    """Consulta el trabajo cada PERIODO_SONDEO_S y emite su estado cuando cambia."""

    estado = Signal(dict)       # el trabajo completo (dict) en cada cambio
    perdido = Signal(str)       # el servidor ya no responde o el trabajo no existe

    def __init__(self, cliente, id_trabajo):
        super().__init__()
        self.cliente = cliente
        self.id_trabajo = id_trabajo
        self.activo = True

    def run(self):
        ultimo = None
        while self.activo:
            codigo, trabajo = self.cliente.peticion("GET", f"/api/Jobs/{self.id_trabajo}")
            if codigo is None or codigo == 404:
                self.perdido.emit(str(trabajo)[:120])
                return
            if isinstance(trabajo, dict):
                estado = trabajo.get("state", {})
                clave = (estado.get("name"), estado.get("isTerminal"), estado.get("isError"),
                         len(trabajo.get("printOperations", [])))
                if clave != ultimo:
                    ultimo = clave
                    self.estado.emit(trabajo)
                if estado.get("isTerminal"):
                    return
            self.msleep(int(PERIODO_SONDEO_S * 1000))

    def detener(self):
        self.activo = False


def generar_vpi_pagina(ruta_imagen, ancho_mm, alto_mm, x_pagina_mm, y_mm, rotacion, espejo_x, espejo_y,
                       carpeta_trabajo, ancho_cabezal_mm=vpi.ANCHO_CABEZAL_MM):
    """VPI cuya pagina cubre desde el print go hasta el final de la imagen:
    ancho de pagina = x_pagina + ancho, imagen colocada en X = x_pagina."""
    plantilla = vpi._ruta_plantilla()
    if not os.path.exists(plantilla):
        raise FileNotFoundError(f"No se encuentra la plantilla: {plantilla}")
    nueva_imagen = os.path.join(carpeta_trabajo, os.path.basename(ruta_imagen))
    if not os.path.exists(nueva_imagen):
        shutil.copy(ruta_imagen, nueva_imagen)
    if rotacion % (vpi.GRADOS_VUELTA // 2) == vpi.GIRO_PERPENDICULAR:
        ancho_imagen, alto_visible = alto_mm, ancho_mm
    else:
        ancho_imagen, alto_visible = ancho_mm, alto_mm
    ancho_pagina = x_pagina_mm + ancho_imagen
    d = vpi.DECIMALES_MM

    arbol = ET.parse(plantilla)
    raiz = arbol.getroot()
    documento = raiz.find("Document")
    if documento is not None:
        documento.set("Filename", os.path.join(carpeta_trabajo, NOMBRE_VPI_EPSON))
        documento.set("PhysicalPageWidth", f"{ancho_pagina:.{d}f}")
        documento.set("PhysicalPageHeight", f"{ancho_cabezal_mm:.{d}f}")
        documento.set("VisibleWidth", f"{ancho_pagina:.{d}f}")
        documento.set("VisibleHeight", f"{alto_visible:.{d}f}")
        documento.set("PrintRotation", str(rotacion))
    mapa = raiz.find(".//DIBitmapUser")
    if mapa is not None:
        mapa.set("Filename", nueva_imagen)
        mapa.set("Rotation", f"{rotacion:.{vpi.DECIMALES_GIRO}f}")
        mapa.set("MirrorInX", str(espejo_x).lower())
        mapa.set("MirrorInY", str(espejo_y).lower())
        mapa.set("OrigWidth", f"{ancho_mm:.{d}f}")
        mapa.set("OrigHeight", f"{alto_mm:.{d}f}")
        posicion = mapa.find("DPPosition")
        if posicion is not None:
            posicion.set("X", f"{x_pagina_mm:.{d}f}")
            posicion.set("Y", f"{y_mm:.{d}f}")
        limites = mapa.find("DPBoundary")
        if limites is not None:
            limites.set("Right", f"{ancho_pagina:.{d}f}")
            limites.set("Bottom", f"{alto_visible:.{d}f}")
    ruta_vpi = os.path.join(carpeta_trabajo, NOMBRE_VPI_EPSON)
    arbol.write(ruta_vpi, encoding="UTF-8", xml_declaration=False)
    return ruta_vpi, ancho_pagina, ancho_cabezal_mm


class BoardEpson(Board):

    nombre = "EPSON"
    tipos_modulo = ("SM-200",)

    def __init__(self, host=HOST_ATLAS, puerto=PUERTO_API, parent=None):
        super().__init__(parent)
        self.cliente = ClienteAtlas(host, puerto)
        self.modo = None
        self.pasos_por_modo = {}       # modo -> (xPitch, yPitch) en mm
        self.ruta_vpi = None
        self.dimensiones_pagina = None  # (ancho, alto) mm del VPI enviado
        self.geometria = None           # (x_imagen, ancho_imagen) mm para las previews
        self.alto_imagen_mm = None
        self.id_trabajo = None
        self.sondeo = None
        self._conectada = False
        self._estado_hmb = {}   # id -> ultimo estado avisado, para no repetir el aviso
        self._estado_trabajo_atlas = None   # ultimo state.name recibido del trabajo

    # ===== conexion y modos =====
    def conectar(self):
        codigo, version = self.cliente.peticion("GET", "/api/Version")
        if codigo != 200:
            self._conectada = False
            self.registrar(f"Atlas Server no responde en {self.cliente.base}: {version}")
            return False
        if not self._conectada:
            self.registrar(f"Atlas Server {version.get('AtlasServices', '?') if isinstance(version, dict) else version}")
        self._conectada = True
        codigo, hmbs = self.cliente.peticion("GET", "/api/HeadManagerBoards")
        if codigo == 200 and isinstance(hmbs, list):
            for hmb in hmbs:
                estado = hmb.get("state", {}).get("name")
                if estado == self._estado_hmb.get(hmb.get("id")):
                    continue   # se avisa solo cuando cambia
                self._estado_hmb[hmb.get("id")] = estado
                if estado != ESTADO_HMB_OK:
                    self.registrar(f"HMB {hmb.get('id')}: {estado} (no se podra imprimir hasta que este {ESTADO_HMB_OK})")
                else:
                    self.registrar(f"HMB {hmb.get('id')}: {estado}")
        return True

    def esta_conectada(self):
        return self._conectada

    def pedir_modos(self):
        if not self.conectar():
            return
        codigo, colas = self.cliente.peticion("GET", "/api/PrintQueues")
        if codigo != 200 or not isinstance(colas, list):
            self.registrar(f"No se han podido leer los modos: {colas}")
            return
        self.pasos_por_modo = {c["id"]: (c.get("xPitchInMillimetres"), c.get("yPitchInMillimetres")) for c in colas}
        self.modos_recibidos.emit(list(self.pasos_por_modo))

    def seleccionar_modo(self, modo):
        self.modo = modo
        pasos = self.pasos_por_modo.get(modo)
        if pasos and pasos[0] and pasos[1]:
            self.dpi_recibido.emit(round(MM_POR_PULGADA / pasos[0]), round(MM_POR_PULGADA / pasos[1]))

    def _cola(self):
        return urllib.parse.quote(self.modo, safe="")

    # ===== trabajo =====
    def preparar(self, trabajo, x_cabezal_mm):
        if self.modo is None:
            self.registrar("Selecciona antes un modo de impresion (Load modes)")
            return False
        offset_x_mm = calcular_offset_x(x_cabezal_mm, trabajo.x_mm, trabajo.ancho_mm)
        if offset_x_mm < 0:
            self.registrar(f"La imagen ya esta bajo el cabezal en reposo (offset = {offset_x_mm:.{DECIMALES_MM}f} mm)")
            return False
        self.registrar(f"Imagen en mesa: X={trabajo.x_mm:.{DECIMALES_MM}f} mm, Y={trabajo.y_mm:.{DECIMALES_MM}f} mm; "
                       f"cabezal a {x_cabezal_mm:.{DECIMALES_MM}f} mm -> pagina desde el print go, "
                       f"imagen en X = {offset_x_mm:.{DECIMALES_MM}f} mm")
        marca = datetime.now().strftime(vpi.FORMATO_MARCA)
        nombre_base = os.path.splitext(os.path.basename(trabajo.ruta_imagen))[0]
        carpeta = os.path.join(vpi.CARPETA_SALIDA, f"{marca}_{nombre_base}_epson")
        try:
            os.makedirs(carpeta, exist_ok=True)
            ruta_vpi, ancho_pagina, alto_pagina = generar_vpi_pagina(
                trabajo.ruta_imagen, trabajo.ancho_mm, trabajo.alto_mm, offset_x_mm, trabajo.y_mm,
                trabajo.rotacion, trabajo.espejo_x, trabajo.espejo_y, carpeta)
            with open(os.path.join(carpeta, vpi.NOMBRE_POSICION), "w", encoding="utf-8") as f:
                json.dump({CLAVE_DATOS_EPSON: {"offset_x_mm": offset_x_mm, "x_imagen_mm": trabajo.x_mm,
                                               "ancho_imagen_mm": trabajo.ancho_mm, "alto_imagen_mm": trabajo.alto_mm,
                                               "x_cabezal_mm": x_cabezal_mm,
                                               "modo": self.modo, "ancho_pagina_mm": ancho_pagina}}, f, indent=2)
        except (OSError, ValueError) as e:
            self.registrar(f"No se ha podido generar el VPI: {e}")
            return False
        self._olvidar_trabajo()
        self.carpeta_trabajo = carpeta
        self.ruta_vpi = ruta_vpi
        self.dimensiones_pagina = (ancho_pagina, alto_pagina)
        self.geometria = (trabajo.x_mm, trabajo.ancho_mm)
        self.alto_imagen_mm = trabajo.alto_mm
        self.registrar(f"Trabajo generado: {ruta_vpi}")
        return self._enviar_trabajo()

    def _enviar_trabajo(self):
        """Crea el trabajo en Atlas con la cola parada (no imprime hasta armar)."""
        if not self.conectar():
            return False
        self.cliente.peticion("POST", f"/api/PrintQueues/{self._cola()}/stop")
        ancho, alto = self.dimensiones_pagina
        codigo, trabajo = self.cliente.crear_trabajo(self.ruta_vpi, self.modo, NOMBRE_TRABAJO, ancho, alto)
        if codigo not in CODIGOS_OK or not isinstance(trabajo, dict):
            self.registrar(f"Atlas ha rechazado el trabajo ({codigo}): {str(trabajo)[:200]}")
            return False
        self.id_trabajo = trabajo["id"]
        self._estado_trabajo_atlas = trabajo.get("state", {}).get("name")
        self.registrar(f"Trabajo {self.id_trabajo} creado en Atlas ({self._estado_trabajo_atlas}): ripeando...")
        self.sondeo = SondeoTrabajo(self.cliente, self.id_trabajo)
        self.sondeo.estado.connect(self._estado_trabajo)
        self.sondeo.perdido.connect(self._trabajo_perdido)
        self.sondeo.start()
        return True

    def _estado_trabajo(self, trabajo):
        estado = trabajo.get("state", {})
        nombre = estado.get("name")
        self._estado_trabajo_atlas = nombre
        self.registrar(f"Trabajo {trabajo.get('id')}: {nombre}"
                       + (f" ERROR {estado.get('error')}" if estado.get("isError") else ""))
        if estado.get("isError"):
            self._poner_estado(ESTADO_RENDER_LISTO if self.ruta_vpi else ESTADO_SIN_TRABAJO)
            self.id_trabajo = None
        elif estado.get("isTerminal"):
            if nombre in ESTADOS_IMPRESO:
                self.registrar("Impresion completada")
            self.id_trabajo = None
            self._poner_estado(ESTADO_RENDER_LISTO)   # el VPI sigue: armar() lo reenvia
        elif nombre in ESTADOS_ARMADA:
            if self.estado == ESTADO_ARMANDO:
                self._armada()
            elif self.estado != ESTADO_LISTO:
                self.registrar("Raster terminado")
                self._poner_estado(ESTADO_RENDER_LISTO)   # dispara las previews en Print Server

    def _armada(self):
        self.registrar("Cabezal armado, esperando print go")
        self._poner_estado(ESTADO_LISTO)

    def _trabajo_perdido(self, motivo):
        self.registrar(f"Se ha perdido el trabajo en Atlas: {motivo}")
        self.id_trabajo = None
        self._poner_estado(ESTADO_RENDER_LISTO if self.ruta_vpi else ESTADO_SIN_TRABAJO)

    def _olvidar_trabajo(self):
        if self.sondeo is not None:
            self.sondeo.detener()
            self.sondeo.wait()
            self.sondeo = None
        self.id_trabajo = None

    # ===== armado =====
    def armar(self, posicion_eje_mm):
        if self.ruta_vpi is None:
            self.registrar("No hay ningun trabajo generado")
            return False
        if self.estado == ESTADO_LISTO:
            return True
        if self.id_trabajo is None and not self._enviar_trabajo():
            return False
        self._poner_estado(ESTADO_ARMANDO)
        codigo, _ = self.cliente.peticion("POST", f"/api/PrintQueues/{self._cola()}/start")
        if codigo not in CODIGOS_OK:
            self.registrar(f"No se ha podido arrancar la cola {self.modo} ({codigo})")
            self._poner_estado(ESTADO_RENDER_LISTO)
            return False
        self.registrar(f"Cola {self.modo} en marcha: el trabajo esperara el print go")
        if self._estado_trabajo_atlas in ESTADOS_ARMADA:
            self._armada()   # el trabajo ya estaba ripeado y listo cuando se arranco la cola
        return True

    def abortar(self):
        if self.id_trabajo is not None:
            codigo, _ = self.cliente.peticion("POST", f"/api/Jobs/{self.id_trabajo}/Cancel")
            self.registrar(f"Trabajo {self.id_trabajo} cancelado ({codigo})")
        if self.modo is not None:
            self.cliente.peticion("POST", f"/api/PrintQueues/{self._cola()}/stop")
        self._olvidar_trabajo()
        self._poner_estado(ESTADO_RENDER_LISTO if self.ruta_vpi else ESTADO_SIN_TRABAJO)

    def descartar(self):
        self.abortar()
        self.ruta_vpi = None
        self.geometria = None
        super().descartar()

    # ===== previews =====
    def cargar_carpeta(self, carpeta):
        datos = vpi.leer_datos_trabajo(carpeta).get(CLAVE_DATOS_EPSON)
        ruta_vpi = os.path.join(carpeta, NOMBRE_VPI_EPSON)
        if not datos or not os.path.exists(ruta_vpi):
            return False
        self._olvidar_trabajo()
        self.carpeta_trabajo = carpeta
        self.ruta_vpi = ruta_vpi
        self.modo = datos.get("modo", self.modo)
        self.dimensiones_pagina = (datos["ancho_pagina_mm"], vpi.ANCHO_CABEZAL_MM)
        self.geometria = (datos["x_imagen_mm"], datos["ancho_imagen_mm"])
        self.alto_imagen_mm = datos.get("alto_imagen_mm")
        self._poner_estado(ESTADO_RENDER_LISTO)
        return True

    def planos_render(self):
        """Descarga Preview.tif del trabajo (un unico plano) y guarda en la carpeta el tramo
        de pagina que ocupa la imagen, con el mismo formato que un plano del PMB (ancho de la
        imagen x alto del cabezal), para que Print Server lo componga sobre la mesa."""
        if self.id_trabajo is None or self.carpeta_trabajo is None:
            return []
        codigo, datos = self.cliente.peticion("GET", f"/api/Jobs/{self.id_trabajo}/Preview.tif")
        if codigo != 200 or not isinstance(datos, bytes):
            self.registrar(f"Sin previsualizacion del trabajo {self.id_trabajo} ({codigo})")
            return []
        imagen = QImage.fromData(datos)
        if imagen.isNull():
            self.registrar("Preview.tif no se ha podido decodificar")
            return []
        with open(os.path.join(self.carpeta_trabajo, NOMBRE_PREVIEW_ATLAS), "wb") as f:
            f.write(datos)
        recorte = self._recortar_pagina(imagen)
        ruta = os.path.join(self.carpeta_trabajo, NOMBRE_PREVIEW)
        if not recorte.save(ruta):
            return []
        return [ruta]

    def _recortar_pagina(self, imagen):
        """Preview.tif es una miniatura cuadrada (256 x 256) con la pagina entera encajada
        conservando la proporcion y centrada (bandas blancas arriba y abajo). Se recorta el
        tramo final de la pagina (donde esta la imagen: la pagina empieza en el print go)
        a toda la altura del cabezal, como un plano del PMB."""
        if self.dimensiones_pagina is None or self.geometria is None:
            return imagen
        ancho_pagina, alto_pagina = self.dimensiones_pagina
        ancho_imagen = self.geometria[1]
        escala = min(imagen.width() / ancho_pagina, imagen.height() / alto_pagina)   # px por mm
        ancho_pagina_px = ancho_pagina * escala
        alto_pagina_px = alto_pagina * escala
        x0 = (imagen.width() - ancho_pagina_px) / 2
        y0 = (imagen.height() - alto_pagina_px) / 2
        ancho_px = round(ancho_imagen * escala)
        return imagen.copy(round(x0 + ancho_pagina_px) - ancho_px, round(y0), ancho_px, round(alto_pagina_px))

    def geometria_trabajo(self):
        return self.geometria
