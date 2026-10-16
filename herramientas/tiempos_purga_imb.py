# -*- coding: utf-8 -*-
"""Lee (y opcionalmente cambia) los tiempos de purga del IMB por CoAP.

Parametros del canal segun la libreria del fabricante (CoAPIMB_external.py):
  PUTO  /fc/<c>/cset/pu/PUTO   "Purge timeout"            -> duracion de la purga?
  PCTO  /fc/<c>/cset/pu/PCTO   "Purge Complete timeout"   -> tiempo de retorno a Flow?
  ESTO  /s/<c>/va/ESTO         "... Settle timeout"       -> asentamiento de presion?
  SSTO  /s/<c>/va/SSTO         "... Settle timeout"       -> asentamiento de presion?
Nada de esto esta documentado: se averigua cambiando PUTO y cronometrando la purga.
Primera lectura en la maquina: PUTO = '6' con una purga de ~6 s -> PUTO esta en
SEGUNDOS. PCTO/ESTO/SSTO no existen en este firmware (sin respuesta).
El estado "top" es el modo (HighPressureType2Flow); el de la maquina es "sub"
(Dormant / Idle / Flow / HighPressureTimedPurge), como en tinta.py.

Uso:  py tiempos_purga_imb.py                  -> lee los cuatro valores
      py tiempos_purga_imb.py PUTO 3           -> escribe PUTO=3 (segundos) y lo vuelve a leer
      py tiempos_purga_imb.py PUTO 3 save      -> ademas lo guarda en la NV del IMB
      py tiempos_purga_imb.py cronometrar      -> lanza una purga (hay que estar en Flow)
                                                  y mide cuanto dura cada estado
Sin 'save', el cambio se pierde al reiniciar el IMB (sirve para probar sin riesgo).
Hay que CERRAR la app antes: el IMB no admite dos clientes a la vez.
"""

import sys
import time

from coapthon.client.helperclient import HelperClient

IP_IMB      = "192.168.79.75"
PUERTO_COAP = 5683
CANAL       = "1"
TIMEOUT_S   = 3.0
PERIODO_S   = 0.2
ESPERA_PURGA_MAX_S = 120
ESTADO_FLOW  = "Flow"
CARGA_VACIA  = "NULL"
FORMATO_HORA = "%H:%M:%S"

RUTAS = {
    "PUTO": f"/fc/{CANAL}/cset/pu/PUTO",
    "PCTO": f"/fc/{CANAL}/cset/pu/PCTO",
    "ESTO": f"/s/{CANAL}/va/ESTO",
    "SSTO": f"/s/{CANAL}/va/SSTO",
}


def leer(cliente, ruta):
    respuesta = cliente.get(ruta, timeout=TIMEOUT_S)
    return None if respuesta is None else respuesta.payload


def codigo(respuesta):
    return "sin respuesta" if respuesta is None else f"codigo {respuesta.code}"


def leer_todos(cliente):
    for nombre, ruta in RUTAS.items():
        respuesta = cliente.get(ruta, timeout=TIMEOUT_S)
        valor = None if respuesta is None else respuesta.payload
        print(f"  {nombre} = {valor!r}   ({ruta}, {codigo(respuesta)})")


def estado(cliente):
    """(modo, estado): el estado de la maquina es el 'sub' (Dormant/Idle/Flow/...)."""
    return (leer(cliente, f"/state/top?uc={CANAL}"), leer(cliente, f"/state/sub?uc={CANAL}"))


def cronometrar(cliente):
    inicial = estado(cliente)
    print(f"Estado actual: top={inicial[0]} sub={inicial[1]}")
    if inicial[1] != ESTADO_FLOW:
        print("La purga solo se puede lanzar en Flow. Pon el sistema en Flow y repite.")
        return
    t0 = time.time()
    respuesta = cliente.put(f"/cmd/purge?uc={CANAL}", CARGA_VACIA, timeout=TIMEOUT_S)
    print(f"Orden purge: {codigo(respuesta)}")
    ultimo, t_ultimo = inicial, t0
    while time.time() - t0 < ESPERA_PURGA_MAX_S:
        actual = estado(cliente)
        if actual != ultimo:
            ahora = time.time()
            print(f"{time.strftime(FORMATO_HORA)}  +{ahora - t0:6.1f} s  top={actual[0]}  sub={actual[1]}"
                  f"   (anterior duro {ahora - t_ultimo:.1f} s)")
            if actual[1] == ESTADO_FLOW and ahora - t0 > PERIODO_S * 2:
                print(f"Purga completa: {ahora - t0:.1f} s desde la orden hasta volver a Flow")
                return
            ultimo, t_ultimo = actual, ahora
        time.sleep(PERIODO_S)
    print("No ha vuelto a Flow en el tiempo maximo")


def main():
    args = sys.argv[1:]
    cliente = HelperClient(server=(IP_IMB, PUERTO_COAP))
    try:
        if not args:
            leer_todos(cliente)
        elif args[0] == "cronometrar":
            leer_todos(cliente)
            cronometrar(cliente)
        elif args[0].upper() in RUTAS and len(args) >= 2:
            nombre, valor = args[0].upper(), args[1]
            print(f"{nombre} antes: {leer(cliente, RUTAS[nombre])!r}")
            respuesta = cliente.put(RUTAS[nombre], valor, timeout=TIMEOUT_S)
            print(f"PUT {RUTAS[nombre]} = {valor}: {codigo(respuesta)}")
            despues = leer(cliente, RUTAS[nombre])
            print(f"{nombre} despues: {despues!r}")
            if despues != valor:
                print("El IMB NO ha aceptado el valor (sin respuesta = lo ignora; "
                      "prueba otro rango, p. ej. segundos enteros). No se guarda en NV.")
            elif len(args) >= 3 and args[2] == "save":
                respuesta = cliente.put("/nv/save", CARGA_VACIA, timeout=TIMEOUT_S)
                print(f"Guardado en NV: {codigo(respuesta)}")
            else:
                print("No guardado en NV (se pierde al reiniciar el IMB). Anade 'save' para guardarlo.")
        else:
            print(__doc__)
    finally:
        cliente.stop()


if __name__ == "__main__":
    main()
