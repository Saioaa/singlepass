# -*- coding: utf-8 -*-
"""Board PMB-C8 / PMB-C2: cabezales gobernados por el GIS Print Server.

Envuelve ClientePMB (pmb.py, protocolo TCP) con la interfaz Board: ripeo por
VPI + Render Engine, XOffset en el Print Controller y armado con P,P.
"""

import os

import config
import vpi
from board import (ESTADO_ARMANDO, ESTADO_LISTO, ESTADO_RENDER_LISTO, ESTADO_SIN_TRABAJO,
                   Board, calcular_offset_x)

NOMBRE_OFFSET_X = "XOffset"   # como se llama en los mensajes al parametro del Print Controller
DECIMALES_MM = 2
# Con print go por software el servidor dispara al ARMAR (P,P), no cuando la secuencia
# envia el pulso: la mesa tiene que estar ya en la posicion de pulso al pulsar Print.
TOLERANCIA_ARMADO_MM = 2.0
NUMERO_PLANOS = 4   # img_0..img_3 (CMYK)


class BoardPMB(Board):

    nombre = "PMB"
    tipos_modulo = ("PMB-C8", "PMB-C2")

    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.pmb = cliente
        self._tras_completar = None   # accion encadenada al proximo comando completado
        self._cabezales_registrados = False

        self.pmb.mensaje.connect(self.mensaje)
        self.pmb.modos_recibidos.connect(self.modos_recibidos)
        self.pmb.dpi_recibido.connect(self.dpi_recibido)
        self.pmb.comando_completado.connect(self._tras_completar_comando)
        self.pmb.comando_fallido.connect(self._tras_fallo)
        self.pmb.impresion_terminada.connect(self._tras_fin_impresion)
        self.pmb.listo_para_imprimir.connect(self._armada)
        self.pmb.estado_cabezales.connect(self._mostrar_cabezales)
        self.pmb.conexion_perdida.connect(lambda _motivo: self._poner_estado(ESTADO_SIN_TRABAJO))

    # ===== conexion y modos =====
    def conectar(self):
        return self.pmb.conectado() or self.pmb.conectar()

    def esta_conectada(self):
        return self.pmb.conectado()

    def pedir_modos(self):
        if self.conectar():
            self.pmb.pedir_modos()

    def seleccionar_modo(self, modo):
        self.pmb.pedir_info_modo(modo)

    def _mostrar_cabezales(self, cabezales):
        """Estado periodico de los cabezales: se registra solo la primera vez."""
        if self._cabezales_registrados or not cabezales:
            return
        self._cabezales_registrados = True
        for c in cabezales:
            estado = "activo" if c["activo"] else "deshabilitado"
            self.registrar(f"Cabezal {c['nombre']}: {estado}, "
                           f"{c['temperatura']:.1f} C (objetivo {c['objetivo']:.1f} C)")

    # ===== trabajo =====
    def preparar(self, trabajo, x_cabezal_mm):
        """Genera el VPI con el XOffset de este cabezal, lo carga y lanza el render."""
        offset_x_mm = calcular_offset_x(x_cabezal_mm, trabajo.x_mm, trabajo.ancho_mm)
        if offset_x_mm < 0:
            self.registrar(f"La imagen ya esta bajo el cabezal en reposo "
                           f"({NOMBRE_OFFSET_X} = {offset_x_mm:.{DECIMALES_MM}f} mm): "
                           f"aleja el reposo o acerca la imagen al 0 de la mesa")
            return False
        self.registrar(f"Imagen en mesa: X={trabajo.x_mm:.{DECIMALES_MM}f} mm, "
                       f"Y={trabajo.y_mm:.{DECIMALES_MM}f} mm; "
                       f"cabezal a {x_cabezal_mm:.{DECIMALES_MM}f} mm -> "
                       f"{NOMBRE_OFFSET_X} = {offset_x_mm:.{DECIMALES_MM}f} mm")
        try:
            ruta_vpi = vpi.generar_vpi(
                ruta_imagen=trabajo.ruta_imagen,
                ancho_mm=trabajo.ancho_mm,
                alto_mm=trabajo.alto_mm,
                pos_y_mm=trabajo.y_mm,
                offset_x_mm=offset_x_mm,
                x_imagen_mm=trabajo.x_mm,
                x_cabezal_mm=x_cabezal_mm,
                rotacion=trabajo.rotacion,
                espejo_x=trabajo.espejo_x,
                espejo_y=trabajo.espejo_y)
        except (OSError, ValueError) as e:
            self.registrar(f"No se ha podido generar el VPI: {e}")
            return False
        if not self.conectar():
            return False
        self.carpeta_trabajo = os.path.dirname(ruta_vpi)
        self.registrar(f"Trabajo generado: {ruta_vpi}")
        self._poner_estado(ESTADO_SIN_TRABAJO)
        self._encadenar(self._lanzar_render, vpi.ruta_render(ruta_vpi))
        self.pmb.cargar_vpi(ruta_vpi)
        return True

    def _lanzar_render(self, ruta_bmp):
        self._encadenar(self._render_listo)
        self.pmb.renderizar(ruta_bmp)

    def _render_listo(self):
        self._poner_estado(ESTADO_RENDER_LISTO)

    def cargar_carpeta(self, carpeta):
        if vpi.leer_offset_x(carpeta) is None:
            return False
        self.carpeta_trabajo = carpeta
        self._poner_estado(ESTADO_RENDER_LISTO)
        return True

    def planos_render(self):
        if self.carpeta_trabajo is None:
            return []
        return vpi.rutas_planos(self.carpeta_trabajo, NUMERO_PLANOS)

    def geometria_trabajo(self):
        if self.carpeta_trabajo is None:
            return None
        datos = vpi.leer_datos_trabajo(self.carpeta_trabajo)
        try:
            return float(datos[vpi.CLAVE_X_IMAGEN]), float(datos[vpi.CLAVE_ANCHO_PAGINA])
        except (KeyError, TypeError, ValueError):
            return None

    # ===== armado =====
    def _ruta_bmp(self):
        return os.path.join(self.carpeta_trabajo, vpi.NOMBRE_RENDER)

    def armar(self, posicion_eje_mm):
        if self.carpeta_trabajo is None:
            self.registrar("No hay ningun trabajo rasterizado")
            return False
        if self.estado == ESTADO_LISTO:
            return True   # ya armada: no repetir P,P (daria -201 Print Controller busy)
        if config.PRINT_GO_TAMBIEN_POR_SOFTWARE:
            if posicion_eje_mm is None or abs(posicion_eje_mm - config.POSICION_PULSE_MM) > TOLERANCIA_ARMADO_MM:
                self.registrar(f"Con print go por software el PMB empieza a contar al armar: "
                               f"lleva la mesa a {config.POSICION_PULSE_MM:.0f} mm (reposo) antes de pulsar Print"
                               + (f"; ahora esta en {posicion_eje_mm:.1f} mm" if posicion_eje_mm is not None else ""))
                return False
        offset_x_mm = vpi.leer_offset_x(self.carpeta_trabajo)
        if offset_x_mm is None:
            self.registrar("El trabajo no tiene offset X guardado (falta position_x.json)")
            return False
        self._poner_estado(ESTADO_ARMANDO)
        self._encadenar(self._enviar_print)
        self.pmb.cambiar_parametro_pc(config.PARAMETRO_OFFSET_X, offset_x_mm)
        return True

    def _enviar_print(self):
        # P,P no completa hasta el FIN de la impresion: el "listo" llega por I,<id>,RTP
        self.pmb.imprimir(self._ruta_bmp())

    def _armada(self):
        if self.estado != ESTADO_ARMANDO:
            return
        self.registrar("Cabezales armados, esperando print go")
        self._poner_estado(ESTADO_LISTO)

    def abortar(self):
        if self.pmb.abortar_impresion():
            self._tras_completar = None
            self._poner_estado(ESTADO_RENDER_LISTO if self.carpeta_trabajo else ESTADO_SIN_TRABAJO)

    def print_go_software(self):
        return self.pmb.print_go_software()

    # ===== respuestas del servidor =====
    def _encadenar(self, accion, *argumentos):
        """Accion que se ejecutara cuando el servidor complete el siguiente comando."""
        self._tras_completar = (accion, argumentos)

    def _tras_completar_comando(self, id_comando):
        if self._tras_completar is None:
            return
        accion, argumentos = self._tras_completar
        self._tras_completar = None
        accion(*argumentos)

    def _tras_fallo(self, id_comando, codigo):
        """Un comando ha fallado: se descarta lo encadenado y se vuelve atras."""
        self._tras_completar = None
        if self.estado == ESTADO_ARMANDO:
            self._poner_estado(ESTADO_RENDER_LISTO)

    def _tras_fin_impresion(self):
        """El PMB ha terminado de imprimir (I,<id>,EP): el trabajo sigue disponible."""
        self.registrar("Impresion completada")
        self._poner_estado(ESTADO_RENDER_LISTO)
