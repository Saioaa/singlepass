# -*- coding: utf-8 -*-
"""Pagina Programa: parametros de la secuencia, plan de recorrido a partir de
los modulos, grafico de la barra a escala y arranque/parada de la secuencia.

El grafico dibuja la barra (BARRA_MM) con sus modulos, los perfiles de
velocidad del plan y la mesa como un rectangulo que sigue la posicion real
del eje leida del D1.

Botones del .ui: bt_pg_prog_start, bt_pg_prog_stop.
"""

import time

from PySide6.QtCore import QEvent, QLocale, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QDoubleValidator, QFont, QIntValidator, QPen
from PySide6.QtWidgets import (QFrame, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsTextItem)

import config
from mduino import CMD_PULSO
from board import recorrido_impresion_mm
from secuencia import ParametrosPrograma

# ===== MODULOS DE LA BARRA =====
PRIMER_MODULO = 1
ULTIMO_MODULO = 8
# cabezales de impresion; que board gobierna cada uno lo dice board.tipos_modulo (print_server.py)
TIPOS_CABEZAL = ("PMB-C8", "PMB-C2", "APMB4", "SM-200")
MODULO_VACIO  = "-"
TIPO_NIR      = "NIR"
TIPO_SECADOR  = "Air dryver"
COLOR_NIR     = "#CC9B62"
COLOR_SECADOR = "#CC7662"
COLOR_CABEZAL = "#62CBC9"
OPACIDAD_MODULO_INACTIVO = 0.3   # modulo montado pero desmarcado: se dibuja atenuado
GRADOS_POR_GIRO = 90   # rotacion del nombre del modulo en el grafico

# ===== GRAFICO DE LA BARRA (px) =====
MARGEN_SUPERIOR_MODULO = 10
ALTO_RESERVADO_MODULO  = 40    # alto de la vista menos esto = alto del rectangulo
Y_NUMERO_MODULO        = 12
MARGEN_MESETA          = 15
GROSOR_PERFIL          = 2
ALTO_BARRA_PX          = 10    # linea negra que representa el eje
ALTO_MESA_PX           = 22    # rectangulo de la mesa sobre el eje
ALTO_IMAGEN_PX         = 8     # imagen dibujada sobre la mesa
MARGEN_TEXTO_PX        = 6
TAMANO_TEXTO_ESTADO_PT = 10
COLOR_BARRA   = "#111111"
COLOR_MESA    = "#FFFFFF"
COLOR_BORDE_MESA = "#333333"
COLOR_IMAGEN  = "#7F8C8D"
COLOR_TEXTO   = "#FFFFFF"
COLOR_PULSO   = "#E74C3C"
COLOR_LIMITE  = "#E74C3C"   # marca del limite de carrera del eje sobre la barra
GROSOR_LIMITE = 1
DURACION_AVISO_PULSO_S = 0.6

COLOR_PERFIL_IMPRESION = "#2E86C1"
COLOR_PERFIL_CURADO    = "#27AE60"
TIPOS_CURADO = (TIPO_NIR, TIPO_SECADOR)

MARGEN_FIN_IMPRESION_MM = 20   # recorrido extra tras el fin de la imagen, por deceleracion y holgura

# ===== POTENCIAS (%) =====
POTENCIA_MIN = 0
POTENCIA_MAX = 100

# ===== TEMPORIZACION =====
PERIODO_ANIMACION_MS   = 40     # refresco de la mesa en el grafico


class PlanInvalido(ValueError):
    """El plan de recorrido no puede construirse con los modulos/parametros actuales."""


def _leer_float(campo, por_defecto=None):
    """float del texto de un QLineEdit, o por_defecto si esta vacio o no es numero."""
    try:
        return float(campo.text())
    except ValueError:
        return por_defecto


class PaginaPrograma(QObject):

    def __init__(self, ui, secuencia, mduino, boards_listas, abortar_boards, geometria_imagen,
                 posicion_real, registrar, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.secuencia = secuencia
        self.mduino = mduino
        self._boards_listas = boards_listas      # callable -> bool: todas las boards activas armadas
        self._abortar_boards = abortar_boards    # callable
        self._geometria_imagen = geometria_imagen  # callable -> (x_mm, ancho_mm) | None
        self._posicion_real = posicion_real      # callable -> mm | None
        self.registrar = registrar               # callable(texto)

        self._t_ultimo_pulso = 0.0
        self._ultima_posicion = config.POSICION_REPOSO_MM

        validador = QDoubleValidator()
        validador.setLocale(QLocale(QLocale.English))
        for campo in (self.ui.pg_prog_acel_curado, self.ui.pg_prog_acel_impresion,
                      self.ui.pg_prog_cant_pasadas_curado, self.ui.pg_prog_decel_curado,
                      self.ui.pg_prog_decel_impresion, self.ui.pg_prog_vel_impresion,
                      self.ui.pg_prog_vel_curado):
            campo.setValidator(validador)
        validador_potencia = QIntValidator(POTENCIA_MIN, POTENCIA_MAX)
        self.ui.pg_prog_potencia_NIR.setValidator(validador_potencia)
        self.ui.pg_prog_potencia_secador.setValidator(validador_potencia)

        self.ui.bt_pg_prog_start.clicked.connect(self.start)
        self.ui.bt_pg_prog_stop.clicked.connect(self.stop)

        self.mduino.mensaje_enviado.connect(self._mensaje_mduino)
        self.secuencia.terminada.connect(lambda: self.registrar("[PROGRAMA] Secuencia terminada"))

        # grafico de la barra a escala
        self.escena = QGraphicsScene(self)
        self.ui.pg_vista.setScene(self.escena)
        self.ui.pg_vista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.pg_vista.setFrameShape(QFrame.NoFrame)
        self.ui.pg_vista.viewport().installEventFilter(self)
        self._mesa_item = None
        self._imagen_item = None
        self._texto_estado = None
        self._escala = 1.0
        self._y_base = 0.0

        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            self.combo_modulo(i).currentIndexChanged.connect(self.dibujar_modulos)
            self.campo_distancia(i).textChanged.connect(self.dibujar_modulos)
            check = self.check_modulo(i)
            if check is not None:
                check.toggled.connect(self.dibujar_modulos)
        for campo in (self.ui.pg_prog_vel_impresion, self.ui.pg_prog_acel_impresion,
                      self.ui.pg_prog_decel_impresion, self.ui.pg_prog_vel_curado,
                      self.ui.pg_prog_acel_curado, self.ui.pg_prog_decel_curado,
                      self.ui.pg_prog_cant_pasadas_curado):
            campo.textChanged.connect(self.dibujar_modulos)

        self.timer_animacion = QTimer(self)
        self.timer_animacion.setInterval(PERIODO_ANIMACION_MS)
        self.timer_animacion.timeout.connect(self.actualizar_animacion)
        self.timer_animacion.start()

    def eventFilter(self, objeto, evento):
        if evento.type() == QEvent.Resize:
            QTimer.singleShot(0, self.dibujar_modulos)   # solo esta filtrado el viewport de pg_vista
        return False

    # ===== widgets repetidos =====
    def combo_modulo(self, i):
        return getattr(self.ui, f"modulo{i}")

    def campo_distancia(self, i):
        return getattr(self.ui, f"M{i}D")

    def check_modulo(self, i):
        """QCheckBox que activa el modulo en la secuencia, o None si el .ui no lo tiene."""
        return getattr(self.ui, f"M{i}Check", None)

    def modulo_activo(self, i):
        check = self.check_modulo(i)
        return check is None or check.isChecked()

    # ===== plan de recorrido =====
    def calcular_plan(self, pasadas_curado):
        """Recorridos (mm) a partir de los modulos montados.
        Devuelve (fin_impresion, inicio_curado, fin_curado, hay_curado, hay_impresion, avisos).
        Casos: solo impresion, impresion + curado, solo curado (sin cabezal)."""
        modulos = self.leer_modulos()
        cabezal = self.posicion_cabezal()
        curado = [d for _i, tipo, d in modulos if tipo in TIPOS_CURADO]
        hay_impresion = cabezal is not None
        requiere_armado = hay_impresion   # todo cabezal con board se arma desde Print Server
        hay_curado = bool(curado) and pasadas_curado > 0
        if not hay_impresion and not hay_curado:
            if curado:
                raise PlanInvalido("sin cabezal solo se puede curar, y las pasadas de curado son 0")
            raise PlanInvalido("no hay ningun cabezal ni modulo de curado en los modulos")
        avisos = []
        reposo = config.POSICION_REPOSO_MM
        mesa = config.MESA_ANCHO_MM
        ancho_modulo = config.MODULO_MM

        fin_impresion = reposo
        if hay_impresion:
            fin_impresion = cabezal + ancho_modulo         # la mesa entera ha pasado el cabezal
            if reposo + mesa > cabezal:
                avisos.append(f"en reposo ({reposo} mm) la mesa ya alcanza el cabezal ({cabezal} mm)")
            # el PMB cuenta XOffset + ancho de imagen de encoder tras el PULSE: la pasada
            # tiene que llegar al menos hasta donde termina la imagen, con margen
            geometria = self._geometria_imagen()
            if geometria is not None:
                x_imagen, ancho_imagen = geometria
                fin_pmb = recorrido_impresion_mm(cabezal, x_imagen, ancho_imagen) + MARGEN_FIN_IMPRESION_MM
                if fin_pmb > fin_impresion:
                    avisos.append(f"la imagen termina de imprimirse en {fin_pmb - MARGEN_FIN_IMPRESION_MM:.0f} mm, "
                                  f"mas alla del modulo: se alarga la pasada")
                    fin_impresion = fin_pmb

        if pasadas_curado > 0 and not curado:
            avisos.append("se han pedido pasadas de curado pero no hay modulo NIR/secador")
        if hay_curado:
            inicio_curado = max(config.LIMITE_MIN_MM, min(curado) - mesa)
            fin_curado = max(curado) + ancho_modulo
            fin_impresion = max(fin_impresion, fin_curado)   # la ida imprime y cura a la vez
        else:
            inicio_curado = fin_curado = reposo

        maximo = config.LIMITE_MAX_MM
        if fin_impresion > maximo or fin_curado > maximo:
            avisos.append(f"el recorrido necesario ({max(fin_impresion, fin_curado):.0f} mm) "
                          f"supera el limite del eje ({maximo} mm): se recorta")
            fin_impresion = min(fin_impresion, maximo)
            fin_curado = min(fin_curado, maximo)
        return fin_impresion, inicio_curado, fin_curado, hay_curado, hay_impresion, requiere_armado, avisos

    # ===== parametros =====
    def leer_potencia(self, campo):
        """Potencia en % recortada a [POTENCIA_MIN, POTENCIA_MAX]; vacio = 0."""
        valor = int(_leer_float(campo, por_defecto=0))
        return max(POTENCIA_MIN, min(POTENCIA_MAX, valor))

    def leer_parametros(self):
        """ParametrosPrograma listo para la secuencia. Lanza ValueError si falta algo."""
        pasadas = int(_leer_float(self.ui.pg_prog_cant_pasadas_curado, por_defecto=0))
        (fin_impresion, inicio_curado, fin_curado,
         hay_curado, hay_impresion, requiere_armado, avisos) = self.calcular_plan(pasadas)
        potencia_nir = self.leer_potencia(self.ui.pg_prog_potencia_NIR)
        potencia_secador = self.leer_potencia(self.ui.pg_prog_potencia_secador)
        if hay_curado and potencia_nir == 0:
            avisos.append("hay curado pero la potencia NIR es 0 %: las lamparas no se encenderan")
        for aviso in avisos:
            self.registrar(f"[PROGRAMA] Aviso: {aviso}")
        return ParametrosPrograma(
            vel_impresion=float(self.ui.pg_prog_vel_impresion.text()),
            acel_impresion=float(self.ui.pg_prog_acel_impresion.text()),
            decel_impresion=float(self.ui.pg_prog_decel_impresion.text()),
            vel_curado=float(self.ui.pg_prog_vel_curado.text()),
            acel_curado=float(self.ui.pg_prog_acel_curado.text()),
            decel_curado=float(self.ui.pg_prog_decel_curado.text()),
            pasadas_curado=pasadas,
            fin_impresion=fin_impresion,
            inicio_curado=inicio_curado,
            fin_curado=fin_curado,
            hay_curado=hay_curado,
            hay_impresion=hay_impresion,
            requiere_armado=requiere_armado,
            potencia_nir=potencia_nir,
            potencia_secador=potencia_secador,
        )

    def describir_plan(self, parametros):
        partes = []
        if parametros.hay_impresion:
            partes.append(f"impresion {config.POSICION_REPOSO_MM:.0f} -> {parametros.fin_impresion:.0f} mm "
                          f"a {parametros.vel_impresion:.0f} mm/s")
        if parametros.hay_curado:
            partes.append(f"curado {parametros.pasadas_curado} pasadas entre "
                          f"{parametros.inicio_curado:.0f} y {parametros.fin_curado:.0f} mm "
                          f"a {parametros.vel_curado:.0f} mm/s, NIR {parametros.potencia_nir} %"
                          + ("" if parametros.hay_impresion else " (sin impresion)"))
        return "; ".join(partes)

    # ===== arranque / parada =====
    def start(self):
        """Arranca la secuencia: D1 + M-Duino, con el PMB armado."""
        try:
            parametros = self.leer_parametros()
        except PlanInvalido as e:
            self.registrar(f"[PROGRAMA] No se puede planificar: {e}")
            return
        except ValueError:
            self.registrar("[PROGRAMA] Faltan parametros de impresion o curado")
            return
        if parametros.hay_impresion and parametros.requiere_armado and not self._boards_listas():
            self.registrar("[PROGRAMA] Las boards no estan armadas: pulsa Print en la pagina Print Server")
            return
        if not self.secuencia.start(parametros):
            self.registrar("[PROGRAMA] No se puede arrancar: seta o referencia pendiente")
            return
        self.registrar(f"[PROGRAMA] Plan: {self.describir_plan(parametros)}")

    def stop(self):
        if self.secuencia.en_marcha():
            self.secuencia.stop()
            self.registrar("[PROGRAMA] Parada")
            if self._boards_listas():
                self._abortar_boards()   # las boards no deben quedarse esperando un print go que no llegara

    def _mensaje_mduino(self, mensaje):
        """Lo que sale hacia el M-Duino: el PULSE se resalta en el grafico."""
        if mensaje == CMD_PULSO:
            self._t_ultimo_pulso = time.monotonic()

    # ===== modulos =====
    def leer_modulos(self, solo_activos=True):
        """[(indice, tipo, posicion_mm), ...] de las ranuras ocupadas.
        Por defecto solo los marcados con su checkbox: los demas estan montados
        pero no intervienen en la secuencia."""
        modulos = []
        for i in range(PRIMER_MODULO, ULTIMO_MODULO + 1):
            tipo = self.combo_modulo(i).currentText()
            distancia = _leer_float(self.campo_distancia(i))
            if tipo in (MODULO_VACIO, "") or distancia is None:
                continue
            if solo_activos and not self.modulo_activo(i):
                continue
            modulos.append((i, tipo, distancia))
        return modulos

    def _cabezal_activo(self, tipos=TIPOS_CABEZAL):
        """(tipo, posicion_mm) del primer cabezal activo de esos tipos, o None."""
        cabezales = sorted((m for m in self.leer_modulos() if m[1] in tipos), key=lambda m: m[2])
        return (cabezales[0][1], cabezales[0][2]) if cabezales else None

    def posicion_cabezal(self):
        """Posicion del primer cabezal de impresion activo sobre el recorrido, en mm."""
        cabezal = self._cabezal_activo()
        return cabezal[1] if cabezal else None

    def tipo_cabezal(self):
        cabezal = self._cabezal_activo()
        return cabezal[0] if cabezal else None

    def cabezales_activos(self):
        """[(tipo, posicion_mm), ...] de todos los cabezales activos, para Print Server."""
        return [(tipo, d) for _i, tipo, d in self.leer_modulos() if tipo in TIPOS_CABEZAL]

    # ===== grafico estatico =====
    def _dibujar_perfil(self, v, a, dec, inicio_mm, fin_mm, escala, y_base, altura, color):
        """Perfil trapezoidal de velocidad de un borde del carro."""
        if v <= 0 or a <= 0 or dec <= 0:
            return
        dist_acel = v * v / (2 * a)
        dist_decel = v * v / (2 * dec)
        recorrido = fin_mm - inicio_mm
        if dist_acel + dist_decel > recorrido:   # no cabe la meseta: triangulo
            dist_acel = recorrido * a / (a + dec)
            dist_decel = recorrido - dist_acel
        x0 = inicio_mm * escala
        x1 = (inicio_mm + dist_acel) * escala
        x2 = (fin_mm - dist_decel) * escala
        x3 = fin_mm * escala
        y_pico = y_base - altura
        lapiz = QPen(QColor(color))
        lapiz.setWidth(GROSOR_PERFIL)
        self.escena.addLine(x0, y_base, x1, y_pico, lapiz)
        self.escena.addLine(x1, y_pico, x2, y_pico, lapiz)
        self.escena.addLine(x2, y_pico, x3, y_base, lapiz)

    def dibujar_modulos(self):
        self.escena.clear()
        self._mesa_item = self._imagen_item = self._texto_estado = None

        ancho_px = self.ui.pg_vista.viewport().width()
        alto_px = self.ui.pg_vista.viewport().height()
        self.escena.setSceneRect(0, 0, ancho_px, alto_px)
        self._escala = ancho_px / config.BARRA_MM   # px por mm
        escala = self._escala

        # eje: linea negra a lo ancho, pegada abajo
        y_barra = alto_px - ALTO_BARRA_PX
        self.escena.addRect(QRectF(0, y_barra, ancho_px, ALTO_BARRA_PX),
                            QPen(Qt.NoPen), QBrush(QColor(COLOR_BARRA)))
        self._y_base = y_barra - ALTO_MESA_PX   # sobre la mesa arrancan los perfiles

        # limite de carrera del eje: hasta aqui llega el borde trasero de la mesa
        lapiz_limite = QPen(QColor(COLOR_LIMITE))
        lapiz_limite.setWidth(GROSOR_LIMITE)
        lapiz_limite.setStyle(Qt.DashLine)
        x_limite = config.LIMITE_MAX_MM * escala
        self.escena.addLine(x_limite, MARGEN_SUPERIOR_MODULO, x_limite, y_barra, lapiz_limite)
        etiqueta = QGraphicsSimpleTextItem(f"limite eje {config.LIMITE_MAX_MM:.0f} mm")
        etiqueta.setBrush(QBrush(QColor(COLOR_LIMITE)))
        etiqueta.setFont(QFont("", TAMANO_TEXTO_ESTADO_PT))
        etiqueta.setPos(x_limite + MARGEN_TEXTO_PX, MARGEN_SUPERIOR_MODULO)
        self.escena.addItem(etiqueta)

        alto_rect = self._y_base - ALTO_RESERVADO_MODULO
        for i, tipo, distancia in self.leer_modulos(solo_activos=False):
            x = distancia * escala
            w = config.MODULO_MM * escala
            color = {TIPO_NIR: COLOR_NIR, TIPO_SECADOR: COLOR_SECADOR}.get(tipo, COLOR_CABEZAL)
            rect = QGraphicsRectItem(QRectF(x, MARGEN_SUPERIOR_MODULO, w, alto_rect))
            rect.setBrush(QBrush(QColor(color)))
            if not self.modulo_activo(i):
                rect.setOpacity(OPACIDAD_MODULO_INACTIVO)
            self.escena.addItem(rect)
            num = QGraphicsTextItem(str(i))
            num.setPos(x + (w - num.boundingRect().width()) / 2, Y_NUMERO_MODULO)
            self.escena.addItem(num)
            nombre = QGraphicsTextItem(tipo)
            r = nombre.boundingRect()
            nombre.setRotation(GRADOS_POR_GIRO)
            nombre.setPos(x + w / 2 + r.height() / 2,
                          MARGEN_SUPERIOR_MODULO + alto_rect / 2 - r.width() / 2)
            self.escena.addItem(nombre)

        # perfiles de velocidad del plan (posicion del eje): impresion y, si lo hay, curado
        y_base = self._y_base
        altura_max = y_base - MARGEN_MESETA
        v_impr = _leer_float(self.ui.pg_prog_vel_impresion, por_defecto=0)
        a_impr = _leer_float(self.ui.pg_prog_acel_impresion, por_defecto=0)
        d_impr = _leer_float(self.ui.pg_prog_decel_impresion, por_defecto=0)
        v_cur = _leer_float(self.ui.pg_prog_vel_curado, por_defecto=0)
        a_cur = _leer_float(self.ui.pg_prog_acel_curado, por_defecto=0)
        d_cur = _leer_float(self.ui.pg_prog_decel_curado, por_defecto=0)
        pasadas = int(_leer_float(self.ui.pg_prog_cant_pasadas_curado, por_defecto=0))
        try:
            (fin_impresion, inicio_curado, fin_curado,
             hay_curado, hay_impresion, _requiere_armado, _avisos) = self.calcular_plan(pasadas)
        except PlanInvalido:
            hay_curado = hay_impresion = False
        v_ref = v_impr if hay_impresion and v_impr > 0 else v_cur   # la altura maxima es la mayor velocidad
        if hay_impresion and v_impr > 0:
            self._dibujar_perfil(v_impr, a_impr, d_impr, config.POSICION_REPOSO_MM, fin_impresion,
                                 escala, y_base, altura_max, COLOR_PERFIL_IMPRESION)
        if hay_curado and v_cur > 0 and v_ref > 0:
            altura_cur = altura_max * min(1.0, v_cur / v_ref)
            self._dibujar_perfil(v_cur, a_cur, d_cur, inicio_curado, fin_curado,
                                 escala, y_base, altura_cur, COLOR_PERFIL_CURADO)

        # elementos animados: mesa, imagen sobre la mesa y texto de estado
        self._mesa_item = self.escena.addRect(
            QRectF(0, 0, config.MESA_ANCHO_MM * escala, ALTO_MESA_PX),
            QPen(QColor(COLOR_BORDE_MESA)), QBrush(QColor(COLOR_MESA)))
        self._imagen_item = self.escena.addRect(
            QRectF(0, 0, 0, ALTO_IMAGEN_PX), QPen(Qt.NoPen), QBrush(QColor(COLOR_IMAGEN)))
        self._texto_estado = QGraphicsSimpleTextItem()
        self._texto_estado.setBrush(QBrush(QColor(COLOR_TEXTO)))
        self._texto_estado.setFont(QFont("", TAMANO_TEXTO_ESTADO_PT))
        self.escena.addItem(self._texto_estado)
        self.actualizar_animacion()

    # ===== grafico animado =====
    def posicion_mostrada(self):
        """Posicion real del eje (ultima lectura del D1), en mm."""
        posicion = self._posicion_real()
        if posicion is not None:
            self._ultima_posicion = posicion
        return self._ultima_posicion

    def actualizar_animacion(self):
        if self._mesa_item is None:
            return
        escala = self._escala
        x_mesa = self.posicion_mostrada() * escala
        self._mesa_item.setPos(x_mesa, self._y_base)

        geometria = self._geometria_imagen()
        if geometria is None:
            self._imagen_item.setVisible(False)
        else:
            x_imagen, ancho_imagen = geometria
            self._imagen_item.setRect(0, 0, ancho_imagen * escala, ALTO_IMAGEN_PX)
            self._imagen_item.setPos(x_mesa + x_imagen * escala,
                                     self._y_base + (ALTO_MESA_PX - ALTO_IMAGEN_PX) / 2)
            self._imagen_item.setVisible(True)

        hace_pulso = time.monotonic() - self._t_ultimo_pulso < DURACION_AVISO_PULSO_S
        texto = (f"pos {self.posicion_mostrada():.1f} mm   etapa {self.secuencia.etapa}   "
                 f"lamparas {self.secuencia.senal_lamparas}%" + ("   PRINT GO" if hace_pulso else ""))
        self._texto_estado.setText(texto)
        self._texto_estado.setBrush(QBrush(QColor(COLOR_PULSO if hace_pulso else COLOR_TEXTO)))
        self._texto_estado.setPos(MARGEN_TEXTO_PX, MARGEN_TEXTO_PX)
