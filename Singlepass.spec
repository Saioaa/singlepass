# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller: Singlepass en una carpeta (dist/Singlepass), sin consola.

Desde la carpeta de main.py (la de este fichero):
    python -m PyInstaller --noconfirm --clean Singlepass.spec

Recursos: imagenes, fuentes y template.vpi van dentro del paquete, en
dist/Singlepass/_internal/recursos, que es donde los busca programa/config.py
(sys._MEIPASS) con la app empaquetada. Lo que la app escribe (ajustes.json,
RIPOutput, Logging) va a <usuario>\\MATERIALIGHT y lo crea la propia app: no se
empaqueta. recursos/arduino y la configuracion del motor no los usa la app.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

NOMBRE = "Singlepass"
CARPETA = Path(SPECPATH)
sys.path.insert(0, str(CARPETA))   # para que collect_submodules encuentre programa/ e interfaz/
CARPETA_RECURSOS = CARPETA / "recursos"
ICONO = CARPETA_RECURSOS / "imagenes" / "M_02.ico"
PLANTILLA_VPI = CARPETA_RECURSOS / "template.vpi"
CARPETA_FUENTES = CARPETA_RECURSOS / "fuentes"

# Recursos imprescindibles: si falta alguno, el empaquetado se detiene aqui
RECURSOS_OBLIGATORIOS = (ICONO, PLANTILLA_VPI)
faltan = [str(r) for r in RECURSOS_OBLIGATORIOS if not r.is_file()]
if not any(CARPETA_FUENTES.glob("*.ttf")):
    faltan.append(f"{CARPETA_FUENTES} (ningun .ttf: la fuente Nunito)")
if faltan:
    raise SystemExit("Faltan recursos:\n  " + "\n  ".join(faltan))

a = Analysis(
    ["main.py"],
    pathex=[str(CARPETA)],
    binaries=[],
    datas=[
        (str(CARPETA_RECURSOS / "imagenes"), "recursos/imagenes"),
        (str(CARPETA_FUENTES), "recursos/fuentes"),
        (str(PLANTILLA_VPI), "recursos"),
    ],
    # Todos los modulos de programa/ e interfaz/ entran explicitamente, aunque el
    # analisis de imports no los detecte (p. ej. "from programa import registro").
    # coapthon lo usa el sistema de tinta a traves de CoAPIMB_external.
    hiddenimports=(collect_submodules("programa") + collect_submodules("interfaz")
                   + ["coapthon.client.helperclient"]),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOMBRE,
    console=False,            # sin ventana de terminal; el .log del dia se escribe igual
    icon=str(ICONO),
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=NOMBRE,
    upx=False,
)
